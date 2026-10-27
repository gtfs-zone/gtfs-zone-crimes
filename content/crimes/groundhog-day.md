---
title: Groundhog Day
tagline: Same file, new date, download it again.
---

HTTP has a simple way to say "you already have this": the server sends an
`ETag` or a `Last-Modified` header, the client sends it back next time, and the
server answers `304 Not Modified` without a body.

Some servers send neither, so every client downloads the whole feed every time.
Others regenerate the zip on a schedule, so its date and ETag change every day
while its contents do not.

## The law

The URL answers with no `ETag` and no `Last-Modified`, or on 3 of the last 7
daily checks it sent new validators with byte-for-byte the same file.

## How to get pardoned

Serve the feed as a static file: every web server sets both headers by itself.
Only replace the file when its contents change.
