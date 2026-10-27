"""Route types (the spec's and the extended Hierarchical Vehicle Types) grouped
into modes, each with the speed nothing in that mode reaches on a schedule."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class Mode:
    name: str
    # km/h between two stops that no scheduled vehicle of this mode reaches.
    limit_kmh: float
    route_types: frozenset[int]


def span(start: int, stop: int) -> set[int]:
    return set(range(start, stop + 1))


# Speed of sound: the limit for air and for anything without a known mode.
SUPERSONIC_KMH = 1235.0

MODES = [
    Mode("tram", 200.0, frozenset({0} | span(900, 999))),
    Mode("metro", 200.0, frozenset({1, 12} | span(400, 499))),
    Mode("rail", 450.0, frozenset({2} | span(100, 199) | span(300, 399))),
    Mode("bus", 250.0, frozenset({3, 11} | span(700, 899) | span(1500, 1599))),
    Mode("coach", 250.0, frozenset(span(200, 299))),
    Mode("ferry", 150.0, frozenset({4} | span(1000, 1099) | span(1200, 1299))),
    Mode("cable", 100.0, frozenset({5, 6, 7} | span(1300, 1499))),
]
UNKNOWN = Mode("unknown mode", SUPERSONIC_KMH, frozenset())

# Route types that serve bus stops on the street.
LOCAL_BUS = frozenset({3, 11} | span(700, 899))


def mode_of(route_type: int | None) -> Mode:
    for mode in MODES:
        if route_type in mode.route_types:
            return mode
    return UNKNOWN


def limit_expr(column: str = "route_type") -> pl.Expr:
    """The mode's speed limit for each row's route type."""
    expr = pl.lit(SUPERSONIC_KMH)
    for mode in reversed(MODES):
        expr = (
            pl.when(pl.col(column).is_in(list(mode.route_types)))
            .then(pl.lit(mode.limit_kmh))
            .otherwise(expr)
        )
    return expr
