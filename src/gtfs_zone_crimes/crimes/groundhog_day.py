"""Groundhog Day: the server never lets a client skip a download. Either it
sends no ETag and no Last-Modified, or they change while the bytes do not."""

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict

# Runs out of the record's log whose validators changed with identical bytes.
FALSE_CHANGES = 3


def judge(case: CatalogCase) -> Verdict | None:
    record = case.record
    if record is None or (record.status != 200 and not record.log):
        return None
    if record.status == 200 and not record.etag and not record.last_modified:
        return Verdict(
            guilty=True,
            summary="No ETag, no Last-Modified: every client downloads it every time",
        )
    false_changes = sum(
        1 for entry in record.log if entry.validators_changed and not entry.sha_changed
    )
    if false_changes < FALSE_CHANGES:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=(
            f"New validators on {false_changes} of the last {len(record.log)} "
            "checks, same bytes every time"
        ),
        metric=false_changes,
    )


CRIME = Crime(slug="groundhog-day", scope=Scope.CATALOG, judge=judge)
