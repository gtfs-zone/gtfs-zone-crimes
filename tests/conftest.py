import io
import zipfile
from datetime import date
from pathlib import Path

import pytest

from gtfs_zone_crimes.catalog import CatalogFeed
from gtfs_zone_crimes.crime import Verdict
from gtfs_zone_crimes.judge import judge_zip

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 26)


def make_zip(
    files: dict[str, str | bytes], method: int = zipfile.ZIP_DEFLATED
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=method) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def fixture_files(name: str = "clean") -> dict[str, str]:
    """The text files in tests/fixtures/<name>/ by file name."""
    return {path.name: path.read_text() for path in (FIXTURES / name).glob("*.txt")}


def feed(**overrides) -> CatalogFeed:
    fields = {
        "id": "f-0123456789",
        "name": "Clean Transit",
        "subtitle": None,
        "place": "Portland, Oregon, United States",
        "scheduled_urls": ("https://example.org/gtfs.zip",),
        "scheduled_state": "up",
        "auth": frozenset(),
        "never_up": False,
        "since": "2026-01-01T00:00:00+00:00",
        "service_end": None,
    }
    return CatalogFeed(**{**fields, **overrides})


@pytest.fixture
def judge_files(tmp_path):
    """Judge a zip of `files` (the clean fixture with overrides by default)."""

    def run(
        overrides: dict[str, str | bytes] | None = None,
        base: str | None = "clean",
        method: int = zipfile.ZIP_DEFLATED,
    ) -> dict[str, Verdict | None]:
        files = {**(fixture_files(base) if base else {}), **(overrides or {})}
        path = tmp_path / "feed.zip"
        path.write_bytes(make_zip(files, method))
        result = judge_zip(path, tmp_path / "work", TODAY)
        verdicts = result["verdicts"]
        run.facts = result["facts"]
        return {
            slug: Verdict.from_json(v) if v else None for slug, v in verdicts.items()
        }

    return run
