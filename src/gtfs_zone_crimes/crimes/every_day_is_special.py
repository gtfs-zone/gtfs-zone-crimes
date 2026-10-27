"""Every day is special: no weekly calendar, just thousands of calendar_dates
rows listing every single day of service."""

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict

MIN_ROWS = 5000


def judge(case: CatalogCase) -> Verdict | None:
    facts = case.record.facts if case.record else {}
    if "datedRows" not in facts:
        return None
    rows = facts["datedRows"]
    if facts["weeklyRows"] or rows <= MIN_ROWS:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=f"No weekly calendar, {rows:,} calendar_dates rows instead",
        metric=rows,
    )


CRIME = Crime(slug="every-day-is-special", scope=Scope.CATALOG, judge=judge)
