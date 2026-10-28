/** Markup shared by the pages. */
import { formatDate, formatNumber } from 'gtfs-zone-web-common/i18n/fmt';
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import { CONFIG } from '../config';
import type { Conviction, CrimesDoc, FeedSummary } from '../data/crimes';
import { WRITE_UPS } from '../data/write-ups';
import { t } from '../i18n/messages';

export function crimeTitle(slug: string): string {
  return WRITE_UPS.get(slug)?.title ?? slug;
}

export function day(iso: string): string {
  return formatDate(new Date(`${iso.slice(0, 10)}T12:00:00Z`), {
    dateStyle: 'medium',
  });
}

export function count(value: number): string {
  return formatNumber(value);
}

export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(to) - Date.parse(from)) / 86_400_000);
}

/**
 * The feed's name linking to its rap sheet, a small link to list.gtfs.zone
 * beside it, and its place under it.
 */
export function feedCell(doc: CrimesDoc, feedId: string): string {
  const feed = doc.feeds[feedId];
  const name = escapeHtml(feed?.name ?? feedId);
  const sub = [feed?.subtitle, feed?.place].filter(Boolean).join(' - ');
  return (
    `<a href="#/feed/${feedId}" class="link link-hover font-medium wrap-anywhere">${name}</a>` +
    ` <a href="${listUrl(feedId)}" target="_blank" rel="noopener noreferrer" class="link link-hover text-xs opacity-60 whitespace-nowrap">${t('feed.listShort')}</a>` +
    (sub
      ? `<div class="text-xs opacity-60 wrap-anywhere">${escapeHtml(sub)}</div>`
      : '')
  );
}

export function crimeBadge(slug: string): string {
  return `<a href="#/crime/${slug}" class="badge badge-error badge-outline badge-sm whitespace-nowrap">${escapeHtml(crimeTitle(slug))}</a>`;
}

export function evidence(conviction: Conviction, open = false): string {
  const summary = escapeHtml(conviction.summary ?? '');
  const details = (conviction.details ?? []).filter(
    (line) => line !== conviction.summary
  );
  if (!details.length) {
    return `<span class="wrap-anywhere">${summary}</span>`;
  }
  return `<details${open ? ' open' : ''} class="wrap-anywhere"><summary class="cursor-pointer">${summary}</summary><ul class="list-disc list-inside text-sm opacity-80 mt-1">${details
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join('')}</ul></details>`;
}

export function listUrl(feedId: string): string {
  return `${CONFIG.LIST_FEED_BASE}${encodeURIComponent(feedId)}`;
}

/** The editor needs a schedule and nothing else. Mirrors feed-list's app-links.ts. */
export function editorUrl(feed: FeedSummary): string | null {
  return feed.url
    ? `${CONFIG.EDITOR_BASE}/#load=${encodeURIComponent(feed.url)}`
    : null;
}

/**
 * The visualizer draws realtime against a schedule, so it needs both. An
 * endpoint of undeclared type takes the first empty slot. Mirrors
 * feed-list's app-links.ts.
 */
export function viewerUrl(feed: FeedSummary): string | null {
  const realtime = feed.realtime ?? {};
  if (!feed.url || !Object.keys(realtime).length) {
    return null;
  }
  const params = new URLSearchParams({ scheduled: feed.url });
  const slots = [
    ['vehicles', 'rt_vp'],
    ['trip_updates', 'rt_tu'],
    ['alerts', 'rt_al'],
  ] as const;
  for (const [role, key] of slots) {
    const url = realtime[role];
    if (url) {
      params.set(key, url);
    }
  }
  const empty = slots.find(([, key]) => !params.has(key));
  if (realtime.realtime && empty) {
    params.set(empty[1], realtime.realtime);
  }
  return `${CONFIG.VIEWER_BASE}/#${params.toString()}`;
}

/** Buttons to the feed on list.gtfs.zone, in the editor and, with realtime, the visualizer. */
export function feedLinks(feedId: string, feed: FeedSummary): string {
  const links = [
    [listUrl(feedId), t('feed.list'), 'btn-primary'],
    [editorUrl(feed), t('feed.edit'), ''],
    [viewerUrl(feed), t('feed.viz'), ''],
  ] as const;
  return `<div class="flex flex-wrap gap-2 mt-3">${links
    .filter(([href]) => href)
    .map(
      ([href, label, style]) =>
        `<a href="${escapeHtml(href!)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm ${style}">${escapeHtml(label)}</a>`
    )
    .join('')}</div>`;
}

export function pageHeader(title: string, lede?: string): string {
  return (
    `<h1 class="text-3xl font-bold">${escapeHtml(title)}</h1>` +
    (lede ? `<p class="mt-2 opacity-80 max-w-3xl">${escapeHtml(lede)}</p>` : '')
  );
}
