"""One scheduled URL's latest response: feed-catalog's download of it from the
schedule index, or a conditional GET with the last validators, streamed to a
temp file and hashed on the way."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gtfs_zone_feed_fetch.fetch import Fetched
from gtfs_zone_feed_fetch.fetch import conditional_headers as validator_headers
from gtfs_zone_feed_fetch.fetch import fetch as fetch_url
from gtfs_zone_feed_fetch.store import ERROR, NOT_MODIFIED, OK, TOO_LARGE

from gtfs_zone_crimes.record import LogEntry

if TYPE_CHECKING:
    from pathlib import Path

    import httpx
    from gtfs_zone_feed_fetch.store import Stored

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


def from_index(entry: Stored, max_bytes: int) -> Fetched:
    """feed-catalog's last request of a URL as `fetch` would have returned it,
    without the body: a stored body is known by its sha256 and kind, also
    after a 304."""
    out = Fetched(
        status=entry.status,
        etag=entry.etag or None,
        last_modified=entry.last_modified or None,
    )
    if entry.outcome == TOO_LARGE or (entry.bytes or 0) > max_bytes:
        out.error = f"larger than {max_bytes} bytes"
    elif entry.outcome == ERROR:
        out.status, out.error = None, ERROR
    elif entry.outcome in (OK, NOT_MODIFIED) and entry.sha256:
        out.sha256, out.kind = entry.sha256, entry.kind
    return out


def update_record(
    record: UrlRecord, fetched: Fetched, today: str, version: str
) -> bool:
    """Fold a download into the record; True when there is a zip to judge."""
    record.checked = today
    record.status = fetched.status
    record.error = fetched.error
    if fetched.sha256 is None:
        if fetched.status == 304:
            record.add_log(
                LogEntry(date=today, validators_changed=False, sha_changed=False)
            )
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
