---
title: Feed requires an API key
tagline: A zip file behind a login.
---

A static GTFS feed is a zip file. It changes a few times a month. Serving it to
everyone who asks is about the cheapest thing a web server can do, and every
CDN on earth will do it for free.

Putting it behind an API key means every app developer, every researcher and
every aggregator has to sign up, wait, store a secret, rotate it, and break when
it expires. All to protect a file that is meant to be public.

## The law

The feed's static schedule is only listed with an API key in the
[Mobility Database](https://mobilitydatabase.org) or the
[Transitland Atlas](https://github.com/transitland/transitland-atlas).

Realtime feeds are let off: they are generated every few seconds and can cost
real money to serve.

## How to get pardoned

Put the zip on a plain URL. If you need to know who downloads it, read your
access logs.
