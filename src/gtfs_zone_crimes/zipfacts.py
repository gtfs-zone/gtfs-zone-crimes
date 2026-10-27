"""What a zip's central directory says: entry names, sizes and compression."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Entry:
    name: str
    size: int
    method: int

    @property
    def path(self) -> PurePosixPath:
        return PurePosixPath(self.name)

    @property
    def is_dir(self) -> bool:
        return self.name.endswith("/")


@dataclass(frozen=True)
class ZipFacts:
    entries: tuple[Entry, ...]

    @property
    def files(self) -> list[Entry]:
        return [entry for entry in self.entries if not entry.is_dir]

    @property
    def root(self) -> str | None:
        """The folder holding stops.txt ('' at the top), or None when the zip
        has no stops.txt outside a nested zip."""
        folders = sorted(
            (
                str(entry.path.parent)
                for entry in self.files
                if entry.path.name == "stops.txt"
                and not entry.name.startswith("__MACOSX/")
            ),
            key=len,
        )
        if not folders:
            return None
        return "" if folders[0] == "." else folders[0] + "/"

    def member(self, filename: str) -> Entry | None:
        """The GTFS file `filename` under the root."""
        root = self.root
        if root is None:
            return None
        for entry in self.files:
            if entry.name == root + filename:
                return entry
        return None

    def uncompressed_bytes(self) -> int:
        return sum(entry.size for entry in self.files)


def read_zipfacts(path: Path) -> ZipFacts:
    with zipfile.ZipFile(path) as archive:
        entries = tuple(
            Entry(
                name=info.filename,
                size=info.file_size,
                method=info.compress_type,
            )
            for info in archive.infolist()
        )
    return ZipFacts(entries=entries)
