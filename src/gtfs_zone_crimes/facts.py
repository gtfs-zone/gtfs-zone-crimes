"""What a parsed zip contains that catalog-scope crimes read: service range and
calendar shape. Computed once per zip and cached with its verdicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from gtfs_zone_crimes.parse import Gtfs

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def parse_date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value, "%Y%m%d").date() if value else None
    except ValueError:
        return None


def service_facts(gtfs: Gtfs) -> dict[str, Any]:
    """calendar.txt rows with any weekday running, calendar_dates.txt rows, and
    the first and last service dates over both (ISO)."""
    starts: list[date] = []
    ends: list[date] = []
    weekly_rows = 0
    calendar = gtfs.table("calendar", ["start_date", "end_date", *WEEKDAYS])
    if calendar is not None:
        weekly = gtfs.collect(
            calendar.filter(
                pl.any_horizontal(pl.col(day) == "1" for day in WEEKDAYS)
            ).select("start_date", "end_date")
        )
        weekly_rows = weekly.height
        starts += [d for v in weekly["start_date"] if (d := parse_date(v))]
        ends += [d for v in weekly["end_date"] if (d := parse_date(v))]
    dated_rows = 0
    calendar_dates = gtfs.table("calendar_dates", ["date", "exception_type"])
    if calendar_dates is not None:
        dates = gtfs.collect(calendar_dates.select("date", "exception_type"))
        dated_rows = dates.height
        added = dates.filter(pl.col("exception_type") == "1")["date"].drop_nulls()
        if added.len():
            parsed = [d for v in (added.min(), added.max()) if (d := parse_date(v))]
            starts += parsed
            ends += parsed
    return {
        "weeklyRows": weekly_rows,
        "datedRows": dated_rows,
        "serviceStart": min(starts).isoformat() if starts else None,
        "serviceEnd": max(ends).isoformat() if ends else None,
    }
