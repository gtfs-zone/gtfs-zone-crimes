---
title: Ultra high speed service
tagline: The New Flyer is ready for takeoff.
featured: f-2f033a022e
---

A timetable is a promise about time and distance. Divide one by the other and
you get a speed, and some feeds promise speeds no vehicle has ever reached.

The patron saint of this crime is **Lbo**: a stop in Amtrak's feed, served by a
Thruway Connecting Service bus between Merced and Gilroy, California. Its
coordinates put it in northern Manitoba. The bus leaves Lbo and reaches Gilroy
2,479 km later, four hours on: 620 km/h, by road coach.

## The law

A hop between two consecutive timed stops of a trip is too fast when it beats
everything its mode can do:

| Mode | Limit |
|---|---|
| Bus, trolleybus, coach, taxi | 250 km/h |
| Tram, metro (monorail included) | 200 km/h |
| Rail | 450 km/h, above any scheduled high speed average |
| Ferry | 150 km/h |
| Cable transport (cable car, gondola), funicular | 100 km/h |
| Air, miscellaneous, or no known mode | 1,235 km/h, the speed of sound |

Times in GTFS are usually rounded to the minute, so every hop is given at least
a minute, and hops shorter than 2 km are never counted.

Only trips whose service still runs are judged. A hop to or from a stop at 0,0,
or with its latitude and longitude swapped, is left to Null Island.

When a trip reaches a stop at an impossible speed and leaves it at a similar
one (within a factor of two), the evidence marks that stop as likely
misplaced: the trip seems to go out to it and come straight back. It is a
guess, not a finding.

## How to get pardoned

Put the stop where the stop is. Then check that the times either side of it
are the times the vehicle actually takes.
