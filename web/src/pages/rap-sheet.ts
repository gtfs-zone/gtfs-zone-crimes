/** One feed: every crime it stands convicted of, and its pardons. */
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import type { CrimesDoc } from '../data/crimes';
import { t } from '../i18n/messages';
import {
  crimeBadge,
  crimeTitle,
  day,
  evidence,
  feedLinks,
  pageHeader,
} from './render';

export function renderRapSheet(doc: CrimesDoc, feedId: string): string {
  const feed = doc.feeds[feedId];
  if (!feed) {
    return `${pageHeader(t('feed.title'))}<p class="mt-6 opacity-60">${t('feed.unknown')}</p>`;
  }
  const order = new Map(doc.crimes.map((c, i) => [c.slug, i] as const));
  const convictions = doc.convictions
    .filter((c) => c.feedId === feedId)
    .sort((a, b) => (order.get(a.crime) ?? 0) - (order.get(b.crime) ?? 0));
  const pardons = doc.pardons.filter((p) => p.feedId === feedId);
  const sub = [feed.subtitle, feed.place].filter(Boolean).join(' - ');
  const cards = convictions
    .map(
      (c) => `<div class="card bg-base-100 border border-base-300">
        <div class="card-body gap-2">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <a href="#/crime/${c.crime}" class="card-title link link-hover">${escapeHtml(crimeTitle(c.crime))}</a>
            <span class="text-xs opacity-60">${t('crime.since', { date: day(c.since) })}</span>
          </div>
          ${evidence(c, true)}
        </div>
      </div>`
    )
    .join('');
  const pardonList = pardons.length
    ? `<h2 class="text-xl font-bold mt-8 mb-3">${t('feed.pardons')}</h2>
       <ul class="space-y-2">${pardons
         .map(
           (p) =>
             `<li>${crimeBadge(p.crime)} <span class="text-sm opacity-70">${day(p.since)} to ${day(p.pardoned)}</span></li>`
         )
         .join('')}</ul>`
    : '';
  return `
    <div class="text-xs uppercase opacity-60">${t('feed.title')}</div>
    ${pageHeader(feed.name)}
    ${sub ? `<p class="opacity-70">${escapeHtml(sub)}</p>` : ''}
    ${feedLinks(feedId, feed)}
    <div class="grid gap-4 mt-6">${cards || `<p class="opacity-60">${t('feed.clean')}</p>`}</div>
    ${pardonList}`;
}
