"""SHOUTING: stop or route names in capitals. Scripts without case (Japanese,
Chinese, Arabic...) never count, and short acronyms are let off."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import Gtfs

MAX_SHARE = 0.5
MIN_LENGTH = 5
MIN_NAMES = {"stop": 10, "route": 5}


def shouting(names: pl.Series) -> tuple[float, int, list[str]]:
    """Share of cased names that are all capitals, the cased count, examples."""
    frame = pl.DataFrame({"name": names}).drop_nulls().unique()
    frame = frame.filter(
        (pl.col("name").str.len_chars() >= MIN_LENGTH)
        & (pl.col("name").str.to_lowercase() != pl.col("name").str.to_uppercase())
    )
    if frame.is_empty():
        return 0.0, 0, []
    loud = frame.filter(pl.col("name") == pl.col("name").str.to_uppercase())
    return loud.height / frame.height, frame.height, loud["name"].head(5).to_list()


def judge(gtfs: Gtfs) -> Verdict | None:
    columns = {}
    if gtfs.stops is not None:
        columns["stop"] = gtfs.stops["stop_name"]
    if gtfs.routes is not None:
        columns["route"] = gtfs.routes["route_long_name"]
    if not columns:
        return None
    counts, details, worst = [], [], 0.0
    for what, names in columns.items():
        share, cased, examples = shouting(names)
        if cased >= MIN_NAMES[what] and share > MAX_SHARE:
            counts.append(f"{share:.0%} of {what} names in capitals")
            details += examples
            worst = max(worst, share)
    if not counts:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=f"{'; '.join(counts).upper()}",
        metric=round(worst * 100, 1),
        details=details,
    )


CRIME = Crime(slug="shouting", scope=Scope.CONTENT, judge=judge)
