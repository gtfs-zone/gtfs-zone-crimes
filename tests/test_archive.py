import zipfile

from tests.conftest import fixture_files, make_zip


def test_russian_doll_folder(judge_files):
    files = {f"gtfs/{name}": body for name, body in fixture_files().items()}
    verdicts = judge_files(files, base=None)
    assert verdicts["russian-doll"].guilty
    assert verdicts["russian-doll"].summary == "GTFS files inside the folder gtfs/"
    # Content is still judged from the folder.
    assert verdicts["supersonic"] is not None


def test_russian_doll_nested_zip(judge_files):
    inner = make_zip(fixture_files())
    verdicts = judge_files({"feed.zip": inner}, base=None)
    assert verdicts["russian-doll"].summary == "1 zip(s) inside the zip"
    assert "supersonic" not in verdicts


def test_russian_doll_litter(judge_files):
    verdict = judge_files({"__MACOSX/._stops.txt": "x", "timetable.pdf": "x"})[
        "russian-doll"
    ]
    assert verdict.summary == "1 OS junk file(s); 1 non-GTFS file(s)"


def test_extra_txt_tables_are_fine(judge_files):
    assert not judge_files({"route_directions.txt": "x"})["russian-doll"].guilty


def test_zip_in_name_only(judge_files):
    big = {"notes.txt": "x" * 1_200_000}
    assert judge_files(big, method=zipfile.ZIP_STORED)["zip-in-name-only"].guilty
    assert not judge_files(big)["zip-in-name-only"].guilty


def test_small_stored_zip_is_let_off(judge_files):
    assert not judge_files(method=zipfile.ZIP_STORED)["zip-in-name-only"].guilty


def test_bad_zip(tmp_path):
    from gtfs_zone_crimes.judge import judge_zip

    path = tmp_path / "feed.zip"
    path.write_bytes(b"<html>not a zip</html>")
    assert judge_zip(path, tmp_path / "work")["error"].startswith("bad_zip")


def test_data_only(judge_files):
    big = {"notes.txt": "x" * 10_500_000}
    verdict = judge_files(big)["data-only"]
    assert verdict.guilty
    assert verdict.summary == "No feed_info.txt in 11 MB of data"
    feed_info = "feed_publisher_name,feed_publisher_url,feed_lang\nA,https://a.org,en"
    assert not judge_files({**big, "feed_info.txt": feed_info})["data-only"].guilty


def test_small_feed_needs_no_feed_info(judge_files):
    assert not judge_files()["data-only"].guilty
