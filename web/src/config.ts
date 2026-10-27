/**
 * Application-wide configuration constants.
 * All magic numbers and URLs live here; import CONFIG rather than inlining literals.
 */
export const CONFIG = Object.freeze({
  // Where crimes.json is served. In the cluster the site's nginx proxies
  // /data/ to the crimes bucket. In dev, `crimes judge` writes web/dev-data,
  // which Vite serves from the root but never copies into a build.
  DATA_BASE:
    import.meta.env.VITE_DATA_BASE ??
    (import.meta.env.DEV ? '/dev-data' : '/data'),

  // Convictions listed on a crime page before "Show all".
  LIST_CAP: 100,

  // Feeds on the Most Wanted page.
  MOST_WANTED: 100,

  // Sibling apps a feed links to. Same targets as gtfs-zone-feed-list.
  LIST_FEED_BASE: 'https://list.gtfs.zone/feed/',
  EDITOR_BASE: 'https://edit.gtfs.zone',
  VIEWER_BASE: 'https://viz.rt.gtfs.zone',
  SOURCE_URL: 'https://github.com/gtfs-zone/gtfs-zone-crimes',
});
