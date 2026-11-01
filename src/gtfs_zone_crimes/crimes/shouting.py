"""SHOUTING: stop or route names in capitals. Scripts without case (Japanese,
Chinese, Arabic...) never count, and short acronyms are let off."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict, linked
from gtfs_zone_crimes.parse import Gtfs

MAX_SHARE = 0.5
MIN_LENGTH = 5
MIN_NAMES = {"stop": 10, "route": 5}


def shouting(table: pl.DataFrame) -> tuple[float, int, list[tuple[str, str]]]:
    """Share of cased names in an (id, name) table that are all capitals, the
    cased count, and (id, name) examples, each name with its first id."""
    frame = (
        table.select(pl.all().cast(pl.String))
        .rename(dict(zip(table.columns, ["id", "name"], strict=True)))
        .drop_nulls("name")
        .unique("name", keep="first", maintain_order=True)
    )
    frame = frame.filter(
        (pl.col("name").str.len_chars() >= MIN_LENGTH)
        & (pl.col("name").str.to_lowercase() != pl.col("name").str.to_uppercase())
    )
    if frame.is_empty():
        return 0.0, 0, []
    loud = frame.filter(pl.col("name") == pl.col("name").str.to_uppercase())
    examples = loud.head(5).select("id", "name").rows()
    return loud.height / frame.height, frame.height, examples


def judge(gtfs: Gtfs) -> Verdict | None:
    columns = {}
    if gtfs.stops is not None:
        columns["stop"] = gtfs.stops.select("stop_id", "stop_name")
    if gtfs.routes is not None:
        columns["route"] = gtfs.routes.select("route_id", "route_long_name")
    if not columns:
        return None
    counts, details, worst = [], [], 0.0
    for what, table in columns.items():
        share, cased, examples = shouting(table)
        if cased >= MIN_NAMES[what] and share > MAX_SHARE:
            counts.append(f"{share:.0%} of {what} names in capitals")
            details += [linked((what, oid, name)) for oid, name in examples]
            worst = max(worst, share)
    if not counts:
        return ACQUITTED
    return Verdict.lines(
        details,
        summary=f"{'; '.join(counts).upper()}",
        metric=round(worst * 100, 1),
    )


CRIME = Crime(slug="shouting", scope=Scope.CONTENT, judge=judge)
