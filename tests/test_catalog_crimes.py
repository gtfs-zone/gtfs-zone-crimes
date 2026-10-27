from gtfs_zone_crimes.crime import CatalogCase
from gtfs_zone_crimes.crimes import (
    api_key,
    dead_link,
    disguised_as_html,
    eternal_service,
    every_day_is_special,
    expired,
    groundhog_day,
)
from gtfs_zone_crimes.record import LogEntry, UrlRecord
from tests.conftest import TODAY, feed


def case(record: UrlRecord | None = None, **overrides) -> CatalogCase:
    return CatalogCase(feed=feed(**overrides), today=TODAY, record=record)


def record(**fields) -> UrlRecord:
    return UrlRecord(url="https://example.org/gtfs.zip", **fields)


def test_api_key_only_for_the_schedule():
    assert api_key.judge(case(auth=frozenset({"scheduled"}))).guilty
    assert not api_key.judge(case(auth=frozenset({"vehicles"}))).guilty


def test_dead_link():
    assert (
        dead_link.judge(case(scheduled_state="down", never_up=True)).summary
        == "Never seen up"
    )
    down = case(scheduled_state="down", since="2026-09-01T10:00:00+00:00")
    assert dead_link.judge(down).summary == "Down for 55 days"
    recent = case(scheduled_state="down", since="2026-10-20T10:00:00+00:00")
    assert not dead_link.judge(recent).guilty
    assert not dead_link.judge(case()).guilty
    assert dead_link.judge(case(scheduled_state="unknown")) is None


def test_expired_prefers_the_judged_zip():
    stale = record(facts={"serviceEnd": "2026-10-01"})
    assert expired.judge(case(stale, service_end="2027-01-01")).metric == 25
    assert not expired.judge(case(service_end="2027-01-01")).guilty
    assert expired.judge(case()) is None


def test_eternal_service():
    verdict = eternal_service.judge(case(record(facts={"serviceEnd": "2099-12-31"})))
    assert verdict.summary == "Service runs until 2099-12-31, 73 years from now"
    assert not eternal_service.judge(case(service_end="2028-01-01")).guilty


def test_disguised_as_html():
    assert (
        disguised_as_html.judge(case(record(kind="html"))).summary
        == "200 OK, then an HTML page"
    )
    assert not disguised_as_html.judge(case(record(kind="zip"))).guilty
    assert disguised_as_html.judge(case()) is None


def test_groundhog_day_no_validators():
    verdict = groundhog_day.judge(case(record(status=200, kind="zip")))
    assert verdict.guilty


def test_groundhog_day_false_changes():
    false = LogEntry(date="2026-10-20", validators_changed=True, sha_changed=False)
    real = LogEntry(date="2026-10-21", validators_changed=True, sha_changed=True)
    quiet = LogEntry(date="2026-10-22", validators_changed=False, sha_changed=False)
    guilty = record(status=200, etag='"a"', log=[false, false, real, false, quiet])
    assert groundhog_day.judge(case(guilty)).summary == (
        "New validators on 3 of the last 5 checks, same bytes every time"
    )
    innocent = record(status=304, etag='"a"', log=[false, real, quiet, quiet])
    assert not groundhog_day.judge(case(innocent)).guilty
    assert groundhog_day.judge(case(record(status=500))) is None


def test_every_day_is_special():
    sprawl = record(facts={"weeklyRows": 0, "datedRows": 12000})
    assert every_day_is_special.judge(case(sprawl)).summary == (
        "No weekly calendar, 12,000 calendar_dates rows instead"
    )
    weekly = record(facts={"weeklyRows": 3, "datedRows": 12000})
    assert not every_day_is_special.judge(case(weekly)).guilty
    assert every_day_is_special.judge(case()) is None


def test_every_day_is_special_from_a_zip(judge_files):
    rows = ["service_id,date,exception_type"]
    rows += [
        f"WK,2026{m:02d}{d:02d},1"
        for m in range(1, 13)
        for d in range(1, 29)
        for _ in range(16)
    ]
    judge_files({"calendar.txt": "", "calendar_dates.txt": "\n".join(rows)})
    assert judge_files.facts["weeklyRows"] == 0
    assert judge_files.facts["datedRows"] == 5376
