---
title: Every day is special
tagline: No weekly calendar, just a list of every day.
---

calendar.txt says "weekdays from January to June". calendar_dates.txt says
"except Christmas". Some feeds skip calendar.txt and list every single day of
service in calendar_dates.txt instead: thousands of rows that say, at length,
"weekdays from January to June".

It is valid GTFS. It also makes the feed bigger, slower to load and impossible
to read, and it hides the service pattern from anyone looking at the data.

## The law

No calendar.txt row runs on any day of the week, and calendar_dates.txt has
more than 5,000 rows.

## How to get pardoned

Write the weekly patterns to calendar.txt and keep calendar_dates.txt for the
exceptions.
