"""Dead link: the schedule URL has never answered, or has been down for a month."""

from datetime import datetime

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict

DOWN_DAYS = 30


def judge(case: CatalogCase) -> Verdict | None:
    feed = case.feed
    if feed.scheduled_state is None or feed.scheduled_state == "unknown":
        return None
    if feed.scheduled_state != "down":
        return ACQUITTED
    if feed.never_up:
        # Ranked above every feed that was up once.
        return Verdict(guilty=True, summary="Never seen up", metric=1e6)
    if feed.since is None:
        return None
    days = (case.today - datetime.fromisoformat(feed.since).date()).days
    if days < DOWN_DAYS:
        return ACQUITTED
    return Verdict(guilty=True, summary=f"Down for {days} days", metric=days)


CRIME = Crime(slug="dead-link", scope=Scope.CATALOG, judge=judge)
