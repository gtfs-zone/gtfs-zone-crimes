"""Data ONLY: a big feed with no feed_info.txt, so nothing in it says who
publishes it, which version it is, or whom to tell when it is wrong."""

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.zipfacts import ZipFacts

MIN_BYTES = 10_000_000


def judge(facts: ZipFacts) -> Verdict | None:
    if facts.root is None:
        return None
    feed_info = facts.member("feed_info.txt")
    total = facts.uncompressed_bytes()
    if (feed_info is not None and feed_info.size) or total < MIN_BYTES:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary=f"No feed_info.txt in {total / 1e6:,.0f} MB of data",
        metric=total,
    )


CRIME = Crime(slug="data-only", scope=Scope.ARCHIVE, judge=judge)
