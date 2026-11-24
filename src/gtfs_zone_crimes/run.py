"""Judge every scheduled URL, a bounded number of zips at once. A URL in
feed-catalog's schedule index is read from the store; any other is downloaded
politely: hosts in parallel, one request at a time per host with a pause
between them."""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlsplit

import httpx
from gtfs_zone_feed_fetch.store import lookup, stored_zip

from gtfs_zone_crimes.fetch import USER_AGENT, fetch, from_index, update_record
from gtfs_zone_crimes.judge import judge_zip
from gtfs_zone_crimes.pool import WorkerError, isolated
from gtfs_zone_crimes.record import UrlRecord

if TYPE_CHECKING:
    from collections.abc import Callable

    from gtfs_zone_feed_fetch.fetch import Fetched
    from gtfs_zone_feed_fetch.store import Stored

    from gtfs_zone_crimes.settings import Settings

log = logging.getLogger(__name__)


def judge_item(item: tuple[Path, Path, date]) -> dict[str, Any]:
    return judge_zip(*item)


def by_host(urls: list[str]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        groups[urlsplit(url).netloc.lower()].append(url)
    # Busiest hosts first, so the longest queue is not started last.
    return sorted(groups.values(), key=len, reverse=True)


class ZipSource(Protocol):
    def download(self, key: str, path: Path) -> bool: ...


class Judge:
    """Fetches and judges URLs into `records`, which it updates in place. URLs
    in `index` are read from `zips`."""

    def __init__(
        self,
        records: dict[str, UrlRecord],
        settings: Settings,
        today: str,
        version: str,
        index: dict[str, Stored] | None = None,
        zips: ZipSource | None = None,
    ) -> None:
        self.records = records
        self.settings = settings
        self.today = today
        self.version = version
        self.index = (index or {}) if zips is not None else {}
        self.zips = zips
        self.judging = threading.Semaphore(settings.workers)
        self.lock = threading.Lock()
        self.counts: dict[str, int] = defaultdict(int)

    def record(self, url: str) -> UrlRecord:
        with self.lock:
            return self.records.setdefault(url, UrlRecord(url=url))

    def count(self, key: str) -> None:
        with self.lock:
            self.counts[key] += 1

    def one(self, client: httpx.Client, url: str) -> None:
        record = self.record(url)
        fetched = fetch(
            client,
            url,
            record,
            self.version,
            self.settings.workdir,
            self.settings.max_download,
        )
        self.judge(url, record, fetched)

    def stored(self, url: str, entry: Stored) -> None:
        """Judge `url` on feed-catalog's download of it; the zip is read from
        the store only when it needs judging."""
        assert self.zips is not None
        record = self.record(url)
        fetched = from_index(entry, self.settings.max_download)
        self.count("indexed")
        if not update_record(record, fetched, self.today, self.version):
            self.count(f"status {fetched.status or 'error'}")
            return
        key = stored_zip(entry)
        with tempfile.NamedTemporaryFile(
            dir=self.settings.workdir, suffix=".zip", delete=False
        ) as handle:
            fetched.path = Path(handle.name)
        if not key or not self.zips.download(key, fetched.path):
            log.warning("%s: %s is not in the store", url, key or entry.sha256)
            fetched.path.unlink(missing_ok=True)
            # Judged again on the next run.
            record.judged_version = None
            self.count("not stored")
            return
        self.judge(url, record, fetched, updated=True)

    def judge(
        self, url: str, record: UrlRecord, fetched: Fetched, updated: bool = False
    ) -> None:
        """Fold `fetched` into the record unless `updated`, and judge its zip
        when there is one to judge."""
        try:
            if not updated and not update_record(
                record, fetched, self.today, self.version
            ):
                self.count(f"status {fetched.status or 'error'}")
                return
            assert fetched.path is not None
            workdir = fetched.path.with_suffix(".d")
            with self.judging:
                started = time.monotonic()
                result, peak = isolated(
                    judge_item,
                    (fetched.path, workdir, date.fromisoformat(self.today)),
                    self.settings.worker_memory,
                )
            log.info(
                "%s: judged %d MB in %.1fs, peak %d MB resident",
                url,
                fetched.path.stat().st_size // 1_000_000,
                time.monotonic() - started,
                peak // 1_000_000,
            )
            record.judged_version = self.version
            if isinstance(result, WorkerError):
                log.warning("%s: %s", url, result)
                error = str(result)
                record.judge_error = (
                    "memory" if "Memory" in error or "Broken" in error else error
                )
                record.verdicts, record.facts = {}, {}
                self.count("unjudged")
                return
            record.judge_error = result.get("error")
            record.verdicts = result["verdicts"]
            record.facts = result["facts"]
            self.count("judged")
        finally:
            if fetched.path is not None:
                fetched.path.unlink(missing_ok=True)
                shutil.rmtree(fetched.path.with_suffix(".d"), ignore_errors=True)

    def host(self, urls: list[str]) -> None:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=self.settings.timeout,
            follow_redirects=True,
        ) as client:
            for index, url in enumerate(urls):
                if index:
                    time.sleep(self.settings.per_host_delay)
                try:
                    self.one(client, url)
                except Exception:
                    log.exception("%s failed", url)
                    self.count("failed")

    def guarded(self, url: str, entry: Stored) -> None:
        try:
            self.stored(url, entry)
        except Exception:
            log.exception("%s failed", url)
            self.count("failed")

    def all(self, urls: list[str]) -> dict[str, int]:
        self.settings.workdir.mkdir(parents=True, exist_ok=True)
        entries = {url: entry for url in urls if (entry := lookup(self.index, url))}
        rest = [url for url in urls if url not in entries]
        # Host queues first: their pauses make them the longest tasks.
        tasks: list[Callable[[], None]] = [
            partial(self.host, group) for group in by_host(rest)
        ]
        tasks += [partial(self.guarded, url, entry) for url, entry in entries.items()]
        with ThreadPoolExecutor(max_workers=self.settings.concurrency) as pool:
            list(pool.map(lambda task: task(), tasks))
        return dict(self.counts)
