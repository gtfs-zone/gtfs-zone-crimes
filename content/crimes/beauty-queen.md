---
title: Beauty queen
tagline: shapes.txt traced to the millimetre.
---

shapes.txt exists so a map can draw where the bus goes. A line on a phone
screen does not need a point every few centimetres, but some feeds export
straight from survey-grade GIS and ship every vertex anyway. The result is a
shapes.txt bigger than the rest of the feed combined, downloaded by every
consumer, every day, to draw the same line.

## The law

The median distance between consecutive points of a shape is under 2 m, **and**
shapes.txt is the largest file in the zip.

## How to get pardoned

Simplify the shapes before you publish them. Douglas-Peucker with a tolerance of
a few metres keeps every curve a map can show and removes the rest.
