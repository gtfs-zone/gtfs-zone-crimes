/** crimes.gtfs.zone's UI strings, in English. The keys are the catalog's shape. */
export const en = {
  'nav.gallery': 'Crimes',
  'nav.mostWanted': 'Most Wanted',
  'nav.pardoned': 'Pardoned',
  'nav.theme': 'Toggle theme',

  'home.title': 'Crimes against GTFS',
  'home.lede':
    'Things GTFS feeds do that are allowed, or nearly, and make everyone downstream suffer. Every feed in the public catalogs is put on trial daily; a feed that cleans up its act is pardoned automatically.',
  'home.onTrial': 'feeds on trial',
  'home.convictions': 'convictions',
  'home.convicted': 'feeds convicted',
  'home.pardons': 'pardons, last 90 days',
  'home.lastTrial': 'Last trial {date}',

  'crime.convicted_one': '{count} convicted',
  'crime.convicted_other': '{count} convicted',
  'crime.judged': 'of {count} judged',
  'crime.worst': 'Worst offender',
  'crime.none': 'Nobody, yet.',
  'crime.featured': 'Exhibit A',
  'crime.convictedList': 'Convicted',
  'crime.showAll': 'Show all {count}',
  'crime.since': 'since {date}',

  'table.feed': 'Feed',
  'table.evidence': 'Evidence',
  'table.since': 'Convicted',
  'table.crimes': 'Crimes',
  'table.pardoned': 'Pardoned',
  'table.crime': 'Crime',

  'wanted.title': 'Most Wanted',
  'wanted.lede': 'The feeds with the most active convictions.',

  'pardoned.title': 'Recently pardoned',
  'pardoned.lede': 'Feeds that stopped committing a crime in the last 90 days.',
  'pardoned.none': 'No pardons yet. Fix your feeds.',
  'pardoned.after': 'after {days} days',

  'feed.title': 'Rap sheet',
  'feed.list': 'View on list.gtfs.zone',
  'feed.edit': 'Open in the editor',
  'feed.viz': 'Watch it live',
  'feed.listShort': 'list.gtfs.zone',
  'feed.clean': 'No active convictions.',
  'feed.pardons': 'Pardons',
  'feed.unknown': 'This feed has no record.',

  'footer.data':
    'Feeds from the {catalogs}. Each feed belongs to its publisher. Crimes are opinions.',
  'footer.source': 'Source',
  'error.load': 'Could not load the case files: {error}',
} as const;
