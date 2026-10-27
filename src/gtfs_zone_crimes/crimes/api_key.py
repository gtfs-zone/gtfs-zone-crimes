"""Feed requires an API key: a static schedule behind a key. Serving a static
file costs next to nothing; realtime keys are tolerated."""

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict


def judge(case: CatalogCase) -> Verdict:
    if "scheduled" not in case.feed.auth:
        return ACQUITTED
    return Verdict(guilty=True, summary="Static schedule behind an API key")


CRIME = Crime(slug="api-key", scope=Scope.CATALOG, judge=judge)
