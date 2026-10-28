"""Judging: catalog-scope crimes on a feed, archive- and content-scope crimes on
a downloaded zip."""

from __future__ import annotations

import logging
import zipfile
from datetime import date
from typing import TYPE_CHECKING, Any

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Scope, Verdict
from gtfs_zone_crimes.facts import service_facts
from gtfs_zone_crimes.parse import Gtfs
from gtfs_zone_crimes.registry import CRIMES
from gtfs_zone_crimes.zipfacts import read_zipfacts

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from gtfs_zone_crimes.catalog import CatalogFeed
    from gtfs_zone_crimes.record import UrlRecord

log = logging.getLogger(__name__)

Verdicts = dict[str, dict[str, Any] | None]


def judge_zip(
    zip_path: Path, workdir: Path, today: date | None = None
) -> dict[str, Any]:
    """Verdicts of every archive- and content-scope crime on one zip as of
    `today`, plus its service facts. A crime that raises is recorded as
    unjudged."""
    try:
        zipfacts = read_zipfacts(zip_path)
    except zipfile.BadZipFile as exc:
        return {"error": f"bad_zip: {exc}", "verdicts": {}, "facts": {}}
    verdicts: Verdicts = {}
    for crime in CRIMES:
        if crime.scope is Scope.ARCHIVE:
            verdicts[crime.slug] = run(crime.slug, crime.judge, zipfacts)
    gtfs = Gtfs(zip_path, zipfacts, workdir, today or date.today())
    try:
        facts = {}
        if zipfacts.root is not None:
            facts = service_facts(gtfs)
            for crime in CRIMES:
                if crime.scope is Scope.CONTENT:
                    verdicts[crime.slug] = run(crime.slug, crime.judge, gtfs)
    finally:
        gtfs.close()
    return {"verdicts": verdicts, "facts": facts}


def run(
    slug: str, judge: Callable[[Any], Verdict | None], subject: object
) -> dict[str, Any] | None:
    try:
        verdict = judge(subject)
    except Exception:
        log.exception("%s failed", slug)
        return None
    return verdict.to_json() if verdict else None


def judge_feed(
    feed: CatalogFeed, record: UrlRecord | None, today: date
) -> dict[str, Verdict]:
    """Every crime that applies to the feed and could be judged: catalog-scope
    ones now, the rest from the record of its last zip. A conviction whose
    offending service has since ended is an acquittal."""
    case = CatalogCase(feed=feed, today=today, record=record)
    out: dict[str, Verdict] = {}
    for crime in CRIMES:
        if not crime.applies_to(feed.id):
            continue
        if crime.scope is Scope.CATALOG:
            verdict = crime.judge(case)
        else:
            data = record.verdicts.get(crime.slug) if record else None
            verdict = Verdict.from_json(data) if data else None
            if verdict and verdict.until and verdict.until < today.isoformat():
                verdict = ACQUITTED
        if verdict is not None:
            out[crime.slug] = verdict
    return out
