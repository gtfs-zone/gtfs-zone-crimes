"""crimes.json: every crime with its counts, every conviction with its evidence
and since when, and recent pardons. The shape is the contract with
web/src/data/crimes.ts."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from gtfs_zone_crimes.facts import feed_trips, service_end
from gtfs_zone_crimes.judge import judge_feed
from gtfs_zone_crimes.registry import CRIMES

if TYPE_CHECKING:
    from gtfs_zone_crimes.catalog import CatalogFeed
    from gtfs_zone_crimes.record import UrlRecord

# Days a pardon stays on the Recently pardoned page.
PARDON_DAYS = 90
# Verdict fields kept in records.json but not published.
UNPUBLISHED = {"guilty", "until"}


def score(conviction: dict[str, Any], trips: int | None) -> float:
    """How prominently a conviction is listed within its crime: the feed's size
    times the offence's breadth, both on a log scale."""
    return math.log1p(trips or 0) * math.log1p(conviction.get("metric") or 1)


def build_crimes(
    feeds: list[CatalogFeed],
    records: dict[str, UrlRecord],
    today: date,
    previous: dict[str, Any] | None,
    generated_at: str,
    attribution: object = None,
) -> dict[str, Any]:
    """Today's verdicts, with conviction dates carried forward from `previous`.
    A conviction that can no longer be judged (the download failed, the zip
    was too big) stands as it was; one that is now acquitted becomes a pardon,
    unless the crime's revision changed since `previous`, when it is dropped.
    Pardons are kept only under the revision that issued them. Feeds whose
    service has ended are left out altogether."""
    previous = previous or {}
    revision = {crime.slug: crime.revision for crime in CRIMES}
    before_revision = {c["slug"]: c.get("revision") for c in previous.get("crimes", [])}
    feeds = [
        feed
        for feed in feeds
        if (end := service_end(feed, records.get(feed.url or ""))) is None
        or end >= today
    ]
    before = {(c["crime"], c["feedId"]): c for c in previous.get("convictions", [])}
    before_by_feed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for conviction in before.values():
        before_by_feed[conviction["feedId"]].append(conviction)
    live = {feed.id: feed for feed in feeds}
    judged = {crime.slug: 0 for crime in CRIMES}
    convictions: list[dict[str, Any]] = []
    pardons: list[dict[str, Any]] = []
    for feed in feeds:
        verdicts = judge_feed(feed, records.get(feed.url or ""), today)
        for slug, verdict in verdicts.items():
            judged[slug] += 1
            key = (slug, feed.id)
            if verdict.guilty:
                old = before.get(key)
                convictions.append(
                    {
                        "crime": slug,
                        "feedId": feed.id,
                        "since": old["since"] if old else today.isoformat(),
                        **{
                            k: v
                            for k, v in verdict.to_json().items()
                            if k not in UNPUBLISHED
                        },
                    }
                )
            elif key in before and before_revision.get(slug) == revision[slug]:
                pardons.append(
                    {
                        "crime": slug,
                        "feedId": feed.id,
                        "since": before[key]["since"],
                        "pardoned": today.isoformat(),
                        "summary": before[key].get("summary", ""),
                        "revision": revision[slug],
                    }
                )
        for old in before_by_feed.get(feed.id, []):
            if old["crime"] in judged and old["crime"] not in verdicts:
                convictions.append(old)
    cutoff = (today - timedelta(days=PARDON_DAYS)).isoformat()
    seen = {(p["crime"], p["feedId"], p["pardoned"]) for p in pardons}
    pardons += [
        p
        for p in previous.get("pardons", [])
        if p["pardoned"] >= cutoff
        and p["feedId"] in live
        and p["crime"] in judged
        and p.get("revision") == revision[p["crime"]]
        and (p["crime"], p["feedId"], p["pardoned"]) not in seen
    ]
    order = {crime.slug: i for i, crime in enumerate(CRIMES)}
    trips = {feed.id: feed_trips(feed, records.get(feed.url or "")) for feed in feeds}
    convictions.sort(
        key=lambda c: (
            order.get(c["crime"], 99),
            -score(c, trips.get(c["feedId"])),
            -(c.get("metric") or 0),
            c["feedId"],
        )
    )
    pardons.sort(key=lambda p: (p["pardoned"], p["crime"], p["feedId"]), reverse=True)
    convicted: dict[str, int] = {crime.slug: 0 for crime in CRIMES}
    for conviction in convictions:
        convicted[conviction["crime"]] = convicted.get(conviction["crime"], 0) + 1
    named = {c["feedId"] for c in convictions} | {p["feedId"] for p in pardons}
    out: dict[str, Any] = {
        "generated_at": generated_at,
        "feedCount": len(feeds),
        "crimes": [
            {
                "slug": crime.slug,
                "scope": str(crime.scope),
                "convicted": convicted[crime.slug],
                "judged": judged[crime.slug],
                "revision": crime.revision,
            }
            for crime in CRIMES
        ],
        "convictions": convictions,
        "pardons": pardons,
        "feeds": {
            fid: live[fid].summary(trips.get(fid))
            for fid in sorted(named)
            if fid in live
        },
    }
    if attribution is not None:
        out["attribution"] = attribution
    return out
