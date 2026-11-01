"""Ultra high speed service: a scheduled hop faster than anything in its mode
can go. A bus at 600 km/h, a ferry at 300, or anything at the speed of sound.
Times are often rounded to the minute, so a hop is given at least a minute
and hops under 2 km are ignored. Only trips that still run are judged, and
hops to or from a stop at 0,0 or with swapped coordinates are left to Null
Island. A stop reached and left at impossible speeds within 2x of each other
is marked as likely misplaced."""

from typing import Any

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Part, Ref, Scope, Verdict, linked
from gtfs_zone_crimes.crimes.null_island import stray_stops
from gtfs_zone_crimes.modes import limit_expr, mode_of
from gtfs_zone_crimes.parse import Gtfs

MIN_KM = 2.0
MIN_SECONDS = 60
SIMILAR = 2.0


def misplaced_stops(timed: pl.DataFrame) -> set[str]:
    """Stops reached by one fast hop and left by the next at a similar speed:
    the trip went out to the stop and came back."""
    nxt = pl.col("kmh").shift(-1)
    out = timed.filter(
        (pl.col("trip_id").shift(-1) == pl.col("trip_id"))
        & (pl.col("from_stop").shift(-1) == pl.col("to_stop"))
        & pl.col("fast")
        & pl.col("fast").shift(-1)
        & (pl.max_horizontal("kmh", nxt) <= SIMILAR * pl.min_horizontal("kmh", nxt))
    )
    return set(out["to_stop"].cast(pl.String).to_list())


def judge(gtfs: Gtfs) -> Verdict | None:
    pairs = gtfs.pairs(timed=True, active=True)
    if pairs is None or gtfs.stops is None:
        return None
    stray = stray_stops(gtfs.stops)["stop_id"].implode()
    timed = (
        pairs.filter(
            (pl.col("km") >= MIN_KM)
            & (pl.col("seconds") >= 0)
            & ~pl.col("from_stop").cast(pl.String).is_in(stray)
            & ~pl.col("to_stop").cast(pl.String).is_in(stray)
        )
        .with_columns(
            kmh=pl.col("km") / pl.max_horizontal("seconds", MIN_SECONDS) * 3600
        )
        .with_columns(fast=pl.col("kmh") > limit_expr())
    )
    speeding = timed.filter("fast").sort("kmh", descending=True)
    misplaced = misplaced_stops(timed)
    if speeding.is_empty():
        return ACQUITTED
    names = gtfs.stop_names()
    hops = speeding.unique(["from_stop", "to_stop"], keep="first", maintain_order=True)
    trips = speeding["trip_id"].n_unique()

    def stop(stop_id: str) -> Part:
        return ("stop", stop_id, names.get(stop_id, stop_id))

    def describe(row: dict[str, Any]) -> tuple[str, list[Ref]]:
        mode = mode_of(row["route_type"]).name
        minutes = row["seconds"] / 60
        parts: list[Part] = [
            stop(row["from_stop"]),
            " to ",
            stop(row["to_stop"]),
            f": {row['km']:,.0f} km in {minutes:,.0f} min "
            f"({row['kmh']:,.0f} km/h, {mode}, ",
            ("route", row["route_id"], gtfs.route_label(row["route_id"])),
            ")",
        ]
        suspects = [s for s in (row["from_stop"], row["to_stop"]) if s in misplaced]
        if suspects:
            parts.append(" (likely misplaced stop: ")
            for i, suspect in enumerate(suspects):
                parts += [", "] * bool(i) + [stop(suspect)]
            parts.append(")")
        return linked(*parts)

    rows = hops.head(10).iter_rows(named=True)
    details = [describe(row) for row in rows]
    summary = details[0][0]
    if trips > 1:
        summary = f"{trips:,} trips; {summary}"
    return Verdict.lines(
        details if speeding.height > 1 else [],
        summary=summary,
        metric=trips,
        until=gtfs.until(speeding["trip_id"]),
    )


CRIME = Crime(slug="supersonic", scope=Scope.CONTENT, judge=judge)
