"""Null Island: stops at 0,0 in the Gulf of Guinea, or with latitude and
longitude swapped, a continent away from the rest of the feed. Only stops
served by a trip that still runs are judged."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import Gtfs, haversine_km

NULL_KM = 1.0
STRAY_KM = 2000.0
SWAP_KM = 200.0


def stray_stops(stops: pl.DataFrame) -> pl.DataFrame:
    """Stops with coordinates at 0,0 (`null`) or swapped (`swapped`)."""
    placed = stops.drop_nulls(["stop_lat", "stop_lon"])
    if placed.is_empty():
        return placed.with_columns(null=pl.lit(False), swapped=pl.lit(False))
    lat, lon = pl.col("stop_lat"), pl.col("stop_lon")
    mid_lat, mid_lon = placed["stop_lat"].median(), placed["stop_lon"].median()
    return placed.with_columns(
        null=haversine_km(lat, lon, pl.lit(0.0), pl.lit(0.0)) < NULL_KM,
        swapped=(haversine_km(lat, lon, pl.lit(mid_lat), pl.lit(mid_lon)) > STRAY_KM)
        & (haversine_km(lon, lat, pl.lit(mid_lat), pl.lit(mid_lon)) < SWAP_KM),
    ).filter(pl.col("null") | pl.col("swapped"))


def judge(gtfs: Gtfs) -> Verdict | None:
    stops = gtfs.stops
    running = gtfs.running()
    if stops is None or running is None:
        return None
    served = gtfs.collect(running.select("stop_id").unique())["stop_id"]
    stops = stops.filter(pl.col("stop_id").is_in(served.cast(pl.String).implode()))
    if stops.drop_nulls(["stop_lat", "stop_lon"]).is_empty():
        return None
    flagged = stray_stops(stops)
    if flagged.is_empty():
        return ACQUITTED
    nulls = int(flagged["null"].sum())
    swaps = flagged.height - nulls
    counts = []
    if nulls:
        counts.append(f"{nulls} stop(s) at 0,0")
    if swaps:
        counts.append(f"{swaps} stop(s) with latitude and longitude swapped")
    details = [
        f"{row['stop_name'] or row['stop_id']} ({row['stop_lat']}, {row['stop_lon']})"
        for row in flagged.head(10).iter_rows(named=True)
    ]
    trips = gtfs.collect(
        running.filter(
            pl.col("stop_id").cast(pl.String).is_in(flagged["stop_id"].implode())
        ).select("trip_id")
    )
    return Verdict(
        guilty=True,
        summary="; ".join(counts),
        metric=flagged.height,
        details=details,
        until=gtfs.until(trips["trip_id"]),
    )


CRIME = Crime(slug="null-island", scope=Scope.CONTENT, judge=judge)
