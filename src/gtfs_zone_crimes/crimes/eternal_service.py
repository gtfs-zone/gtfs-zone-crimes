"""Eternal service: a calendar that runs for years (or until 2099), so the feed
never says when it stops being true."""

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict
from gtfs_zone_crimes.facts import service_end

MAX_YEARS = 5


def judge(case: CatalogCase) -> Verdict | None:
    end = service_end(case.feed, case.record)
    if end is None:
        return None
    years = (end - case.today).days / 365.25
    if years <= MAX_YEARS:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=f"Service runs until {end.isoformat()}, {years:.0f} years from now",
        metric=round(years, 1),
    )


CRIME = Crime(slug="eternal-service", scope=Scope.CATALOG, judge=judge)
