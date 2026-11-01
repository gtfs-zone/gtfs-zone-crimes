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


# An object a detail line names: its editor page (`stop`, `route`), its id,
# and the text that links to it, starting at UTF-16 offset `at` as JS counts.
Ref = dict[str, str | int]
Part = str | tuple[str, object, str]


def linked(*parts: Part) -> tuple[str, list[Ref]]:
    """A detail line and its refs from plain text and (type, id, text) parts.
    A part with a null id stays plain text."""
    line, refs, at = "", [], 0
    for part in parts:
        text = part if isinstance(part, str) else part[2]
        if not isinstance(part, str) and part[1] is not None:
            refs.append({"type": part[0], "id": str(part[1]), "at": at, "text": text})
        line += text
        at += len(text.encode("utf-16-le")) // 2
    return line, refs


@dataclass(frozen=True)
class Verdict:
    """The outcome of one crime for one feed. `metric` ranks convictions,
    larger is worse; `summary` is the one line the site shows; `until` is the
    last date (ISO) the offending service runs, after which it is pardoned.
    `refs[i]` names the objects in `details[i]` the site links to the editor."""

    guilty: bool
    summary: str = ""
    metric: float | None = None
    details: list[str] = field(default_factory=list)
    until: str | None = None
    refs: list[list[Ref]] = field(default_factory=list)

    @classmethod
    def lines(
        cls,
        lines: list[tuple[str, list[Ref]]],
        summary: str,
        metric: float,
        until: str | None = None,
    ) -> Verdict:
        """A guilty verdict whose details come from `linked`."""
        return cls(
            guilty=True,
            summary=summary,
            metric=metric,
            details=[text for text, _ in lines],
            until=until,
            refs=[refs for _, refs in lines],
        )

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
        if any(self.refs):
            out["refs"] = self.refs
        return out

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Verdict:
        return cls(
            guilty=data["guilty"],
            summary=data.get("summary", ""),
            metric=data.get("metric"),
            details=data.get("details", []),
            until=data.get("until"),
            refs=data.get("refs", []),
        )


ACQUITTED = Verdict(guilty=False)


@dataclass(frozen=True)
class Crime:
    """A judge returns a Verdict, or None when the feed cannot be judged (the
    input it needs is missing). `feeds` limits the crime to those feed ids.
    `revision` is bumped when a rule change could acquit unchanged feeds; an
    acquittal across revisions is not a pardon."""

    slug: str
    scope: Scope
    judge: Callable[[Any], Verdict | None]
    feeds: frozenset[str] | None = None
    revision: int = 1

    def applies_to(self, feed_id: str) -> bool:
        return self.feeds is None or feed_id in self.feeds


@dataclass(frozen=True)
class CatalogCase:
    """What a catalog-scope crime is judged on. `record` is None until the
    feed's URL has been downloaded once."""

    feed: CatalogFeed
    today: date
    record: UrlRecord | None
