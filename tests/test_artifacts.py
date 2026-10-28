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
            "revision": 1,
        }
    ]
    # A second run the same day keeps the pardon once.
    third = build([feed()], previous=second)
    assert len(third["pardons"]) == 1


def test_acquittal_across_a_revision_is_not_a_pardon():
    first = build(
        [feed(auth=frozenset({"scheduled"}))], today=TODAY - timedelta(days=3)
    )
    for crime in first["crimes"]:
        crime["revision"] = 0
    second = build([feed()], previous=first)
    assert not second["convictions"]
    assert not second["pardons"]


def test_pardons_of_other_revisions_are_dropped():
    pardon = {
        "crime": "api-key",
        "feedId": "f-0123456789",
        "since": "2026-10-01",
        "pardoned": "2026-10-20",
        "summary": "",
    }
    unrevised = build([feed()], previous={"pardons": [pardon]})
    assert not unrevised["pardons"]
    older = build([feed()], previous={"pardons": [{**pardon, "revision": 0}]})
    assert not older["pardons"]
    current = build([feed()], previous={"pardons": [{**pardon, "revision": 1}]})
    assert len(current["pardons"]) == 1


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


def test_bigger_feeds_rank_first():
    feeds = [
        feed(id="f-000000000a", auth=frozenset({"scheduled"}), trips=40),
        feed(id="f-000000000b", auth=frozenset({"scheduled"}), trips=90_000),
    ]
    doc = build(feeds)
    assert [c["feedId"] for c in doc["convictions"]] == ["f-000000000b", "f-000000000a"]
    assert doc["feeds"]["f-000000000b"]["trips"] == 90_000


def test_breadth_outweighs_a_little_size():
    big = UrlRecord(
        url=URL,
        facts={"trips": 2000},
        verdicts={"time-travel": {"guilty": True, "summary": "1", "metric": 1}},
    )
    wide_url = "https://example.org/wide.zip"
    wide = UrlRecord(
        url=wide_url,
        facts={"trips": 1000},
        verdicts={"time-travel": {"guilty": True, "summary": "500", "metric": 500}},
    )
    feeds = [
        feed(id="f-000000000a"),
        feed(id="f-000000000b", scheduled_urls=(wide_url,)),
    ]
    doc = build(feeds, {URL: big, wide_url: wide})
    assert [c["feedId"] for c in doc["convictions"]] == ["f-000000000b", "f-000000000a"]


def test_expired_feeds_are_ignored():
    first = build([feed(auth=frozenset({"scheduled"}))])
    second = build(
        [feed(auth=frozenset({"scheduled"}), service_end="2026-10-01")], previous=first
    )
    assert not second["convictions"]
    assert not second["pardons"]
    assert second["feedCount"] == 0


def test_conviction_past_its_service_is_pardoned():
    def record(until):
        verdict = {"guilty": True, "summary": "1", "until": until}
        return {URL: UrlRecord(url=URL, verdicts={"time-travel": verdict})}

    first = build([feed()], record("2026-10-20"), today=TODAY - timedelta(days=10))
    assert "until" not in keyed(first)[("time-travel", "f-0123456789")]
    second = build([feed()], record("2026-10-20"), previous=first)
    assert not second["convictions"]
    assert second["pardons"][0]["crime"] == "time-travel"


def test_pardons_of_removed_crimes_are_dropped():
    previous = {
        "pardons": [
            {
                "crime": "expired",
                "feedId": "f-0123456789",
                "since": "2026-10-01",
                "pardoned": "2026-10-20",
                "summary": "",
            }
        ]
    }
    assert not build([feed()], previous=previous)["pardons"]


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
