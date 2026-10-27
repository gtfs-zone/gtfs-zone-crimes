"""Run settings from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def env_list(name: str) -> frozenset[str]:
    return frozenset(
        v.strip() for v in os.environ.get(name, "").split(",") if v.strip()
    )


@dataclass(frozen=True)
class Settings:
    # Hosts downloaded from at once; each host gets one request at a time.
    concurrency: int = 8
    # Zips judged at once, each in a process of its own.
    workers: int = 2
    # Address space per judging process; a feed that needs more is unjudged.
    worker_memory: int = 5_000_000_000
    per_host_delay: float = 1.0
    timeout: float = 120.0
    max_download: int = 2_000_000_000
    workdir: Path = field(
        default_factory=lambda: Path(os.environ.get("TMPDIR", "/tmp"))
    )
    # Judge only these feed ids (all when empty); for local runs.
    only: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            concurrency=int(os.environ.get("CRIMES_CONCURRENCY", "8")),
            workers=int(os.environ.get("CRIMES_WORKERS", "2")),
            worker_memory=int(os.environ.get("CRIMES_WORKER_MEMORY", "5000000000")),
            per_host_delay=float(
                os.environ.get("CRIMES_PER_HOST_DELAY_SECONDS", "1.0")
            ),
            timeout=float(os.environ.get("CRIMES_TIMEOUT_SECONDS", "120")),
            max_download=int(os.environ.get("CRIMES_MAX_DOWNLOAD_BYTES", "2000000000")),
            workdir=Path(
                os.environ.get("CRIMES_WORKDIR", os.environ.get("TMPDIR", "/tmp"))
            ),
            only=env_list("CRIMES_FEEDS"),
        )
