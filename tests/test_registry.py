from pathlib import Path

from gtfs_zone_crimes.registry import CRIMES

CONTENT = Path(__file__).parent.parent / "content" / "crimes"


def test_slugs_are_unique():
    slugs = [crime.slug for crime in CRIMES]
    assert len(slugs) == len(set(slugs))


def test_every_crime_has_a_write_up():
    slugs = {crime.slug for crime in CRIMES}
    write_ups = {path.stem for path in CONTENT.glob("*.md")}
    assert slugs == write_ups
