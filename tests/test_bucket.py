import obstore
from obstore.store import MemoryStore

from gtfs_zone_crimes.pipeline.bucket import Bucket, BucketSettings

SETTINGS = BucketSettings(
    endpoint="http://garage:3900",
    bucket="crimes.gtfs.zone",
    access_key="x",
    secret_key="x",
    region="garage",
)


def test_json_roundtrip():
    bucket = Bucket(SETTINGS, store=MemoryStore())
    assert bucket.get_json("crimes.json") is None
    bucket.put_json("crimes.json", {"convictions": ["Lbo"]})
    assert bucket.get_json("crimes.json") == {"convictions": ["Lbo"]}


def test_private_json_is_not_cached():
    store = MemoryStore()
    Bucket(SETTINGS, store=store).put_json("records.json", {}, public=False)
    attributes = obstore.get(store, "records.json").attributes
    assert attributes["Cache-Control"] == "no-store"
    assert attributes["Content-Type"] == "application/json"


def test_s3_store_builds_from_settings():
    assert Bucket(SETTINGS).name == "crimes.gtfs.zone"
