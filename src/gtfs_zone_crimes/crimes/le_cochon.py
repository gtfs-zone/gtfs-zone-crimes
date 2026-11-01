"""Le Cochon: a feed carrying rows nothing references, such as shapes no trip
follows, stops no trip serves, or trips with no stop_times. Expired service is
not unused; only rows no reference chain reaches are counted."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import SHAPES_SAMPLE_BYTES, Gtfs

MIN_SHARE = 0.10


@dataclass(frozen=True)
class Waste:
    file: str
    unused: int
    rows: int
    size: int

    @property
    def bytes(self) -> float:
        return self.size * self.unused / self.rows if self.rows else 0.0


def ids(frame: pl.DataFrame, column: str) -> pl.Series:
    return frame[column].drop_nulls().unique().cast(pl.String)


def count(
    gtfs: Gtfs, file: str, frame: pl.DataFrame, column: str, used: pl.Series
) -> Waste:
    entry = gtfs.facts.member(f"{file}.txt")
    unused = frame.filter(~pl.col(column).is_in(used.implode())).height
    return Waste(file, unused, frame.height, entry.size if entry else 0)


def used_stops(stops: pl.DataFrame, served: pl.Series) -> pl.Series:
    """Served stops, their parents and grandparents, and anything (entrances,
    nodes, boarding areas) whose parent is one of those."""
    parent = dict(stops.select("stop_id", "parent_station").drop_nulls().iter_rows())
    used = set(served.to_list())
    for _ in range(2):
        used |= {parent[stop] for stop in used if stop in parent}
    for _ in range(2):
        used |= {stop for stop, up in parent.items() if up in used}
    return pl.Series(sorted(used), dtype=pl.String)


def waste(gtfs: Gtfs) -> list[Waste] | None:
    """Unused rows per file, or None when the feed has no trips or stop_times."""
    sequence = gtfs.sequence
    trips_frame = gtfs.table("trips", ["trip_id", "route_id", "service_id", "shape_id"])
    if sequence is None or trips_frame is None or gtfs.stops is None:
        return None
    trips = gtfs.collect(trips_frame)
    if sequence.is_empty() or trips.is_empty():
        return None
    found = [count(gtfs, "trips", trips, "trip_id", ids(sequence, "trip_id"))]
    kept = trips.filter(pl.col("trip_id").is_in(ids(sequence, "trip_id").implode()))

    shapes = gtfs.table("shapes", ["shape_id"], SHAPES_SAMPLE_BYTES)
    if shapes is not None:
        found.append(
            count(
                gtfs, "shapes", gtfs.collect(shapes), "shape_id", ids(kept, "shape_id")
            )
        )

    stops = gtfs.stops.select("stop_id", "parent_station")
    found.append(
        count(
            gtfs, "stops", stops, "stop_id", used_stops(stops, ids(sequence, "stop_id"))
        )
    )

    routes = gtfs.table("routes", ["route_id", "agency_id"])
    if routes is not None:
        routes = gtfs.collect(routes)
        found.append(count(gtfs, "routes", routes, "route_id", ids(kept, "route_id")))
        agency = gtfs.table("agency", ["agency_id"])
        if agency is not None:
            agency = gtfs.collect(agency)
            if agency.height > 1:
                live = routes.filter(
                    pl.col("route_id").is_in(ids(kept, "route_id").implode())
                )
                found.append(
                    count(gtfs, "agency", agency, "agency_id", ids(live, "agency_id"))
                )

    services = ids(kept, "service_id")
    for file in ("calendar", "calendar_dates"):
        frame = gtfs.table(file, ["service_id"])
        if frame is not None:
            found.append(count(gtfs, file, gtfs.collect(frame), "service_id", services))
    return found


def share(gtfs: Gtfs, found: list[Waste]) -> float:
    total = gtfs.facts.uncompressed_bytes()
    return sum(item.bytes for item in found) / total if total else 0.0


def judge(gtfs: Gtfs) -> Verdict | None:
    found = waste(gtfs)
    if found is None:
        return None
    part = share(gtfs, found)
    if part < MIN_SHARE:
        return ACQUITTED
    worst = sorted(
        (item for item in found if item.unused), key=lambda item: -item.bytes
    )
    total = gtfs.facts.uncompressed_bytes()
    return Verdict(
        guilty=True,
        summary=f"About {part:.0%} of the feed is unused: "
        + ", ".join(f"{item.unused:,} rows of {item.file}.txt" for item in worst[:3]),
        metric=round(part * 100, 1),
        details=[
            f"{item.file}.txt: {item.unused:,} of {item.rows:,} rows unused, "
            f"about {item.bytes / 1e6:,.1f} MB ({item.bytes / total:.0%} of the feed)"
            for item in worst
        ],
    )


CRIME = Crime(slug="le-cochon", scope=Scope.CONTENT, judge=judge)
