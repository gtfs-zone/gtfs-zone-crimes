---
title: Deja vu
tagline: The same shape, again and again, under a new shape_id each time.
featured: f-9751d26b01
---

A trip points at a shape with `shape_id`, so one shape can serve every trip
that runs the same way. Some feeds generate a shape per trip, or per tiny
variation of a pattern, and end up shipping the same line hundreds of times
with a few centimetres of noise between the copies. Every consumer downloads
all of them, stores all of them, and draws the same line on top of itself.

## The law

At least 2,000 shapes, and at least 15% of all shapes, are copies of another
shape: they start and end within the same ~100 m, pass the same point halfway
along to within ~1 km, and run the same length to within 5%. shapes.txt is
judged on its first 128 MB and the count scaled up to the whole file.

## How to get pardoned

Merge shapes that run the same way and point every trip of the pattern at the
one that is left. If the copies differ only in where a trip starts or ends
along the route, `shape_dist_traveled` in stop_times.txt lets them share a
shape anyway.
