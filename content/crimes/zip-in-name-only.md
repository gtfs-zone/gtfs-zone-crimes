---
title: Zip in name only
tagline: A .zip that compresses nothing.
---

A zip archive can store its files compressed or "stored": copied in as they
are. CSV compresses brilliantly, often to a fifth of its size or less. A zip
that stores everything is a tarball with extra steps, and every consumer pays
for the bytes.

## The law

Every file in the zip is stored without compression, and together they are
over 1 MB.

## How to get pardoned

Use deflate, which is the default in every zip tool. In Python that is
`zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED)`.
