import httpx
import respx

from gtfs_zone_crimes.fetch import Fetched, fetch, sniff, update_record
from gtfs_zone_crimes.record import UrlRecord
from tests.conftest import fixture_files, make_zip

URL = "https://example.org/gtfs.zip"
ZIP = make_zip(fixture_files())


def test_sniff():
    assert sniff(ZIP[:512]) == "zip"
    assert sniff(b"  <!DOCTYPE html><html>") == "html"
    assert sniff(b'{"error": "key"}') == "json"
    assert sniff(b"<?xml version='1.0'?>") == "xml"
    assert sniff(b"") == "empty"


@respx.mock
def test_fetch_streams_and_hashes(tmp_path):
    respx.get(URL).respond(200, content=ZIP, headers={"ETag": '"v1"'})
    with httpx.Client() as client:
        out = fetch(client, URL, None, "0.1.0", tmp_path, 10_000_000)
    assert out.status == 200
    assert out.kind == "zip"
    assert out.etag == '"v1"'
    assert out.path.read_bytes() == ZIP


@respx.mock
def test_fetch_is_conditional(tmp_path):
    route = respx.get(URL).respond(304)
    record = UrlRecord(
        url=URL,
        etag='"v1"',
        last_modified="Mon, 26 Oct 2026 10:00:00 GMT",
        kind="zip",
        judged_version="0.1.0",
    )
    with httpx.Client() as client:
        out = fetch(client, URL, record, "0.1.0", tmp_path, 10_000_000)
        assert out.status == 304
        assert route.calls.last.request.headers["If-None-Match"] == '"v1"'
        # A new version needs the bytes again.
        fetch(client, URL, record, "0.2.0", tmp_path, 10_000_000)
        assert "If-None-Match" not in route.calls.last.request.headers


@respx.mock
def test_fetch_gives_up_on_huge_bodies(tmp_path):
    respx.get(URL).respond(200, content=ZIP)
    with httpx.Client() as client:
        out = fetch(client, URL, None, "0.1.0", tmp_path, 100)
    assert out.path is None
    assert out.error == "larger than 100 bytes"
    assert not list(tmp_path.iterdir())


def test_update_record_logs_changes(tmp_path):
    record = UrlRecord(url=URL)
    first = Fetched(status=200, etag='"a"', sha256="x", kind="zip", path=tmp_path)
    assert update_record(record, first, "2026-10-25", "0.1.0")
    assert record.log == []
    record.judged_version = "0.1.0"
    same = Fetched(status=200, etag='"b"', sha256="x", kind="zip", path=tmp_path)
    assert not update_record(record, same, "2026-10-26", "0.1.0")
    assert record.log[-1].validators_changed and not record.log[-1].sha_changed
    assert not update_record(record, Fetched(status=304), "2026-10-27", "0.1.0")
    assert len(record.log) == 2


def test_update_record_clears_verdicts_when_the_zip_goes(tmp_path):
    record = UrlRecord(url=URL, sha256="x", kind="zip", verdicts={"russian-doll": None})
    page = Fetched(status=200, sha256="y", kind="html", path=tmp_path)
    assert not update_record(record, page, "2026-10-26", "0.1.0")
    assert record.kind == "html"
    assert record.verdicts == {}
