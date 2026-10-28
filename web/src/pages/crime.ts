/** One crime: its write-up, Exhibit A, and every feed convicted of it. */
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import { CONFIG } from '../config';
import type { CrimesDoc } from '../data/crimes';
import { WRITE_UPS } from '../data/write-ups';
import { t } from '../i18n/messages';
import { day, evidence, feedCell, pageHeader } from './render';

export function renderCrime(
  doc: CrimesDoc,
  slug: string,
  showAll: boolean
): string {
  const writeUp = WRITE_UPS.get(slug);
  const crime = doc.crimes.find((c) => c.slug === slug);
  if (!writeUp || !crime) {
    return pageHeader(slug);
  }
  const convictions = doc.convictions.filter((c) => c.crime === slug);
  const featured = convictions.find((c) => c.feedId === writeUp.featured);
  const exhibit = featured
    ? `<div class="card bg-base-100 border border-error my-6">
         <div class="card-body">
           <div class="text-xs uppercase text-error font-semibold">${t('crime.featured')}</div>
           <div>${feedCell(doc, featured.feedId)}</div>
           <div>${evidence(featured, true)}</div>
         </div>
       </div>`
    : '';
  const shown = showAll ? convictions : convictions.slice(0, CONFIG.LIST_CAP);
  const rows = shown
    .map(
      (c) => `<tr>
        <td>${feedCell(doc, c.feedId)}</td>
        <td>${evidence(c)}</td>
        <td class="whitespace-nowrap text-sm">${day(c.since)}</td>
      </tr>`
    )
    .join('');
  const more =
    shown.length < convictions.length
      ? `<a href="/crime/${slug}/all" class="btn btn-sm mt-3">${t('crime.showAll', { count: convictions.length })}</a>`
      : '';
  const table = convictions.length
    ? `<div class="overflow-x-auto"><table class="table table-sm">
         <thead><tr><th>${t('table.feed')}</th><th>${t('table.evidence')}</th><th>${t('table.since')}</th></tr></thead>
         <tbody>${rows}</tbody></table></div>${more}`
    : `<p class="opacity-60">${t('crime.none')}</p>`;
  return `
    ${pageHeader(writeUp.title)}
    <p class="italic opacity-80 mt-1">${escapeHtml(writeUp.tagline)}</p>
    ${exhibit}
    <article class="write-up max-w-3xl my-6">${writeUp.html}</article>
    <h2 class="text-xl font-bold mt-8 mb-3">${t('crime.convictedList')}
      <span class="badge badge-error align-middle ml-2">${convictions.length}</span>
    </h2>
    ${table}`;
}
