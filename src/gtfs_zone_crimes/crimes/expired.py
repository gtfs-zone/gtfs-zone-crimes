"""Expired: the last day of service is behind us."""

from datetime import date

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict


def service_end(case: CatalogCase) -> date | None:
    """The last service date of the last zip judged, else feed-catalog's."""
    value = case.record and case.record.facts.get("serviceEnd")
    value = value or case.feed.service_end
    return date.fromisoformat(value) if value else None


def judge(case: CatalogCase) -> Verdict | None:
    end = service_end(case)
    if end is None:
        return None
    if end >= case.today:
        return ACQUITTED
    days = (case.today - end).days
    return Verdict(
        guilty=True,
        summary=f"Service ended {end.isoformat()}, {days} days ago",
        metric=days,
    )


CRIME = Crime(slug="expired", scope=Scope.CATALOG, judge=judge)
