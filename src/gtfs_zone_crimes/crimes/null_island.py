"""Null Island: stops at 0,0 in the Gulf of Guinea, or with latitude and
longitude swapped, a continent away from the rest of the feed."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import Gtfs, haversine_km

NULL_KM = 1.0
STRAY_KM = 2000.0
SWAP_KM = 200.0


def judge(gtfs: Gtfs) -> Verdict | None:
    stops = gtfs.stops
    if stops is None:
        return None
    placed = stops.drop_nulls(["stop_lat", "stop_lon"])
    if placed.is_empty():
        return None
    lat, lon = pl.col("stop_lat"), pl.col("stop_lon")
    mid_lat, mid_lon = placed["stop_lat"].median(), placed["stop_lon"].median()
    flagged = placed.with_columns(
        null=haversine_km(lat, lon, pl.lit(0.0), pl.lit(0.0)) < NULL_KM,
        swapped=(haversine_km(lat, lon, pl.lit(mid_lat), pl.lit(mid_lon)) > STRAY_KM)
        & (haversine_km(lon, lat, pl.lit(mid_lat), pl.lit(mid_lon)) < SWAP_KM),
    ).filter(pl.col("null") | pl.col("swapped"))
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
    return Verdict(
        guilty=True, summary="; ".join(counts), metric=flagged.height, details=details
    )


CRIME = Crime(slug="null-island", scope=Scope.CONTENT, judge=judge)
