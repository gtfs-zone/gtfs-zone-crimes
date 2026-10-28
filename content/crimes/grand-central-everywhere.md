---
title: Grand Central Everywhere
tagline: Every pole in the ground is a station.
---

In GTFS a station (`location_type=1`) is a place with platforms inside it: a
rail terminal, a bus depot, somewhere you walk around in. A pole on a street
corner is a stop.

Some feeds wrap every roadside bus stop in its own station with one platform
inside it. Every consumer now has to unwrap thousands of stations that are not
stations, pathways tools see a network of empty buildings, and trip planners
announce "Main St & 5th Ave Station".

## The law

At least 20 stations, each with three platforms or fewer, served only by local
buses, and those platforms are more than a quarter of the feed's bus stops.

Coaches are left out. A route counts as a local bus only when its median gap
between stops is under 3 km and no trip runs further than 100 km, because
intercity coach stations are usually real stations. Only trips whose service
still runs are judged.

## How to get pardoned

Drop the parent stations from roadside stops. Keep `location_type=1` for places
with more than one platform and somewhere to stand between them.
