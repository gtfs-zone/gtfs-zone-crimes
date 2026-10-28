/**
 * Entry point: loads crimes.json once, then renders the page the hash names.
 * Routes: #/ (gallery), #/crime/<slug>[/all], #/feed/<id>, #/most-wanted,
 * #/pardoned.
 */
import {
  renderMoonIcon,
  renderSunIcon,
} from 'gtfs-zone-web-common/ui/nav-icons';
import { renderNavbarActions } from 'gtfs-zone-web-common/ui/navbar-actions';
import { ThemeController } from 'gtfs-zone-web-common/ui/theme-controller';
import { escapeHtml } from 'gtfs-zone-web-common/util/escape-html';
import { CONFIG } from './config';
import type { CrimesDoc } from './data/crimes';
import { loadCrimes } from './data/crimes';
import { WRITE_UPS } from './data/write-ups';
import { t } from './i18n/messages';
import { renderCrime } from './pages/crime';
import { renderGallery } from './pages/gallery';
import { renderMostWanted } from './pages/most-wanted';
import { renderPardoned } from './pages/pardoned';
import { renderRapSheet } from './pages/rap-sheet';
import { crimeTitle } from './pages/render';

const page = document.getElementById('page')!;
const footer = document.getElementById('footer')!;
const nav = document.getElementById('nav-links')!;

const LINKS: [string, string][] = [
  ['#/', t('nav.gallery')],
  ['#/most-wanted', t('nav.mostWanted')],
  ['#/pardoned', t('nav.pardoned')],
];

function renderNav(hash: string): void {
  const active =
    LINKS.find(([href]) => href !== '#/' && hash.startsWith(href))?.[0] ?? '#/';
  nav.innerHTML = LINKS.map(
    ([href, label]) =>
      `<a href="${href}" class="btn btn-ghost btn-sm px-2 sm:px-3${href === active ? ' btn-active' : ''}">${escapeHtml(label)}</a>`
  ).join('');
}

function route(doc: CrimesDoc): void {
  const hash = window.location.hash || '#/';
  const [, section, id, extra] = hash.split('/');
  let title = t('home.title');
  if (section === 'crime' && id) {
    page.innerHTML = renderCrime(doc, id, extra === 'all');
    title = crimeTitle(id);
  } else if (section === 'feed' && id) {
    page.innerHTML = renderRapSheet(doc, id);
    title = doc.feeds[id]?.name ?? id;
  } else if (section === 'most-wanted') {
    page.innerHTML = renderMostWanted(doc);
    title = t('wanted.title');
  } else if (section === 'pardoned') {
    page.innerHTML = renderPardoned(doc);
    title = t('pardoned.title');
  } else {
    page.innerHTML = renderGallery(doc);
  }
  document.title = `${title} - crimes.gtfs.zone`;
  renderNav(hash);
  window.scrollTo(0, 0);
}

function renderFooter(doc: CrimesDoc): void {
  const catalogs = (doc.attribution?.catalogs ?? [])
    .map(
      (c) =>
        `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer" class="link">${escapeHtml(c.name)}</a> (<a href="${escapeHtml(c.licenseUrl)}" target="_blank" rel="noopener noreferrer" class="link">${escapeHtml(c.license)}</a>)`
    )
    .join(', ');
  footer.innerHTML = `<p>${t('footer.data', { catalogs })}</p>
    <p class="mt-1"><a href="${CONFIG.SOURCE_URL}" target="_blank" rel="noopener noreferrer" class="link">${t('footer.source')}</a></p>`;
}

renderNavbarActions(document.getElementById('navbar-actions')!, [
  {
    kind: 'toggle',
    id: 'theme-toggle',
    label: t('nav.theme'),
    iconOn: renderSunIcon('swap-on h-5 w-5'),
    iconOff: renderMoonIcon('swap-off h-5 w-5'),
    inputClass: 'theme-controller',
    value: 'light',
  },
]);
new ThemeController().initialize();
document.getElementById('app-version')!.textContent = `v${__APP_VERSION__}`;
renderNav(window.location.hash);

loadCrimes()
  .then((doc) => {
    // Crimes added to the site before the pipeline has judged them are left out.
    doc.crimes = doc.crimes.filter((c) => WRITE_UPS.has(c.slug));
    renderFooter(doc);
    route(doc);
    window.addEventListener('hashchange', () => route(doc));
  })
  .catch((error: unknown) => {
    page.innerHTML = `<div class="alert alert-error">${escapeHtml(t('error.load', { error: String(error) }))}</div>`;
  });
