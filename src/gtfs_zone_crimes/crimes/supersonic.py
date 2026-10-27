"""Ultra high speed service: a scheduled hop faster than anything in its mode
can go. A bus at 600 km/h, a ferry at 300, or anything at the speed of sound.
Times are often rounded to the minute, so a hop is given at least a minute
and hops under 2 km are ignored."""

from typing import Any

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.modes import limit_expr, mode_of
from gtfs_zone_crimes.parse import Gtfs

MIN_KM = 2.0
MIN_SECONDS = 60


def judge(gtfs: Gtfs) -> Verdict | None:
    pairs = gtfs.pairs(timed=True)
    if pairs is None:
        return None
    speeding = (
        pairs.filter((pl.col("km") >= MIN_KM) & (pl.col("seconds") >= 0))
        .with_columns(
            kmh=pl.col("km") / pl.max_horizontal("seconds", MIN_SECONDS) * 3600
        )
        .filter(pl.col("kmh") > limit_expr())
        .sort("kmh", descending=True)
    )
    if speeding.is_empty():
        return ACQUITTED
    names = gtfs.stop_names()
    hops = speeding.unique(["from_stop", "to_stop"], keep="first", maintain_order=True)

    def describe(row: dict[str, Any]) -> str:
        mode = mode_of(row["route_type"]).name
        start = names.get(row["from_stop"], row["from_stop"])
        end = names.get(row["to_stop"], row["to_stop"])
        where = f"{start} to {end}"
        minutes = row["seconds"] / 60
        return (
            f"{where}: {row['km']:,.0f} km in {minutes:,.0f} min "
            f"({row['kmh']:,.0f} km/h, {mode}, {gtfs.route_label(row['route_id'])})"
        )

    rows = hops.head(10).iter_rows(named=True)
    details = [describe(row) for row in rows]
    return Verdict(
        guilty=True,
        summary=details[0],
        metric=float(hops["kmh"][0]),
        details=details if speeding.height > 1 else [],
    )


CRIME = Crime(slug="supersonic", scope=Scope.CONTENT, judge=judge)
