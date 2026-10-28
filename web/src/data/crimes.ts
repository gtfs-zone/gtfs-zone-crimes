/**
 * crimes.json, published daily by the pipeline in this repo. Mirrors
 * `gtfs_zone_crimes/artifacts.py`; a field change starts there.
 */
import { CONFIG } from '../config';

export interface CrimeCount {
  slug: string;
  scope: 'catalog' | 'archive' | 'content';
  convicted: number;
  judged: number;
}

export interface Conviction {
  crime: string;
  feedId: string;
  /** ISO date of the first run that convicted it. */
  since: string;
  summary?: string;
  /** Ranks convictions of one crime; larger is worse. */
  metric?: number;
  details?: string[];
}

export interface Pardon {
  crime: string;
  feedId: string;
  since: string;
  pardoned: string;
  summary: string;
}

/** The catalog's realtime roles; `realtime` is an endpoint of undeclared type. */
export type RealtimeRole = 'vehicles' | 'trip_updates' | 'alerts' | 'realtime';

export interface FeedSummary {
  name: string;
  subtitle?: string;
  place?: string;
  /** The scheduled URL that was judged. */
  url?: string;
  /** First URL of each realtime role open without a key. */
  realtime?: Partial<Record<RealtimeRole, string>>;
  /** trips.txt rows, which rank convictions by feed size. */
  trips?: number;
}

export interface Attribution {
  catalogs: {
    name: string;
    url: string;
    license: string;
    licenseUrl: string;
  }[];
  feeds: string;
}

export interface CrimesDoc {
  generated_at: string;
  feedCount: number;
  crimes: CrimeCount[];
  convictions: Conviction[];
  pardons: Pardon[];
  feeds: Record<string, FeedSummary>;
  attribution?: Attribution;
}

export async function loadCrimes(): Promise<CrimesDoc> {
  const response = await fetch(`${CONFIG.DATA_BASE}/crimes.json`);
  if (!response.ok) {
    throw new Error(`crimes.json: HTTP ${response.status}`);
  }
  return (await response.json()) as CrimesDoc;
}

/** Convictions grouped by feed id. */
export function byFeed(doc: CrimesDoc): Map<string, Conviction[]> {
  const out = new Map<string, Conviction[]>();
  for (const conviction of doc.convictions) {
    const list = out.get(conviction.feedId) ?? [];
    list.push(conviction);
    out.set(conviction.feedId, list);
  }
  return out;
}
