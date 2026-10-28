"""GTFS tables from a zip as polars frames: each file is extracted once to a
work directory and scanned lazily, every column read as trimmed text."""

from __future__ import annotations

import csv
import io
import math
import shutil
import zipfile
from functools import cached_property
from typing import TYPE_CHECKING

import polars as pl

from gtfs_zone_crimes.facts import WEEKDAYS

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from gtfs_zone_crimes.zipfacts import ZipFacts

EARTH_RADIUS_KM = 6371.0088
# shapes.txt is judged on its first rows: enough to judge it by, and a few
# gigabytes of shapes are never extracted.
SHAPES_SAMPLE_BYTES = 128_000_000


def haversine_km(lat1: pl.Expr, lon1: pl.Expr, lat2: pl.Expr, lon2: pl.Expr) -> pl.Expr:
    """Great-circle distance in km between two coordinate pairs, as an expression."""
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = (dlat / 2).sin() ** 2 + (lat1 * rad).cos() * (lat2 * rad).cos() * (
        dlon / 2
    ).sin() ** 2
    return 2 * EARTH_RADIUS_KM * a.sqrt().arcsin()


def seconds(column: str) -> pl.Expr:
    """A GTFS time (H:MM:SS, hours may pass 24) as seconds into the service day."""
    parts = pl.col(column).str.split(":")
    part = [
        parts.list.get(i, null_on_oob=True).cast(pl.Int32, strict=False)
        for i in range(3)
    ]
    return (part[0] * 3600 + part[1] * 60 + part[2]).alias(column)


def number(column: str, dtype: type[pl.DataType] = pl.Float64) -> pl.Expr:
    return pl.col(column).cast(dtype, strict=False).alias(column)


def read_header(path: Path) -> list[str]:
    with path.open("rb") as handle:
        first = handle.readline().decode("utf-8-sig", errors="replace")
    row = next(csv.reader(io.StringIO(first)), [])
    return [name.strip() for name in row]


class Gtfs:
    """The tables of one GTFS zip, judged as of `today`. Call `close()` to
    remove extracted files."""

    def __init__(
        self, zip_path: Path, facts: ZipFacts, workdir: Path, today: date
    ) -> None:
        self.zip_path = zip_path
        self.facts = facts
        self.workdir = workdir
        self.today = today
        workdir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)

    def extract(self, name: str, max_bytes: int | None = None) -> Path | None:
        """`name`.txt extracted to the work directory, or only its first
        `max_bytes` cut at a line end."""
        suffix = f".head{max_bytes}" if max_bytes else ""
        target = self.workdir / f"{name}{suffix}.txt"
        if target.exists():
            return target
        entry = self.facts.member(f"{name}.txt")
        if entry is None:
            return None
        with (
            zipfile.ZipFile(self.zip_path) as archive,
            archive.open(entry.name) as src,
            target.open("wb") as dst,
        ):
            if max_bytes is None:
                shutil.copyfileobj(src, dst, 1 << 20)
            else:
                head = src.read(max_bytes)
                if len(head) == max_bytes:
                    head = head[: head.rfind(b"\n") + 1]
                dst.write(head)
        return target

    def table(
        self, name: str, columns: list[str], max_bytes: int | None = None
    ) -> pl.LazyFrame | None:
        """`columns` of `name`.txt as trimmed text, empty as null; a column the
        file lacks is all null. None when the file is absent or has no header.
        With `max_bytes`, only the rows in the file's first `max_bytes`."""
        path = self.extract(name, max_bytes)
        if path is None:
            return None
        header = read_header(path)
        if not any(header):
            return None
        # Duplicate or blank header names would make the scan fail; rename them.
        names = [
            name if name and name not in header[:i] else f"_col{i}"
            for i, name in enumerate(header)
        ]
        frame = pl.scan_csv(
            path,
            has_header=True,
            new_columns=names,
            infer_schema=False,
            encoding="utf8-lossy",
            truncate_ragged_lines=True,
            quote_char='"',
        )
        return frame.select(
            [
                (
                    pl.col(column).str.strip_chars()
                    if column in names
                    else pl.lit(None, dtype=pl.String)
                )
                .replace("", None)
                .alias(column)
                for column in columns
            ]
        )

    def collect(self, frame: pl.LazyFrame) -> pl.DataFrame:
        return frame.collect(engine="streaming")

    @cached_property
    def routes(self) -> pl.DataFrame | None:
        frame = self.table(
            "routes",
            [
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type",
                "route_color",
                "route_text_color",
            ],
        )
        if frame is None:
            return None
        return self.collect(frame.with_columns(number("route_type", pl.Int32)))

    @cached_property
    def stops(self) -> pl.DataFrame | None:
        frame = self.table(
            "stops",
            [
                "stop_id",
                "stop_name",
                "stop_lat",
                "stop_lon",
                "location_type",
                "parent_station",
            ],
        )
        if frame is None:
            return None
        return self.collect(
            frame.with_columns(
                number("stop_lat"),
                number("stop_lon"),
                number("location_type", pl.Int32).fill_null(0),
            )
        )

    def shape_points(self) -> pl.LazyFrame | None:
        """shapes.txt's first SHAPES_SAMPLE_BYTES in file order, rows with a
        missing or unparsable value dropped."""
        shapes = self.table(
            "shapes",
            ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
            SHAPES_SAMPLE_BYTES,
        )
        if shapes is None:
            return None
        return shapes.select(
            "shape_id",
            lat=number("shape_pt_lat"),
            lon=number("shape_pt_lon"),
            seq=number("shape_pt_sequence", pl.Int32),
        ).drop_nulls()

    @cached_property
    def sequence(self) -> pl.DataFrame | None:
        """stop_times with route, mode and coordinates, in trip order. Times are
        seconds into the service day, null where the stop is untimed; ids are
        categorical to keep large feeds in memory."""
        stop_times = self.table(
            "stop_times",
            ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
        )
        trips = self.table("trips", ["trip_id", "route_id"])
        if stop_times is None or trips is None or self.stops is None:
            return None
        coords = (
            self.stops.lazy()
            .select(
                pl.col("stop_id").cast(pl.Categorical),
                lat=pl.col("stop_lat").cast(pl.Float32),
                lon=pl.col("stop_lon").cast(pl.Float32),
            )
            .drop_nulls()
            .unique("stop_id")
        )
        frame = (
            stop_times.with_columns(
                number("stop_sequence", pl.Int32),
                seconds("arrival_time"),
                seconds("departure_time"),
            )
            .drop_nulls(["trip_id", "stop_sequence"])
            .select(
                pl.col("trip_id", "stop_id").cast(pl.Categorical),
                "stop_sequence",
                arr=pl.coalesce("arrival_time", "departure_time"),
                dep=pl.coalesce("departure_time", "arrival_time"),
            )
            .join(coords, on="stop_id", how="inner")
            .join(
                trips.drop_nulls("trip_id")
                .unique("trip_id")
                .select(pl.col("trip_id", "route_id").cast(pl.Categorical)),
                on="trip_id",
                how="left",
            )
        )
        if self.routes is not None:
            frame = frame.join(
                self.routes.lazy()
                .select(
                    pl.col("route_id").cast(pl.Categorical),
                    pl.col("route_type").cast(pl.Int16),
                )
                .unique("route_id"),
                on="route_id",
                how="left",
            )
        else:
            frame = frame.with_columns(route_type=pl.lit(None, dtype=pl.Int16))
        # Categorical order groups each trip together, which is all the sort
        # is for; it is far cheaper than sorting the id strings.
        return self.collect(
            frame.sort(pl.col("trip_id").to_physical(), "stop_sequence")
        )

    @cached_property
    def active(self) -> pl.DataFrame | None:
        """Trips whose service runs on or after `today`, with the last date it
        runs (`until`): the latest calendar.txt end_date on a row with any
        weekday set, or added calendar_dates.txt date. None when the feed has
        neither file, so nothing can be said to have ended."""
        # YYYYMMDD sorts as text, so past dates are dropped before parsing.
        today = self.today.strftime("%Y%m%d")
        ends: list[pl.LazyFrame] = []
        calendar = self.table("calendar", ["service_id", "end_date", *WEEKDAYS])
        if calendar is not None:
            ends.append(
                calendar.filter(
                    (pl.col("end_date") >= today)
                    & pl.any_horizontal(pl.col(day) == "1" for day in WEEKDAYS)
                ).select("service_id", date=pl.col("end_date"))
            )
        dates = self.table("calendar_dates", ["service_id", "date", "exception_type"])
        if dates is not None:
            ends.append(
                dates.filter(
                    (pl.col("date") >= today) & (pl.col("exception_type") == "1")
                ).select("service_id", "date")
            )
        trips = self.table("trips", ["trip_id", "service_id"])
        if not ends or trips is None:
            return None
        services = (
            pl.concat(ends)
            .select(
                "service_id", date=pl.col("date").str.to_date("%Y%m%d", strict=False)
            )
            .drop_nulls()
            .group_by("service_id")
            .agg(until=pl.col("date").max())
            .filter(pl.col("until") >= self.today)
        )
        return self.collect(
            trips.drop_nulls()
            .unique("trip_id")
            .join(services, on="service_id")
            .select(pl.col("trip_id").cast(pl.Categorical), "until")
        )

    def running(self) -> pl.LazyFrame | None:
        """`sequence` cut to the active trips, in the same order; all of it when
        the feed has no calendar, None when no trip runs any more."""
        frame = self.sequence
        if frame is None or self.active is None:
            return None if frame is None else frame.lazy()
        if self.active.is_empty():
            return None
        return frame.lazy().join(
            self.active.lazy().select("trip_id"),
            on="trip_id",
            how="semi",
            maintain_order="left",
        )

    def until(self, trips: pl.Series) -> str | None:
        """The last date (ISO) any of `trips` runs, when the feed says."""
        if self.active is None:
            return None
        last = self.active.join(
            trips.unique().to_frame("trip_id"), on="trip_id", how="semi"
        )["until"].max()
        return last.isoformat() if last is not None else None  # type: ignore[union-attr]

    def pairs(self, timed: bool, active: bool = False) -> pl.DataFrame | None:
        """One row per pair of consecutive stops in a trip: the stops, the
        distance, and when `timed`, the scheduled seconds between them (arrival
        minus the previous departure) and the dwell at the second stop. Timed
        pairs skip untimed stops, so they span the stops between two times.
        With `active`, only the trips that still run (None when none do)."""
        if active:
            frame = self.running()
        else:
            frame = None if self.sequence is None else self.sequence.lazy()
        if frame is None:
            return None
        if timed:
            frame = frame.filter(pl.col("arr").is_not_null())
        same_trip = pl.col("trip_id").shift(1) == pl.col("trip_id")
        return (
            frame.with_columns(
                from_stop=pl.col("stop_id").shift(1),
                km=haversine_km(
                    pl.col("lat").shift(1),
                    pl.col("lon").shift(1),
                    pl.col("lat"),
                    pl.col("lon"),
                ).cast(pl.Float32),
                seconds=(pl.col("arr") - pl.col("dep").shift(1)).cast(pl.Int32),
                dwell=(pl.col("dep") - pl.col("arr")).cast(pl.Int32),
            )
            .filter(same_trip)
            .select(
                "trip_id",
                "route_id",
                "route_type",
                "from_stop",
                pl.col("stop_id").alias("to_stop"),
                "km",
                "seconds",
                "dwell",
            )
            .collect()
        )

    def stop_names(self) -> dict[str, str]:
        if self.stops is None:
            return {}
        return {
            row["stop_id"]: row["stop_name"] or row["stop_id"]
            for row in self.stops.select("stop_id", "stop_name")
            .drop_nulls("stop_id")
            .iter_rows(named=True)
        }

    def route_label(self, route_id: str | None) -> str:
        if route_id is None or self.routes is None:
            return "unknown route"
        match = self.routes.filter(pl.col("route_id") == route_id)
        if match.is_empty():
            return route_id
        row = match.row(0, named=True)
        return row["route_short_name"] or row["route_long_name"] or route_id
