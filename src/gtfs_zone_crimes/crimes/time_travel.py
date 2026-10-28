"""Time travel: trips that arrive before they leave. Times past 24:00 or even
48:00 are fine (overnight trains have them); going backwards is not. Only
trips that still run are judged."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import Gtfs


def clock(value: int) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}{value // 3600}:{value // 60 % 60:02d}:{value % 60:02d}"


def judge(gtfs: Gtfs) -> Verdict | None:
    pairs = gtfs.pairs(timed=True, active=True)
    if pairs is None:
        return None
    backwards = pairs.filter((pl.col("seconds") < 0) | (pl.col("dwell") < 0))
    if backwards.is_empty():
        return ACQUITTED
    trips = backwards["trip_id"].n_unique()
    names = gtfs.stop_names()
    worst = backwards.with_columns(rewind=pl.min_horizontal("seconds", "dwell")).sort(
        "rewind"
    )
    details = []
    for row in (
        worst.unique("trip_id", keep="first", maintain_order=True)
        .head(10)
        .iter_rows(named=True)
    ):
        if row["seconds"] < 0:
            what = (
                f"reaches {names.get(row['to_stop'], row['to_stop'])} "
                f"{clock(-row['seconds'])} before leaving "
                f"{names.get(row['from_stop'], row['from_stop'])}"
            )
        else:
            what = (
                f"leaves {names.get(row['to_stop'], row['to_stop'])} "
                f"{clock(-row['dwell'])} before arriving"
            )
        details.append(
            f"Trip {row['trip_id']} ({gtfs.route_label(row['route_id'])}) {what}"
        )
    return Verdict(
        guilty=True,
        summary=f"{trips:,} trip(s) go back in time; {details[0]}",
        metric=trips,
        details=details,
        until=gtfs.until(backwards["trip_id"]),
    )


CRIME = Crime(slug="time-travel", scope=Scope.CONTENT, judge=judge)
