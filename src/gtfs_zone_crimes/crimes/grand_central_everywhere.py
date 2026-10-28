"""Grand Central Everywhere: ordinary bus stops modelled as GTFS stations
(location_type 1), each holding a pole or two. Coach services are left out:
their stations are usually real ones. Only trips that still run are judged."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.modes import LOCAL_BUS
from gtfs_zone_crimes.parse import Gtfs

MIN_STATIONS = 20
MIN_SHARE = 0.25
MAX_CHILDREN = 3
# Past these a bus route is a coach: median km between stops, longest trip km.
COACH_SPACING_KM = 3.0
COACH_TRIP_KM = 100.0


def local_bus_routes(gtfs: Gtfs) -> set[str]:
    pairs = gtfs.pairs(timed=False, active=True)
    if pairs is None:
        return set()
    buses = pairs.filter(pl.col("route_type").is_in(list(LOCAL_BUS)))
    trips = buses.group_by("trip_id", "route_id").agg(km=pl.col("km").sum())
    spacing = buses.group_by("route_id").agg(spacing=pl.col("km").median())
    longest = trips.group_by("route_id").agg(longest=pl.col("km").max())
    local = spacing.join(longest, on="route_id").filter(
        (pl.col("spacing") <= COACH_SPACING_KM) & (pl.col("longest") <= COACH_TRIP_KM)
    )
    return {str(route) for route in local["route_id"].to_list()}


def judge(gtfs: Gtfs) -> Verdict | None:
    stops, running = gtfs.stops, gtfs.running()
    if stops is None or running is None:
        return None
    stations = stops.filter(pl.col("location_type") == 1)
    if stations.height < MIN_STATIONS:
        return ACQUITTED
    local = local_bus_routes(gtfs)
    served = gtfs.collect(
        running.select("stop_id", "route_id")
        .unique()
        .select(pl.col("stop_id").cast(pl.String), pl.col("route_id").cast(pl.String))
        .group_by("stop_id")
        .agg(only_local=pl.col("route_id").is_in(list(local)).all())
    )
    platforms = stops.filter(pl.col("location_type") == 0).join(
        served, on="stop_id", how="inner"
    )
    bus_stops = platforms.filter(pl.col("only_local"))
    if bus_stops.is_empty():
        return ACQUITTED
    by_station = (
        platforms.drop_nulls("parent_station")
        .group_by("parent_station")
        .agg(children=pl.len(), only_local=pl.col("only_local").all())
        .filter((pl.col("children") <= MAX_CHILDREN) & pl.col("only_local"))
    )
    inflated = by_station.join(
        stations.select("stop_id", "stop_name"),
        left_on="parent_station",
        right_on="stop_id",
        how="inner",
    )
    dressed = int(inflated["children"].sum()) if inflated.height else 0
    share = dressed / bus_stops.height
    if inflated.height < MIN_STATIONS or share <= MIN_SHARE:
        return ACQUITTED
    children = platforms.filter(
        pl.col("parent_station").is_in(inflated["parent_station"].implode())
    )["stop_id"]
    trips = gtfs.collect(
        running.filter(
            pl.col("stop_id").cast(pl.String).is_in(children.implode())
        ).select("trip_id")
    )
    return Verdict(
        guilty=True,
        summary=(
            f"{inflated.height:,} bus stops dressed up as stations "
            f"({share:.0%} of bus stops)"
        ),
        metric=inflated.height,
        details=[
            name or sid
            for sid, name in inflated.select("parent_station", "stop_name")
            .head(10)
            .iter_rows()
        ],
        until=gtfs.until(trips["trip_id"]),
    )


CRIME = Crime(slug="grand-central-everywhere", scope=Scope.CONTENT, judge=judge)
