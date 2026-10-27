from gtfs_zone_crimes.crime import Verdict
from tests.conftest import fixture_files

CONTENT = [
    "supersonic",
    "beauty-queen",
    "deja-vu",
    "invisible-ink",
    "null-island",
    "time-travel",
    "shouting",
    "grand-central-everywhere",
]


def guilty(verdict: Verdict | None) -> bool:
    assert verdict is not None
    return verdict.guilty


def test_clean_feed_is_acquitted_of_everything(judge_files):
    verdicts = judge_files()
    for slug in [*CONTENT, "russian-doll", "zip-in-name-only"]:
        assert verdicts[slug] == Verdict(guilty=False), slug


def test_clean_feed_facts(judge_files):
    judge_files()
    assert judge_files.facts == {
        "weeklyRows": 1,
        "datedRows": 1,
        "serviceStart": "2026-01-01",
        "serviceEnd": "2027-12-31",
    }


def test_supersonic_bus(judge_files):
    stops = fixture_files()["stops.txt"].replace(
        "45.5600,-122.6000", "46.5600,-122.6000"
    )
    verdict = judge_files({"stops.txt": stops})["supersonic"]
    assert guilty(verdict)
    assert verdict.summary.startswith("Oak St Transit Center to Elm St & Park Rd")
    assert "bus" in verdict.summary


def test_supersonic_gives_a_minute_of_rounding(judge_files):
    # 3.3 km in 0 minutes is at most 200 km/h once rounding is allowed for.
    times = fixture_files()["stop_times.txt"].replace(
        "T1,08:15:00,08:15:00", "T1,08:08:00,08:08:00"
    )
    assert not guilty(judge_files({"stop_times.txt": times})["supersonic"])


def test_supersonic_limit_depends_on_mode(judge_files):
    stops = fixture_files()["stops.txt"].replace(
        "45.5600,-122.6000", "45.6500,-122.6000"
    )
    # C to D is 13 km in 7 minutes: 114 km/h, fine for a bus, not for a gondola.
    assert not guilty(judge_files({"stops.txt": stops})["supersonic"])
    routes = fixture_files()["routes.txt"].replace("Main Street,3", "Main Street,6")
    assert guilty(judge_files({"stops.txt": stops, "routes.txt": routes})["supersonic"])


def test_beauty_queen(judge_files):
    rows = ["shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence"]
    rows += [f"S1,{45.5 + i * 0.00001:.6f},-122.600000,{i}" for i in range(6000)]
    verdict = judge_files({"shapes.txt": "\n".join(rows)})["beauty-queen"]
    assert guilty(verdict)
    assert verdict.summary.startswith("111 cm between shape points")


def test_beauty_queen_needs_shapes_to_be_the_biggest_file(judge_files):
    rows = ["shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence"]
    rows += [f"S1,{45.5 + i * 0.00001:.6f},-122.600000,{i}" for i in range(20)]
    padding = "\n".join(f"T9,08:00:00,08:00:00,A,{i}" for i in range(500))
    times = fixture_files()["stop_times.txt"] + padding
    verdicts = judge_files({"shapes.txt": "\n".join(rows), "stop_times.txt": times})
    assert not guilty(verdicts["beauty-queen"])


def test_invisible_ink(judge_files):
    routes = fixture_files()["routes.txt"].replace("0055AA,FFFFFF", "FFFFFF,FFFFFF")
    verdict = judge_files({"routes.txt": routes})["invisible-ink"]
    assert guilty(verdict)
    assert verdict.details == ["1: #FFFFFF on #FFFFFF (1.00:1)"]


def test_null_island(judge_files):
    stops = fixture_files()["stops.txt"].replace("45.5100,-122.6000", "0.0,0.0")
    verdict = judge_files({"stops.txt": stops})["null-island"]
    assert guilty(verdict)
    assert verdict.summary == "1 stop(s) at 0,0"


def test_null_island_swapped_coordinates(judge_files):
    stops = "\n".join(
        [
            "stop_id,stop_name,stop_lat,stop_lon",
            "A,Dam,52.3730,4.8930",
            "B,Centraal,52.3790,4.9000",
            "C,Leidseplein,52.3640,4.8830",
            "D,Museumplein,4.8810,52.3580",
        ]
    )
    verdict = judge_files({"stops.txt": stops})["null-island"]
    assert guilty(verdict)
    assert verdict.summary == "1 stop(s) with latitude and longitude swapped"


def test_time_travel(judge_files):
    times = fixture_files()["stop_times.txt"].replace(
        "T1,08:03:00,08:03:00", "T1,07:55:00,07:55:00"
    )
    verdict = judge_files({"stop_times.txt": times})["time-travel"]
    assert guilty(verdict)
    assert (
        "reaches Main St & 5th Ave 0:05:00 before leaving Main St & 1st Ave"
        in verdict.summary
    )


def test_time_travel_allows_overnight_times(judge_files):
    # T2 in the clean fixture runs past 24:00.
    assert not guilty(judge_files()["time-travel"])


def test_time_travel_departing_before_arriving(judge_files):
    times = fixture_files()["stop_times.txt"].replace(
        "T2,25:05:00,25:06:00", "T2,25:05:00,25:01:00"
    )
    assert guilty(judge_files({"stop_times.txt": times})["time-travel"])


def test_shouting(judge_files):
    rows = ["stop_id,stop_name,stop_lat,stop_lon"]
    rows += [f"S{i},MAIN ST & {i}TH AVE,45.5,-122.6" for i in range(12)]
    rows += [
        "A,Main St & 1st Ave,45.5000,-122.6000",
        "B,Main St & 5th Ave,45.5100,-122.6000",
        "C,Oak St Transit Center,45.5300,-122.6000",
        "D,Elm St & Park Rd,45.5600,-122.6000",
    ]
    verdict = judge_files({"stops.txt": "\n".join(rows)})["shouting"]
    assert guilty(verdict)
    assert verdict.summary == "75% OF STOP NAMES IN CAPITALS"


def test_shouting_ignores_scripts_without_case(judge_files):
    rows = ["stop_id,stop_name,stop_lat,stop_lon"]
    rows += [f"S{i},東京駅前{i}番のりば,35.68,139.76" for i in range(20)]
    assert not guilty(judge_files({"stops.txt": "\n".join(rows)})["shouting"])


def grand_central(route_type: int, spacing: float) -> dict[str, str]:
    stops = ["stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station"]
    times = ["trip_id,arrival_time,departure_time,stop_id,stop_sequence"]
    for i in range(25):
        lat = 45.5 + i * spacing
        stops.append(f"ST{i},Stop {i},{lat:.5f},-122.6,1,")
        stops.append(f"P{i},Stop {i},{lat:.5f},-122.6,0,ST{i}")
        times.append(f"T1,08:{i:02d}:00,08:{i:02d}:00,P{i},{i}")
    return {
        "stops.txt": "\n".join(stops),
        "stop_times.txt": "\n".join(times),
        "routes.txt": f"route_id,route_short_name,route_type\nR1,1,{route_type}",
        "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1",
    }


def test_grand_central_everywhere(judge_files):
    verdict = judge_files(grand_central(3, 0.004))["grand-central-everywhere"]
    assert guilty(verdict)
    assert verdict.summary == "25 bus stops dressed up as stations (100% of bus stops)"


def test_grand_central_spares_coaches(judge_files):
    # Typed as coach.
    assert not guilty(
        judge_files(grand_central(200, 0.004))["grand-central-everywhere"]
    )
    # Typed as bus, but 11 km between stops.
    assert not guilty(judge_files(grand_central(3, 0.1))["grand-central-everywhere"])


def test_crime_that_raises_is_unjudged(judge_files):
    verdicts = judge_files({"routes.txt": ""})
    assert verdicts["invisible-ink"] is None


def shapes(count: int, offset: float, bend: float = 0.0) -> str:
    """`count` 2 km shapes along one street, each moved `offset` degrees east;
    every other one bends `bend` degrees east at its middle point."""
    rows = ["shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence"]
    for n in range(count):
        for i in range(3):
            lon = -122.6 + n * offset + (bend if n % 2 and i == 1 else 0)
            rows.append(f"S{n},{45.5 + i * 0.009:.6f},{lon:.7f},{i}")
    return "\n".join(rows)


def test_deja_vu(judge_files):
    # 2,100 copies a millimetre apart: all but one are redundant.
    verdict = judge_files({"shapes.txt": shapes(2100, 1e-8)})["deja-vu"]
    assert guilty(verdict)
    assert verdict.summary == "2,099 of 2,100 shapes (100%) repeat another one"
    assert verdict.details == ["2,100 shapes like S0, S1, S10 (2.0 km)"]


def test_deja_vu_tolerates_small_detours(judge_files):
    verdict = judge_files({"shapes.txt": shapes(2100, 1e-8, bend=0.0003)})["deja-vu"]
    assert guilty(verdict)
    assert verdict.summary == "2,099 of 2,100 shapes (100%) repeat another one"


def test_deja_vu_needs_shapes_to_differ_by_less_than_100_m(judge_files):
    assert not guilty(judge_files({"shapes.txt": shapes(2100, 0.01)})["deja-vu"])


def test_deja_vu_lets_a_few_copies_off(judge_files):
    assert not guilty(judge_files({"shapes.txt": shapes(500, 1e-8)})["deja-vu"])
