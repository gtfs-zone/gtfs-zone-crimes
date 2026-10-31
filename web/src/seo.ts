/**
 * Each path's title, description and canonical URL. Shared by the app, which
 * updates the head on navigation, and the build, which prerenders the pages.
 * Imports nothing that needs a browser or gtfs-zone-web-common.
 */
import { en } from './i18n/catalog.en';

export const SITE = 'https://crimes.gtfs.zone';
export const SITE_NAME = 'crimes.gtfs.zone';

const DESCRIPTION_MAX = 160;

interface WriteUpMeta {
  title: string;
  tagline: string;
  summary: string;
}

export interface PageMeta {
  /** The heading; the document title is `${title} - crimes.gtfs.zone`. */
  title: string;
  description: string;
  /** Absolute canonical URL, or null for a page kept out of the index. */
  canonical: string | null;
}

/** Cuts text to DESCRIPTION_MAX characters at a word boundary. */
function clip(text: string): string {
  if (text.length <= DESCRIPTION_MAX) {
    return text;
  }
  const cut = text.slice(0, DESCRIPTION_MAX - 3);
  return `${cut.slice(0, cut.lastIndexOf(' ')).replace(/[\s,.;:]+$/, '')}...`;
}

export function crimeDescription(writeUp: WriteUpMeta): string {
  return clip(`${writeUp.tagline} ${writeUp.summary}`.trim());
}

export function documentTitle(title: string): string {
  return title === en['home.title']
    ? `${SITE_NAME} - ${title}`
    : `${title} - ${SITE_NAME}`;
}

export function pageMeta(
  path: string,
  writeUps: Map<string, WriteUpMeta>
): PageMeta {
  const [, section = '', id, extra, ...rest] = path.split('/');
  const home: PageMeta = {
    title: en['home.title'],
    description: en['home.description'],
    canonical: `${SITE}/`,
  };
  if (section === '' && id === undefined) {
    return home;
  }
  const writeUp = id ? writeUps.get(id) : undefined;
  if (
    section === 'crime' &&
    writeUp &&
    (extra === undefined || extra === '' || extra === 'all') &&
    !rest.some(Boolean)
  ) {
    return {
      title: writeUp.title,
      description: crimeDescription(writeUp),
      canonical: `${SITE}/crime/${id}`,
    };
  }
  if (!id && !extra) {
    if (section === 'most-wanted') {
      return {
        title: en['wanted.title'],
        description: en['wanted.lede'],
        canonical: `${SITE}/most-wanted`,
      };
    }
    if (section === 'pardoned') {
      return {
        title: en['pardoned.title'],
        description: en['pardoned.lede'],
        canonical: `${SITE}/pardoned`,
      };
    }
  }
  // Rap sheets and unknown paths: reachable, not indexed.
  return { ...home, canonical: null };
}
