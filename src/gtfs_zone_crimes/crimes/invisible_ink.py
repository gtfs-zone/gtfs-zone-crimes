"""Invisible ink: route_text_color on route_color that nobody can read, often
because they are the same colour."""

import re

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import Gtfs

MIN_CONTRAST = 1.5
HEX = re.compile(r"^[0-9a-fA-F]{6}$")


def luminance(color: str) -> float:
    """WCAG relative luminance of an RRGGBB colour."""
    channels = [int(color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def judge(gtfs: Gtfs) -> Verdict | None:
    routes = gtfs.routes
    if routes is None:
        return None
    offenders: list[tuple[float, str]] = []
    for row in routes.iter_rows(named=True):
        color, text = row["route_color"], row["route_text_color"]
        if not (color and text and HEX.match(color) and HEX.match(text)):
            continue
        ratio = contrast(color, text)
        if ratio < MIN_CONTRAST:
            label = row["route_short_name"] or row["route_long_name"] or row["route_id"]
            offenders.append(
                (ratio, f"{label}: #{text.upper()} on #{color.upper()} ({ratio:.2f}:1)")
            )
    if not offenders:
        return ACQUITTED
    offenders.sort()
    return Verdict(
        guilty=True,
        summary=f"{len(offenders)} route(s) unreadable: {offenders[0][1]}",
        metric=len(offenders),
        details=[text for _, text in offenders[:10]],
    )


CRIME = Crime(slug="invisible-ink", scope=Scope.CONTENT, judge=judge)
