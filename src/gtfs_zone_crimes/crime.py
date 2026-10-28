"""A crime, what it is judged on, and the verdict it returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    from gtfs_zone_crimes.catalog import CatalogFeed
    from gtfs_zone_crimes.record import UrlRecord


class Scope(StrEnum):
    """What a crime is judged on, which decides when it is judged."""

    # The catalog entry, the download record and the zip's facts; every run.
    CATALOG = "catalog"
    # The zip's central directory; once per zip.
    ARCHIVE = "archive"
    # The zip's parsed tables; once per zip.
    CONTENT = "content"


@dataclass(frozen=True)
class Verdict:
    """The outcome of one crime for one feed. `metric` ranks convictions,
    larger is worse; `summary` is the one line the site shows; `until` is the
    last date (ISO) the offending service runs, after which it is pardoned."""

    guilty: bool
    summary: str = ""
    metric: float | None = None
    details: list[str] = field(default_factory=list)
    until: str | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"guilty": self.guilty}
        if self.summary:
            out["summary"] = self.summary
        if self.metric is not None:
            out["metric"] = self.metric
        if self.details:
            out["details"] = self.details
        if self.until:
            out["until"] = self.until
        return out

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Verdict:
        return cls(
            guilty=data["guilty"],
            summary=data.get("summary", ""),
            metric=data.get("metric"),
            details=data.get("details", []),
            until=data.get("until"),
        )


ACQUITTED = Verdict(guilty=False)


@dataclass(frozen=True)
class Crime:
    """A judge returns a Verdict, or None when the feed cannot be judged (the
    input it needs is missing). `feeds` limits the crime to those feed ids."""

    slug: str
    scope: Scope
    judge: Callable[[Any], Verdict | None]
    feeds: frozenset[str] | None = None

    def applies_to(self, feed_id: str) -> bool:
        return self.feeds is None or feed_id in self.feeds


@dataclass(frozen=True)
class CatalogCase:
    """What a catalog-scope crime is judged on. `record` is None until the
    feed's URL has been downloaded once."""

    feed: CatalogFeed
    today: date
    record: UrlRecord | None
