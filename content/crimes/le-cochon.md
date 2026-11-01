---
title: Le Cochon
tagline: What Alstom and Bombardier called the og Acela and what I call your feed
featured: f-e8b702f5e5
---

Alstom and Bombardier called the first Acela "le cochon", the pig: a train
built so heavy it could never run as fast as it was meant to. Some feeds have
the same build. Next to the data that runs sit shapes no trip follows, stops
no trip serves, and trips with no stop times, and every consumer downloads
all of it every day just to throw it away.

## The law

At least 10% of the feed, by file size, is rows nothing in the feed
references:

- trips with no stop_times
- shapes no remaining trip follows
- stops no trip serves, unless they are the station, entrance or boarding area
  of one that is served
- routes, services and agencies no remaining trip uses

Rows count by their share of their file. Expired service does not count:
yesterday's trips are still referenced, just not running.

## How to get pardoned

Drop what nothing references before you publish. Most exports have a cleanup
step for unused shapes and stops; turn it on.
