import hashlib
from datetime import UTC, datetime

import obstore
import respx
from gtfs_zone_feed_fetch.store import (
    HTTP_ERROR,
    INDEX_KEY,
    NOT_MODIFIED,
    OK,
    TOO_LARGE,
    Stored,
    index_body,
)
from gtfs_zone_feed_fetch.urls import normalize_url
from obstore.store import MemoryStore

from gtfs_zone_crimes.fetch import from_index, update_record
from gtfs_zone_crimes.pipeline.bucket import Bucket, BucketSettings
from gtfs_zone_crimes.record import UrlRecord
from gtfs_zone_crimes.run import Judge
from gtfs_zone_crimes.session import read_index
from gtfs_zone_crimes.settings import Settings
from tests.conftest import fixture_files, make_zip

URL = "https://example.org/gtfs.zip"
OTHER = "https://other.example.org/gtfs.zip"
ZIP = make_zip(fixture_files())
SHA = hashlib.sha256(ZIP).hexdigest()
KEY = f"gtfs/{SHA}.zip"
TODAY = "2026-10-26"
VERSION = "0.1.0"
SETTINGS = BucketSettings(
    endpoint="http://garage:3900",
    bucket="gtfs-zips",
    access_key="x",
    secret_key="x",
    region="garage",
)


def entry(**fields) -> Stored:
    base = {
        "url": URL,
        "checked": "2026-10-26T09:10:00+00:00",
        "outcome": OK,
        "status": 200,
        "key": KEY,
        "sha256": SHA,
        "bytes": len(ZIP),
        "kind": "zip",
        "etag": '"v1"',
    }
    return Stored(**{**base, **fields})


def zips(*entries: Stored, objects: dict[str, bytes] | None = None) -> Bucket:
    store = MemoryStore()
    for key, body in (objects if objects is not None else {KEY: ZIP}).items():
        obstore.put(store, key, body)
    index = {normalize_url(e.url): e for e in entries}
    generated = datetime(2026, 10, 26, tzinfo=UTC)
    obstore.put(store, INDEX_KEY, index_body(index, generated, 4 << 30))
    return Bucket(SETTINGS, store=store)


def judge(records: dict[str, UrlRecord], bucket: Bucket, tmp_path, urls=(URL,)):
    settings = Settings(workdir=tmp_path, worker_memory=0, per_host_delay=0)
    run = Judge(records, settings, TODAY, VERSION, read_index(bucket), bucket)
    return run.all(list(urls))


def test_from_index_maps_outcomes():
    ok = from_index(entry(), 10_000_000)
    assert (ok.status, ok.sha256, ok.kind, ok.etag) == (200, SHA, "zip", '"v1"')
    # A 304 still names the stored body, so a new version can judge it.
    unchanged = from_index(entry(outcome=NOT_MODIFIED, status=304), 10_000_000)
    assert (unchanged.status, unchanged.sha256) == (304, SHA)
    # The body kept from before a failure is not today's answer.
    failed = from_index(entry(outcome=HTTP_ERROR, status=503), 10_000_000)
    assert (failed.status, failed.sha256) == (503, None)
    assert from_index(entry(), 100).error == "larger than 100 bytes"
    assert from_index(entry(outcome=TOO_LARGE), 10_000_000).sha256 is None


def test_update_record_judges_a_304_body_for_a_new_version():
    record = UrlRecord(url=URL, sha256=SHA, kind="zip", judged_version="0.0.9")
    fetched = from_index(entry(outcome=NOT_MODIFIED, status=304), 10_000_000)
    assert update_record(record, fetched, TODAY, VERSION)
    assert record.status == 304
    assert not record.log[-1].sha_changed


@respx.mock
def test_indexed_url_is_judged_from_the_store(tmp_path):
    route = respx.get(URL)
    records: dict[str, UrlRecord] = {}
    counts = judge(records, zips(entry()), tmp_path)
    assert not route.called
    assert counts == {"indexed": 1, "judged": 1}
    record = records[URL]
    assert (record.sha256, record.etag, record.judged_version) == (SHA, '"v1"', VERSION)
    assert record.facts["trips"]
    assert not list(tmp_path.iterdir())
    # Same sha256 and version: nothing is read or judged again.
    counts = judge(records, zips(entry(etag='"v2"'), objects={}), tmp_path)
    assert counts == {"indexed": 1, "status 200": 1}
    assert records[URL].log[-1].validators_changed


@respx.mock
def test_missing_object_is_judged_next_run(tmp_path):
    records = {URL: UrlRecord(url=URL, sha256="old", kind="zip")}
    counts = judge(records, zips(entry(), objects={}), tmp_path)
    assert counts == {"indexed": 1, "not stored": 1}
    assert records[URL].judged_version is None
    assert not list(tmp_path.iterdir())


@respx.mock
def test_unindexed_url_falls_back_to_a_get(tmp_path):
    respx.get(OTHER).respond(200, content=ZIP)
    failed = respx.get(URL)
    records: dict[str, UrlRecord] = {}
    counts = judge(
        records,
        zips(entry(outcome=HTTP_ERROR, status=503)),
        tmp_path,
        urls=(URL, OTHER),
    )
    assert not failed.called
    assert records[URL].status == 503
    assert records[OTHER].sha256 == SHA
    assert counts == {"indexed": 1, "status 503": 1, "judged": 1}


def test_missing_index_downloads_everything():
    assert read_index(Bucket(SETTINGS, store=MemoryStore())) == {}


def test_download_streams_to_a_file(tmp_path):
    bucket = zips()
    assert bucket.download(KEY, tmp_path / "a.zip")
    assert (tmp_path / "a.zip").read_bytes() == ZIP
    assert not bucket.download("gtfs/none.zip", tmp_path / "b.zip")
    assert bucket.get("gtfs/none.zip") is None


def test_zips_settings_from_env(monkeypatch):
    monkeypatch.delenv("ZIPS_S3_ENDPOINT", raising=False)
    assert BucketSettings.zips_from_env() is None
    monkeypatch.setenv("ZIPS_S3_ENDPOINT", "http://garage:3900")
    monkeypatch.setenv("ZIPS_S3_ACCESS_KEY", "a")
    monkeypatch.setenv("ZIPS_S3_SECRET_KEY", "b")
    assert BucketSettings.zips_from_env().bucket == "gtfs-zips"


@respx.mock
def test_index_is_ignored_without_a_store(tmp_path):
    respx.get(URL).respond(304)
    settings = Settings(workdir=tmp_path, worker_memory=0, per_host_delay=0)
    index = {normalize_url(URL): entry()}
    counts = Judge({}, settings, TODAY, VERSION, index).all([URL])
    assert counts == {"status 304": 1}
