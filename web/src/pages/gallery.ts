/** Home: the crimes as a gallery of cards, with the totals above them. */
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import type { CrimesDoc } from '../data/crimes';
import { byFeed } from '../data/crimes';
import { WRITE_UPS } from '../data/write-ups';
import { t } from '../i18n/messages';
import { count, day, pageHeader } from './render';

function stat(value: number, label: string): string {
  return `<div class="stat px-4 py-3"><div class="stat-value text-2xl">${count(value)}</div><div class="stat-desc">${escapeHtml(label)}</div></div>`;
}

export function renderGallery(doc: CrimesDoc): string {
  const worst = new Map<string, string>();
  for (const conviction of doc.convictions) {
    if (!worst.has(conviction.crime)) {
      worst.set(conviction.crime, conviction.feedId);
    }
  }
  const first = new Map(
    doc.convictions.map((c) => [`${c.crime}/${c.feedId}`, c] as const)
  );
  const cards = doc.crimes.map((crime) => {
    const writeUp = WRITE_UPS.get(crime.slug);
    const feedId = worst.get(crime.slug);
    const top = feedId ? first.get(`${crime.slug}/${feedId}`) : undefined;
    const offender = top
      ? `<div class="text-xs uppercase opacity-60">${t('crime.worst')}</div>
         <div class="font-medium">${escapeHtml(doc.feeds[top.feedId]?.name ?? top.feedId)}</div>
         <div class="text-sm opacity-80 line-clamp-2">${escapeHtml(top.summary ?? '')}</div>`
      : `<div class="text-sm opacity-60">${t('crime.none')}</div>`;
    const badge = crime.convicted ? 'badge-error' : 'badge-success';
    return `
      <a href="#/crime/${crime.slug}" class="card bg-base-100 border border-base-300 hover:border-error transition-colors">
        <div class="card-body gap-3">
          <div class="flex items-center justify-between gap-2">
            <span class="badge ${badge}">${t('crime.convicted', { count: crime.convicted })}</span>
            <span class="text-xs opacity-60">${t('crime.judged', { count: count(crime.judged) })}</span>
          </div>
          <h2 class="card-title">${escapeHtml(writeUp?.title ?? crime.slug)}</h2>
          <p class="italic opacity-80">${escapeHtml(writeUp?.tagline ?? '')}</p>
          <div class="mt-auto pt-2 border-t border-base-300">${offender}</div>
        </div>
      </a>`;
  });
  return `
    ${pageHeader(t('home.title'), t('home.lede'))}
    <p class="text-sm opacity-60 mt-1">${t('home.lastTrial', { date: day(doc.generated_at) })}</p>
    <div class="stats stats-vertical sm:stats-horizontal border border-base-300 my-6 w-full sm:w-auto">
      ${stat(doc.feedCount, t('home.onTrial'))}
      ${stat(doc.convictions.length, t('home.convictions'))}
      ${stat(byFeed(doc).size, t('home.convicted'))}
      ${stat(doc.pardons.length, t('home.pardons'))}
    </div>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">${cards.join('')}</div>`;
}
