"""Russian doll: a zip that is not just GTFS files at its top level. A zip in
the zip, the files in a folder, macOS litter, or PDFs and spreadsheets along
for the ride."""

from pathlib import PurePosixPath

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.zipfacts import ZipFacts

LITTER = ("__MACOSX/", ".DS_Store", "Thumbs.db", "desktop.ini")
# Extensions a GTFS zip carries: the spec's files and producers' extra tables.
ALLOWED = {".txt", ".geojson"}


def judge(facts: ZipFacts) -> Verdict:
    counts: list[str] = []
    files = facts.files
    nested = [entry.name for entry in files if entry.name.lower().endswith(".zip")]
    if nested:
        counts.append(f"{len(nested)} zip(s) inside the zip")
    root = facts.root
    if root:
        counts.append(f"GTFS files inside the folder {root}")
    litter = [
        entry.name for entry in files if any(part in entry.name for part in LITTER)
    ]
    if litter:
        counts.append(f"{len(litter)} OS junk file(s)")
    stowaways = [
        entry.name
        for entry in files
        if entry.name not in litter
        and not entry.name.lower().endswith(".zip")
        and PurePosixPath(entry.name).suffix.lower() not in ALLOWED
    ]
    if stowaways:
        counts.append(f"{len(stowaways)} non-GTFS file(s)")
    if not counts:
        return ACQUITTED
    return Verdict(
        guilty=True,
        summary="; ".join(counts),
        metric=len(nested) * 10 + bool(root) * 5 + len(litter) + len(stowaways),
        details=(nested + litter + stowaways)[:10],
    )


CRIME = Crime(slug="russian-doll", scope=Scope.ARCHIVE, judge=judge)
