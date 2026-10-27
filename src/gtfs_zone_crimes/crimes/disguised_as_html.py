"""Disguised as HTML: the GTFS URL answers 200 OK with a web page (or JSON, or
XML) instead of a zip."""

from gtfs_zone_crimes.crime import ACQUITTED, CatalogCase, Crime, Scope, Verdict

DISGUISES = {"html": "an HTML page", "json": "JSON", "xml": "XML"}


def judge(case: CatalogCase) -> Verdict | None:
    record = case.record
    if record is None or record.kind is None:
        return None
    if record.kind not in DISGUISES:
        return ACQUITTED
    return Verdict(guilty=True, summary=f"200 OK, then {DISGUISES[record.kind]}")


CRIME = Crime(slug="disguised-as-html", scope=Scope.CATALOG, judge=judge)
