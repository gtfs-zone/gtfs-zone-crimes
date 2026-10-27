/** Feeds ranked by how many crimes they stand convicted of. */
import { CONFIG } from '../config';
import type { CrimesDoc } from '../data/crimes';
import { byFeed } from '../data/crimes';
import { t } from '../i18n/messages';
import { crimeBadge, feedCell, pageHeader } from './render';

export function renderMostWanted(doc: CrimesDoc): string {
  const order = new Map(doc.crimes.map((c, i) => [c.slug, i] as const));
  const ranked = [...byFeed(doc).entries()]
    .sort(
      ([a, x], [b, y]) =>
        y.length - x.length ||
        (doc.feeds[a]?.name ?? a).localeCompare(doc.feeds[b]?.name ?? b)
    )
    .slice(0, CONFIG.MOST_WANTED);
  const rows = ranked
    .map(
      ([feedId, convictions], index) => `<tr>
        <td class="text-right font-mono opacity-60">${index + 1}</td>
        <td>${feedCell(doc, feedId)}</td>
        <td class="text-center font-bold">${convictions.length}</td>
        <td><div class="flex flex-wrap gap-1">${convictions
          .map((c) => c.crime)
          .sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0))
          .map(crimeBadge)
          .join('')}</div></td>
      </tr>`
    )
    .join('');
  return `
    ${pageHeader(t('wanted.title'), t('wanted.lede'))}
    <div class="overflow-x-auto mt-6"><table class="table table-sm">
      <thead><tr><th></th><th>${t('table.feed')}</th><th>#</th><th>${t('table.crimes')}</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}
