"""One judging session: feeds.json and yesterday's state in, today's
crimes.json and URL records out. Storage I/O is the caller's, except zips and
the schedule index read from `zips`, so the CLI and Dagster share it."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Protocol

from gtfs_zone_feed_fetch.store import INDEX_KEY, parse_index

from gtfs_zone_crimes.artifacts import build_crimes
from gtfs_zone_crimes.catalog import parse_feeds
from gtfs_zone_crimes.record import dump_records, load_records
from gtfs_zone_crimes.run import Judge

if TYPE_CHECKING:
    from pathlib import Path

    from gtfs_zone_feed_fetch.store import Stored

    from gtfs_zone_crimes.settings import Settings

log = logging.getLogger(__name__)


class Zips(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def download(self, key: str, path: Path) -> bool: ...


def read_index(zips: Zips) -> dict[str, Stored]:
    """feed-catalog's schedule index by normalized URL; empty when missing."""
    body = zips.get(INDEX_KEY)
    if not body:
        log.warning("%s missing; every feed is downloaded", INDEX_KEY)
        return {}
    return parse_index(body)


def judge_session(
    feeds_doc: dict[str, Any],
    previous: dict[str, Any] | None,
    records_doc: dict[str, Any] | None,
    settings: Settings,
    version: str,
    today: date | None = None,
    zips: Zips | None = None,
    slugs: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """(crimes.json, records, counts by download outcome). URLs in the schedule
    index of `zips` are judged on feed-catalog's download, the rest on a GET.
    `slugs` maps feed ids to timetable-sites slugs for the feed links."""
    today = today or datetime.now(UTC).date()
    feeds = parse_feeds(feeds_doc, slugs)
    if settings.only:
        feeds = [feed for feed in feeds if feed.id in settings.only]
    records = load_records(records_doc)
    urls = sorted({feed.url for feed in feeds if feed.url})
    index = read_index(zips) if zips is not None else {}
    counts = Judge(records, settings, today.isoformat(), version, index, zips).all(urls)
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
