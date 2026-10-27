/** Crimes feeds have stopped committing, most recent first. */
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import type { CrimesDoc } from '../data/crimes';
import { t } from '../i18n/messages';
import { crimeBadge, day, daysBetween, feedCell, pageHeader } from './render';

export function renderPardoned(doc: CrimesDoc): string {
  if (!doc.pardons.length) {
    return `${pageHeader(t('pardoned.title'), t('pardoned.lede'))}<p class="mt-6 opacity-60">${t('pardoned.none')}</p>`;
  }
  const rows = doc.pardons
    .map(
      (p) => `<tr>
        <td class="whitespace-nowrap text-sm">${day(p.pardoned)}</td>
        <td>${feedCell(doc, p.feedId)}</td>
        <td>${crimeBadge(p.crime)}<div class="text-sm opacity-70 mt-1">${escapeHtml(p.summary)}</div></td>
        <td class="text-sm opacity-70 whitespace-nowrap">${t('pardoned.after', { days: daysBetween(p.since, p.pardoned) })}</td>
      </tr>`
    )
    .join('');
  return `
    ${pageHeader(t('pardoned.title'), t('pardoned.lede'))}
    <div class="overflow-x-auto mt-6"><table class="table table-sm">
      <thead><tr><th>${t('table.pardoned')}</th><th>${t('table.feed')}</th><th>${t('table.crime')}</th><th></th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}
