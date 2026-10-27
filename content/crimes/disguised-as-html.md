---
title: Disguised as HTML
tagline: 200 OK, here is a web page.
---

A GTFS URL should answer with a zip. Some answer with a cookie banner, a login
form, a "this page has moved" notice or a JSON error, all with a cheerful
`200 OK`, so every client thinks the download worked until it tries to unzip
it.

## The law

The feed's URL answers 200 with a body that is HTML, JSON or XML instead of a
zip.

## How to get pardoned

Serve the zip. If the feed has moved, redirect the old URL to the new one; if
it is gone, answer 404 or 410.
