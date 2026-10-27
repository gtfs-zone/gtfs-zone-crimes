"""One judging session: feeds.json and yesterday's state in, today's
crimes.json and URL records out. No storage I/O, so the CLI and Dagster share it."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from gtfs_zone_crimes.artifacts import build_crimes
from gtfs_zone_crimes.catalog import parse_feeds
from gtfs_zone_crimes.record import dump_records, load_records
from gtfs_zone_crimes.run import Judge

if TYPE_CHECKING:
    from gtfs_zone_crimes.settings import Settings


def judge_session(
    feeds_doc: dict[str, Any],
    previous: dict[str, Any] | None,
    records_doc: dict[str, Any] | None,
    settings: Settings,
    version: str,
    today: date | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """(crimes.json, records, counts by download outcome)."""
    today = today or datetime.now(UTC).date()
    feeds = parse_feeds(feeds_doc)
    if settings.only:
        feeds = [feed for feed in feeds if feed.id in settings.only]
    records = load_records(records_doc)
    urls = sorted({feed.url for feed in feeds if feed.url})
    counts = Judge(records, settings, today.isoformat(), version).all(urls)
    # Records of URLs no feed points at any more are dropped.
    if not settings.only:
        records = {url: records[url] for url in urls if url in records}
    crimes = build_crimes(
        feeds,
        records,
        today,
        previous,
        datetime.now(UTC).isoformat(timespec="seconds"),
        feeds_doc.get("attribution"),
    )
    return crimes, dump_records(records), counts
