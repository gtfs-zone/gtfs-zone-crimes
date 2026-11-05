"""Speed limits per route type family (from gtfs-zone-vocab): the speed nothing
in that family reaches on a schedule."""

from __future__ import annotations

import polars as pl
from gtfs_zone_vocab.route_types import ROUTE_TYPES, route_type_family

# Speed of sound: the limit for air, misc and anything without a known family.
SUPERSONIC_KMH = 1235.0

# km/h between two stops that no scheduled vehicle of the family reaches;
# families not listed get SUPERSONIC_KMH.
LIMIT_BY_FAMILY = {
    "tram": 200.0,
    "metro": 200.0,
    "rail": 450.0,
    "coach": 250.0,
    "bus": 250.0,
    "trolleybus": 250.0,
    "taxi": 250.0,
    "ferry": 150.0,
    "cable": 100.0,
    "funicular": 100.0,
}

# Route types that serve bus stops on the street.
LOCAL_BUS = frozenset(
    rt.code for rt in ROUTE_TYPES if rt.family in ("bus", "trolleybus")
)

# Limit per known route_type code.
_LIMIT_BY_CODE = {
    rt.code: LIMIT_BY_FAMILY.get(rt.family, SUPERSONIC_KMH) for rt in ROUTE_TYPES
}


def mode_name(route_type: int | None) -> str:
    """The family slug of a route type, or "unknown mode"."""
    family = route_type_family(route_type) if route_type is not None else None
    return family or "unknown mode"


def limit_expr(column: str = "route_type") -> pl.Expr:
    """The family's speed limit for each row's route type."""
    return pl.col(column).replace_strict(
        _LIMIT_BY_CODE, default=SUPERSONIC_KMH, return_dtype=pl.Float64
    )
