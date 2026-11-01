from gtfs_zone_crimes.crime import Ref, Verdict, linked
from tests.conftest import fixture_files


def spans(verdict: Verdict | None) -> list[list[tuple[str, str, str]]]:
    """Each ref as (type, id, the text at its offset), checked against its text."""
    assert verdict is not None
    assert verdict.guilty
    assert len(verdict.refs) == len(verdict.details)
    out = []
    for line, refs in zip(verdict.details, verdict.refs, strict=True):
        units = line.encode("utf-16-le")
        row = []
        for ref in refs:
            at, text = int(ref["at"]), str(ref["text"])
            found = units[at * 2 : at * 2 + len(text.encode("utf-16-le"))]
            assert found.decode("utf-16-le") == text
            row.append((str(ref["type"]), str(ref["id"]), text))
        out.append(row)
    return out


def test_linked_counts_utf16_units():
    line, refs = linked(
        "\U0001f68c ", ("stop", 7, "Gare"), " (", ("route", None, "x"), ")"
    )
    assert line == "\U0001f68c Gare (x)"
    assert refs == [{"type": "stop", "id": "7", "at": 3, "text": "Gare"}]


def test_refs_round_trip_and_are_left_out_when_empty():
    lines: list[tuple[str, list[Ref]]] = [linked(("stop", "A", "Ash")), linked("plain")]
    verdict = Verdict.lines(lines, summary="s", metric=1)
    assert Verdict.from_json(verdict.to_json()) == verdict
    assert (
        "refs" not in Verdict.lines([linked("plain")], summary="s", metric=1).to_json()
    )


def test_null_island_links_the_stop(judge_files):
    stops = fixture_files()["stops.txt"].replace("45.5100,-122.6000", "0.0,0.0")
    verdict = judge_files({"stops.txt": stops})["null-island"]
    assert spans(verdict) == [[("stop", "B", "Main St & 5th Ave")]]


def test_invisible_ink_links_the_route(judge_files):
    routes = fixture_files()["routes.txt"].replace("0055AA,FFFFFF", "FFFFFF,FFFFFF")
    verdict = judge_files({"routes.txt": routes})["invisible-ink"]
    assert spans(verdict) == [[("route", "R1", "1")]]


def test_supersonic_links_stops_and_route(judge_files):
    stops = fixture_files()["stops.txt"].replace(
        "45.5100,-122.6000", "46.5100,-122.6000"
    )
    verdict = judge_files({"stops.txt": stops})["supersonic"]
    kinds = [[kind for kind, _, _ in row] for row in spans(verdict)]
    assert kinds[0][:3] == ["stop", "stop", "route"]
    assert any(len(row) > 3 for row in kinds)


def test_time_travel_links_route_and_stops(judge_files):
    times = fixture_files()["stop_times.txt"].replace(
        "T1,08:03:00,08:03:00", "T1,07:55:00,07:55:00"
    )
    verdict = judge_files({"stop_times.txt": times})["time-travel"]
    assert spans(verdict)[0] == [
        ("route", "R1", "1"),
        ("stop", "B", "Main St & 5th Ave"),
        ("stop", "A", "Main St & 1st Ave"),
    ]


def test_shouting_links_the_first_id_of_each_name(judge_files):
    rows = ["stop_id,stop_name,stop_lat,stop_lon"]
    rows += [f"S{i},MAIN ST & {i % 11}TH AVE,45.5,-122.6" for i in range(12)]
    rows += ["A,Main St & 1st Ave,45.5000,-122.6000"]
    verdict = judge_files({"stops.txt": "\n".join(rows)})["shouting"]
    assert spans(verdict)[0] == [("stop", "S0", "MAIN ST & 0TH AVE")]


def test_grand_central_links_the_station(judge_files):
    from tests.test_content import grand_central

    verdict = judge_files(grand_central(3, 0.004))["grand-central-everywhere"]
    assert all(row and row[0][0] == "stop" for row in spans(verdict))
