"""Download and judge every scheduled URL politely: hosts in parallel, one
request at a time per host with a pause between them, and a bounded number of
zips judged at once."""

from __future__ import annotations

import logging
import shutil
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx

from gtfs_zone_crimes.fetch import USER_AGENT, fetch, update_record
from gtfs_zone_crimes.judge import judge_zip
from gtfs_zone_crimes.pool import WorkerError, isolated
from gtfs_zone_crimes.record import UrlRecord

if TYPE_CHECKING:
    from pathlib import Path

    from gtfs_zone_crimes.settings import Settings

log = logging.getLogger(__name__)


def judge_item(item: tuple[Path, Path]) -> dict[str, Any]:
    return judge_zip(*item)


def by_host(urls: list[str]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        groups[urlsplit(url).netloc.lower()].append(url)
    # Busiest hosts first, so the longest queue is not started last.
    return sorted(groups.values(), key=len, reverse=True)


class Judge:
    """Fetches and judges URLs into `records`, which it updates in place."""

    def __init__(
        self,
        records: dict[str, UrlRecord],
        settings: Settings,
        today: str,
        version: str,
    ) -> None:
        self.records = records
        self.settings = settings
        self.today = today
        self.version = version
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
        try:
            if not update_record(record, fetched, self.today, self.version):
                self.count(f"status {fetched.status or 'error'}")
                return
            assert fetched.path is not None
            workdir = fetched.path.with_suffix(".d")
            with self.judging:
                started = time.monotonic()
                result, peak = isolated(
                    judge_item, (fetched.path, workdir), self.settings.worker_memory
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

    def all(self, urls: list[str]) -> dict[str, int]:
        self.settings.workdir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=self.settings.concurrency) as pool:
            list(pool.map(self.host, by_host(urls)))
        return dict(self.counts)
