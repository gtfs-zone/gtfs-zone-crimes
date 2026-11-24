import httpx
import respx

from gtfs_zone_crimes.catalog import SLUGS_URL, fetch_slugs, parse_feeds

URL = "https://example.org/gtfs.zip"


def entry(feed_id):
    return {"feedId": feed_id, "name": feed_id, "urls": {"scheduled": [URL]}}


def test_feed_summary_carries_its_sites_slug():
    doc = {"feeds": [entry("f-1"), entry("f-2")]}
    with_slug, without = parse_feeds(doc, {"f-1": "clean-transit"})
    assert with_slug.summary()["slug"] == "clean-transit"
    assert "slug" not in without.summary()


@respx.mock
def test_fetch_slugs():
    respx.get(SLUGS_URL).respond(json={"f-1": "a", "f-2": 3})
    with httpx.Client() as client:
        assert fetch_slugs(client) == {"f-1": "a"}


@respx.mock
def test_fetch_slugs_is_empty_when_unreadable():
    respx.get(SLUGS_URL).respond(503)
    with httpx.Client() as client:
        assert fetch_slugs(client) == {}
    respx.get(SLUGS_URL).respond(text="<html>")
    with httpx.Client() as client:
        assert fetch_slugs(client) == {}
