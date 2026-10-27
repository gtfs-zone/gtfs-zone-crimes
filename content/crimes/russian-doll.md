---
title: Russian doll
tagline: Open the zip, find a folder. Open the folder, find a zip.
---

The spec says the files go at the top level of the zip. Some feeds put them in
a folder. Some put a zip in the zip. Some carry the producer's `__MACOSX`
metadata, a `.DS_Store`, an XML schema, or the PDF timetable for good measure.

Every one of these breaks somebody's loader.

## The law

Any of: a zip inside the zip, the GTFS files inside a folder, operating system
junk (`__MACOSX/`, `.DS_Store`, `Thumbs.db`), or files that are not `.txt` or
`.geojson`. Extra `.txt` tables are fine: extensions are part of GTFS life.

## How to get pardoned

Zip the files, not the folder. `cd feed && zip ../feed.zip *.txt` does it.
