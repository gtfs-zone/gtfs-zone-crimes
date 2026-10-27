"""What is kept per scheduled URL between runs: the last download, its
validators, and the verdicts and facts of the last zip judged."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Runs kept in a record's log, for Groundhog Day.
LOG_RUNS = 7


@dataclass
class LogEntry:
    date: str
    # The response's ETag or Last-Modified differed from the previous one.
    validators_changed: bool
    # The body's sha256 differed from the previous one.
    sha_changed: bool


@dataclass
class UrlRecord:
    url: str
    checked: str | None = None
    status: int | None = None
    error: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    # What the last 200 body was: zip, html, json, xml, empty or unknown.
    kind: str | None = None
    sha256: str | None = None
    log: list[LogEntry] = field(default_factory=list)
    # Package version that judged `sha256`; a new version judges it again.
    judged_version: str | None = None
    # Why the last zip could not be judged (memory, bad_zip...), if it could not.
    judge_error: str | None = None
    verdicts: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)

    def add_log(self, entry: LogEntry) -> None:
        self.log = [*self.log, entry][-LOG_RUNS:]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> UrlRecord:
        data = dict(data)
        data["log"] = [LogEntry(**entry) for entry in data.get("log", [])]
        return cls(**data)


def load_records(doc: dict[str, Any] | None) -> dict[str, UrlRecord]:
    if not doc:
        return {}
    return {url: UrlRecord.from_json(data) for url, data in doc.get("urls", {}).items()}


def dump_records(records: dict[str, UrlRecord]) -> dict[str, Any]:
    return {"urls": {url: record.to_json() for url, record in sorted(records.items())}}
