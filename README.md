# gtfs-zone-crimes

[crimes.gtfs.zone](https://crimes.gtfs.zone): crimes against the GTFS
specification, and the public feeds convicted of them. Every feed in the
[gtfs.zone catalog](https://list.gtfs.zone) is put on trial daily; a feed that
fixes its problem is pardoned on the next run.

The crimes are opinions. Each one has a write-up in `content/crimes/` and a
check in `src/gtfs_zone_crimes/crimes/`.

## Crimes

| Crime | Judged on | Guilty when |
|---|---|---|
| Ultra high speed service | stop_times | A hop of 2 km or more faster than its mode allows (bus 250 km/h, rail 450, ferry 150, cable 100, anything 1,235); every hop gets at least a minute |
| Feed requires an API key | catalog | The static schedule is only listed behind a key |
| Beauty queen | shapes.txt | Median shape point spacing under 2 m, and shapes.txt is the largest file |
| Grand Central Everywhere | stops, stop_times | 20+ stations of at most 3 platforms served only by local buses, over a quarter of bus stops; coaches excluded |
| Russian doll | zip | Nested zip, files in a folder, OS junk, or non-GTFS files |
| Zip in name only | zip | Every entry stored uncompressed, over 1 MB |
| Groundhog Day | HTTP | No ETag or Last-Modified, or new validators on 3 of 7 runs with the same bytes |
| Every day is special | calendars | No weekly calendar and over 5,000 calendar_dates rows |
| Time travel | stop_times | A trip that arrives before it left, or leaves before it arrived |
| Invisible ink | routes | Text on route colour below 1.5:1 contrast |
| Null Island | stops | A stop at 0,0, or with latitude and longitude swapped |
| SHOUTING | stops, routes | Over half the stop or route long names in capitals |
| Eternal service | calendars | Service ends more than 5 years from today |
| Disguised as HTML | HTTP | 200 OK with HTML, JSON or XML instead of a zip |
| Expired | calendars | The last service date has passed |
| Dead link | catalog | Never answered, or down for 30 days |

## How it works

A Dagster code location in gtfs-zone-feed-catalog's instance runs daily at
14:00 UTC, after the catalog and timetable-sites runs:

1. Read `data.gtfs.zone/feeds.json` and the previous `crimes.json` and
   `state/records.json` from the crimes bucket.
2. Download every scheduled URL with a conditional GET (ETag /
   Last-Modified), hosts in parallel, one request at a time per host with a
   pause between them.
3. Judge each zip whose bytes changed (or that a new release has not judged)
   in a worker process watched for memory: the central directory for archive
   crimes, polars over the extracted tables for content crimes. Verdicts are
   cached per URL with the zip's sha256.
4. Judge the catalog crimes for every feed, carry conviction dates forward,
   turn acquittals into pardons, and publish `crimes.json`.

The site (`web/`) is a Vite app on gtfs-zone-web-common that renders
`crimes.json`, which its nginx proxies from the bucket at `/data/crimes.json`.

## Commands

```bash
uv sync --all-extras
uv run crimes judge                         # judge every feed into web/dev-data
CRIMES_FEEDS=f-2f033a022e uv run crimes judge  # only these feed ids
pnpm install && pnpm dev                    # the site on :8081, reading web/dev-data
scripts/check.sh                            # everything CI checks
```

## Environment variables

| Variable | Default | What it does |
|---|---|---|
| `CRIMES_CONCURRENCY` | 8 | Hosts downloaded from at once |
| `CRIMES_PER_HOST_DELAY_SECONDS` | 1.0 | Pause between requests to one host |
| `CRIMES_TIMEOUT_SECONDS` | 120 | Per-request timeout |
| `CRIMES_MAX_DOWNLOAD_BYTES` | 2000000000 | Downloads larger than this are abandoned |
| `CRIMES_WORKERS` | 2 | Zips judged at once, each in its own process |
| `CRIMES_WORKER_MEMORY` | 5000000000 | Resident bytes a judging process may reach before it is killed and the zip left unjudged |
| `CRIMES_WORKDIR` | `$TMPDIR` | Downloads and extracted tables |
| `CRIMES_FEEDS` | | Comma-separated feed ids to judge, for local runs |
| `CRIMES_SCHEDULE` | `0 14 * * *` | Daily schedule (UTC) |
| `POLARS_MAX_THREADS` | cores | Threads per judging process |
| `S3_ENDPOINT` `S3_BUCKET` `S3_ACCESS_KEY` `S3_SECRET_KEY` `S3_REGION` | | The crimes bucket (`crimes.gtfs.zone`) |
| `GATUS_URL` `GATUS_TOKEN` `GATUS_ENDPOINT_KEY` | | Heartbeat after a publish (`data_crimes-publish`) |

## Cost

Measured on 152 feeds (1.1 GB of zips): 33 s of judging, 6.5 min wall clock,
almost all of it polite downloading. Entur (535 MB zip, 2.4 GB of shapes)
judges in 4.4 s at a 3 GB peak. A first run over all ~4,800 reachable feeds
(about 17 GB) takes one to two hours of the shared run slot; later runs
download only what changed.

## Data

Feeds come from the Transitland Atlas (CC-BY 4.0), the Mobility Database (CC0)
and the National Transit Database (FTA), through gtfs-zone-feed-catalog; their
attribution is carried in `crimes.json`. Each feed belongs to its publisher.

## License

AGPL-3.0-or-later.
