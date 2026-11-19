"""Download one scheduled URL: a conditional GET with the last validators,
streamed to a temp file and hashed on the way."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gtfs_zone_feed_fetch.fetch import Fetched
from gtfs_zone_feed_fetch.fetch import conditional_headers as validator_headers
from gtfs_zone_feed_fetch.fetch import fetch as fetch_url

from gtfs_zone_crimes.record import LogEntry

if TYPE_CHECKING:
    from pathlib import Path

    import httpx

    from gtfs_zone_crimes.record import UrlRecord

USER_AGENT = "gtfs-zone-crimes (+https://crimes.gtfs.zone)"


def conditional_headers(record: UrlRecord | None, version: str) -> dict[str, str]:
    """If-None-Match / If-Modified-Since, unless this version has not judged the
    last zip yet and needs its bytes again."""
    if record is None or record.judged_version != version or record.kind != "zip":
        return {}
    return validator_headers(record.etag, record.last_modified)


def fetch(
    client: httpx.Client,
    url: str,
    record: UrlRecord | None,
    version: str,
    workdir: Path,
    max_bytes: int,
) -> Fetched:
    """The response to a conditional GET of `url`. A 200 body is written to a
    temp file in `workdir` that the caller deletes."""
    return fetch_url(
        client, url, conditional_headers(record, version), workdir, max_bytes
    )


def update_record(
    record: UrlRecord, fetched: Fetched, today: str, version: str
) -> bool:
    """Fold a download into the record; True when there is a zip to judge."""
    record.checked = today
    record.status = fetched.status
    record.error = fetched.error
    if fetched.status == 304:
        record.add_log(
            LogEntry(date=today, validators_changed=False, sha_changed=False)
        )
        return False
    if fetched.status != 200 or fetched.sha256 is None:
        return False
    if record.sha256 is not None:
        record.add_log(
            LogEntry(
                date=today,
                validators_changed=(fetched.etag, fetched.last_modified)
                != (record.etag, record.last_modified),
                sha_changed=fetched.sha256 != record.sha256,
            )
        )
    changed = fetched.sha256 != record.sha256 or record.judged_version != version
    record.etag = fetched.etag
    record.last_modified = fetched.last_modified
    record.sha256 = fetched.sha256
    record.kind = fetched.kind
    if fetched.kind != "zip":
        # The verdicts were about a zip this URL no longer serves.
        record.verdicts, record.facts = {}, {}
        record.judged_version, record.judge_error = version, None
        return False
    return changed
