"""Download one scheduled URL: a conditional GET with the last validators,
streamed to a temp file and hashed on the way."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from gtfs_zone_crimes.record import LogEntry

if TYPE_CHECKING:
    from gtfs_zone_crimes.record import UrlRecord

USER_AGENT = "gtfs-zone-crimes (+https://crimes.gtfs.zone)"


@dataclass
class Fetched:
    status: int | None = None
    error: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    path: Path | None = None
    sha256: str | None = None
    kind: str | None = None


def sniff(head: bytes) -> str:
    """What a body is from its first bytes: zip, empty, html, json, xml or unknown."""
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    head = head[:512].lstrip().lower()
    if not head:
        return "empty"
    if head.startswith((b"<!doctype html", b"<html")) or b"<html" in head:
        return "html"
    if head.startswith((b"{", b"[")):
        return "json"
    if head.startswith(b"<"):
        return "xml"
    return "unknown"


def conditional_headers(record: UrlRecord | None, version: str) -> dict[str, str]:
    """If-None-Match / If-Modified-Since, unless this version has not judged the
    last zip yet and needs its bytes again."""
    if record is None or record.judged_version != version or record.kind != "zip":
        return {}
    headers = {}
    if record.etag:
        headers["If-None-Match"] = record.etag
    if record.last_modified:
        headers["If-Modified-Since"] = record.last_modified
    return headers


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
    try:
        with client.stream(
            "GET", url, headers=conditional_headers(record, version)
        ) as response:
            out = Fetched(
                status=response.status_code,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
            if response.status_code != 200:
                return out
            digest = hashlib.sha256()
            size = 0
            head = b""
            with tempfile.NamedTemporaryFile(
                dir=workdir, suffix=".zip", delete=False
            ) as handle:
                out.path = Path(handle.name)
                for chunk in response.iter_bytes(1 << 20):
                    size += len(chunk)
                    if size > max_bytes:
                        out.error = f"larger than {max_bytes} bytes"
                        break
                    if len(head) < 512:
                        head += chunk[: 512 - len(head)]
                    digest.update(chunk)
                    handle.write(chunk)
            if out.error:
                out.path.unlink(missing_ok=True)
                out.path = None
                return out
            out.sha256 = digest.hexdigest()
            out.kind = sniff(head)
            return out
    except httpx.HTTPError as exc:
        return Fetched(error=f"{type(exc).__name__}: {exc}")


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
