# AGENTS.md

`crimes.gtfs.zone`: an opinionated list of crimes against the GTFS spec and the
feeds convicted of them. Two halves in one repo: a Python package (the crimes
and a Dagster code location in gtfs-zone-feed-catalog's instance, publishing
`crimes.json` to the `crimes.gtfs.zone` bucket) and a Vite site in `web/`. A
`v*` tag builds both images and commits their digests into gtfs-zone-infra.

## Commands

Local runs, env vars and cost are in [README.md](README.md).

```bash
uv run crimes judge            # judge feeds into web/dev-data (CRIMES_FEEDS limits them)
pnpm dev                       # the site, reading web/dev-data
scripts/check.sh               # what CI and the pre-commit hook run
```

## Architecture

- **A crime is a module plus a write-up.** `crimes/<slug>.py` defines `CRIME`;
  `content/crimes/<slug>.md` is the page. `registry.py` lists them in gallery
  order and a test keeps the two sets equal. Adding one is in
  [CONTRIBUTING.md](CONTRIBUTING.md#adding-a-crime).
- **Scope decides when a crime runs.** `catalog` crimes run every day in the
  main process on the feeds.json entry, the URL record and the zip's facts;
  `archive` and `content` crimes run once per zip in a worker and are cached in
  `state/records.json` by sha256 and package version. Anything that depends on
  today's date must be catalog scope.
- **A judge returns `None` when it cannot judge.** An unjudged conviction
  stands as it was; only an acquittal pardons. Never return an acquittal for
  missing input.
- **`crimes.json` is a contract** with `web/src/data/crimes.ts`; change
  `artifacts.py` first.
- **Memory is watched, not limited.** polars reserves far more address space
  than it uses and aborts under `RLIMIT_AS`, so `pool.isolated` polls the
  worker's RSS and kills it past `CRIMES_WORKER_MEMORY`.
- **Large tables stay narrow.** `Gtfs.sequence` holds stop_times with
  categorical ids, Float32 coordinates and Int32 times; shapes.txt is judged
  on its first 128 MB in file order. Keep new content crimes on those frames.
- **Polite downloads**: conditional GETs, one request at a time per host with
  a delay, an honest User-Agent. Keep it that way.
- **Links go out, never in.** The site links to list.gtfs.zone; no other
  gtfs.zone site is changed to link here.
- **Pages are prerendered for crawlers.** The `prerender` plugin in
  `vite.config.ts` writes `crime/<slug>/index.html`, `most-wanted/` and
  `pardoned/` with their own head (from `web/src/seo.ts`) and a static body,
  plus `sitemap.xml`; the app replaces `<main>` on load. nginx 404s unknown
  paths and serves `/feed/<id>` with `X-Robots-Tag: noindex`.
- The site's nginx serves `/data/crimes.json` only, never the bucket's
  `state/` prefix.

## Conventions

- **Commits**: Conventional Commits, enforced by the `commit-msg` hook. Never add
  Co-Authored-By trailers. Setup and release are in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Logging**: module loggers are named `log`, never `logger`.
- **Copy**: no m-dashes in write-ups, comments or docs. GTFS field names stay literal.
- **Verification**: no Playwright or other browser automation. Stop at
  `pnpm check` / `pnpm build` and hand off; the user checks in the browser.
- **Cross-repo work**: sibling gtfs.zone repos live under the same parent
  directory and may be read and edited when a change spans repos.
- **Plans**: write plans to `CURRENT_PLAN.md` at the repo root as a
  checklist (`- [ ]`), ticked off as work lands. It is neither tracked nor
  gitignored: never stage or commit it.
