from datetime import timedelta

from gtfs_zone_crimes.artifacts import build_crimes
from gtfs_zone_crimes.catalog import parse_feed
from gtfs_zone_crimes.record import UrlRecord
from tests.conftest import TODAY, feed

URL = "https://example.org/gtfs.zip"


def build(feeds, records=None, previous=None, today=TODAY):
    return build_crimes(
        feeds, records or {}, today, previous, "2026-10-26T14:00:00+00:00"
    )


def keyed(doc):
    return {(c["crime"], c["feedId"]): c for c in doc["convictions"]}


def test_new_conviction_starts_today():
    doc = build([feed(auth=frozenset({"scheduled"}))])
    conviction = keyed(doc)[("api-key", "f-0123456789")]
    assert conviction["since"] == "2026-10-26"
    assert doc["feeds"]["f-0123456789"]["name"] == "Clean Transit"
    counts = {c["slug"]: c for c in doc["crimes"]}
    assert counts["api-key"]["convicted"] == 1
    assert counts["api-key"]["judged"] == 1


def test_conviction_keeps_its_date():
    keyed_feed = feed(auth=frozenset({"scheduled"}))
    first = build([keyed_feed], today=TODAY - timedelta(days=10))
    second = build([keyed_feed], previous=first)
    assert keyed(second)[("api-key", "f-0123456789")]["since"] == "2026-10-16"


def test_acquittal_is_a_pardon():
    first = build(
        [feed(auth=frozenset({"scheduled"}))], today=TODAY - timedelta(days=3)
    )
    second = build([feed()], previous=first)
    assert not second["convictions"]
    assert second["pardons"] == [
        {
            "crime": "api-key",
            "feedId": "f-0123456789",
            "since": "2026-10-23",
            "pardoned": "2026-10-26",
            "summary": "Static schedule behind an API key",
        }
    ]
    # A second run the same day keeps the pardon once.
    third = build([feed()], previous=second)
    assert len(third["pardons"]) == 1


def test_old_pardons_expire():
    first = build(
        [feed(auth=frozenset({"scheduled"}))], today=TODAY - timedelta(days=200)
    )
    second = build([feed()], previous=first, today=TODAY - timedelta(days=100))
    assert second["pardons"]
    assert not build([feed()], previous=second)["pardons"]


def test_unjudged_conviction_stands():
    verdicts = {"beauty-queen": {"guilty": True, "summary": "1 cm", "metric": 9.0}}
    records = {URL: UrlRecord(url=URL, verdicts=verdicts)}
    first = build([feed()], records, today=TODAY - timedelta(days=5))
    # The zip could not be judged today: no verdict at all.
    second = build([feed()], {URL: UrlRecord(url=URL)}, previous=first)
    assert keyed(second)[("beauty-queen", "f-0123456789")]["since"] == "2026-10-21"


def test_vanished_feed_is_dropped_not_pardoned():
    first = build([feed(auth=frozenset({"scheduled"}))])
    second = build([], previous=first)
    assert not second["convictions"]
    assert not second["pardons"]
    assert not second["feeds"]


def test_convictions_rank_worst_first():
    feeds = [
        feed(
            id="f-000000000a", scheduled_state="down", since="2026-09-01T00:00:00+00:00"
        ),
        feed(id="f-000000000b", scheduled_state="down", never_up=True),
    ]
    doc = build(feeds)
    assert [c["feedId"] for c in doc["convictions"]] == ["f-000000000b", "f-000000000a"]


def test_feed_summary_carries_open_realtime_urls():
    parsed = parse_feed(
        {
            "feedId": "f-0123456789",
            "name": "Clean Transit",
            "urls": {
                "scheduled": [URL],
                "vehicles": ["https://example.org/vp.pb", "https://mirror.org/vp.pb"],
                "trip_updates": ["https://example.org/tu.pb"],
            },
            "auth": ["trip_updates"],
        }
    )
    assert parsed.summary() == {
        "name": "Clean Transit",
        "url": URL,
        "realtime": {"vehicles": "https://example.org/vp.pb"},
    }
