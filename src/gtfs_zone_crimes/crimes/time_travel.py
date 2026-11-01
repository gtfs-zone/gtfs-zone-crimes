"""Time travel: trips that arrive before they leave. Times past 24:00 or even
48:00 are fine (overnight trains have them); going backwards is not. A rewind of 22 h or
more is marked as a likely time past midnight written from 00:00. Only trips
that still run are judged."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Part, Scope, Verdict, linked
from gtfs_zone_crimes.parse import Gtfs

OVERNIGHT = 22 * 3600
MIDNIGHT = " (likely a time past midnight written from 00:00 instead of 24:00)"


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
        to_stop: Part = (
            "stop",
            row["to_stop"],
            names.get(row["to_stop"], row["to_stop"]),
        )
        if row["seconds"] < 0:
            from_stop = names.get(row["from_stop"], row["from_stop"])
            what: list[Part] = [
                "reaches ",
                to_stop,
                f" {clock(-row['seconds'])} before leaving ",
                ("stop", row["from_stop"], from_stop),
            ]
        else:
            what = ["leaves ", to_stop, f" {clock(-row['dwell'])} before arriving"]
        if -row["rewind"] >= OVERNIGHT:
            what.append(MIDNIGHT)
        route = ("route", row["route_id"], gtfs.route_label(row["route_id"]))
        details.append(linked(f"Trip {row['trip_id']} (", route, ") ", *what))
    return Verdict.lines(
        details,
        summary=f"{trips:,} trip(s) go back in time; {details[0][0]}",
        metric=trips,
        until=gtfs.until(backwards["trip_id"]),
    )


CRIME = Crime(slug="time-travel", scope=Scope.CONTENT, judge=judge)
