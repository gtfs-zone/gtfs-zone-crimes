---
title: Data ONLY
tagline: Megabytes of timetable, and not a word about who sent it.
---

feed_info.txt is a handful of lines: who publishes the feed, its language,
which version it is, the dates it is good for, and where to write when it is
wrong. Without it, a consumer holding a feed cannot tell whether it has the
latest one, how long it is valid, or whom to call. A tiny feed can get away
with that. A big one, carried by apps and trip planners across a region,
cannot.

## The law

The zip has no feed_info.txt (or an empty one), and its files add up to more
than 10 MB uncompressed.

## How to get pardoned

Add feed_info.txt with at least `feed_publisher_name`, `feed_publisher_url`,
`feed_lang`, `feed_version` and `feed_contact_email`. `feed_start_date` and
`feed_end_date` are a kindness too.
