import polars as pl
from gtfs_zone_vocab.route_types import ROUTE_TYPE_FAMILIES

from gtfs_zone_crimes.modes import (
    LIMIT_BY_FAMILY,
    LOCAL_BUS,
    SUPERSONIC_KMH,
    limit_expr,
    mode_name,
)

LIMITS = {
    # Base types: the limits from before the vocab.
    0: 200.0,
    1: 200.0,
    2: 450.0,
    3: 250.0,
    4: 150.0,
    5: 100.0,
    6: 100.0,
    7: 100.0,
    11: 250.0,
    12: 200.0,
    # Extended and unknown codes.
    109: 450.0,
    715: 250.0,
    1100: SUPERSONIC_KMH,
    1200: 150.0,
    1501: 250.0,
    1700: SUPERSONIC_KMH,
    99: SUPERSONIC_KMH,
    None: SUPERSONIC_KMH,
}


def test_families_are_vocab_families():
    assert set(LIMIT_BY_FAMILY) <= {f.slug for f in ROUTE_TYPE_FAMILIES}


def test_limits():
    frame = pl.DataFrame({"route_type": list(LIMITS)}, schema={"route_type": pl.Int16})
    assert frame.select(limit_expr()).to_series().to_list() == list(LIMITS.values())


def test_mode_name():
    assert mode_name(109) == "rail"
    assert mode_name(11) == "trolleybus"
    assert mode_name(99) == "unknown mode"
    assert mode_name(None) == "unknown mode"


def test_local_bus():
    assert {3, 11, 700, 800} <= LOCAL_BUS
    assert not LOCAL_BUS & {200, 1500}
