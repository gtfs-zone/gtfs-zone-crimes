"""Zip in name only: every entry stored without compression, so the download is
as big as the CSVs inside."""

import zipfile

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.zipfacts import ZipFacts

MIN_BYTES = 1_000_000


def judge(facts: ZipFacts) -> Verdict | None:
    files = [entry for entry in facts.files if entry.size]
    if not files:
        return None
    total = facts.uncompressed_bytes()
    if total < MIN_BYTES or any(e.method != zipfile.ZIP_STORED for e in files):
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=f"{total / 1e6:,.1f} MB stored, not compressed",
        metric=total,
    )


CRIME = Crime(slug="zip-in-name-only", scope=Scope.ARCHIVE, judge=judge)
