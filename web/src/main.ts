/**
 * Entry point: loads crimes.json once, then renders the page the path names.
 * Routes: / (gallery), /crime/<slug>[/all], /feed/<id>, /most-wanted,
 * /pardoned. Old #/ links are rewritten to their path.
 */
import {
  renderMoonIcon,
  renderSunIcon,
} from 'gtfs-zone-web-common/ui/nav-icons';
import {
  githubAction,
  renderNavbarActions,
} from 'gtfs-zone-web-common/ui/navbar-actions';
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
import { documentTitle, pageMeta } from './seo';

const page = document.getElementById('page')!;
const footer = document.getElementById('footer')!;
const nav = document.getElementById('nav-links')!;

const LINKS: [string, string][] = [
  ['/', t('nav.gallery')],
  ['/most-wanted', t('nav.mostWanted')],
  ['/pardoned', t('nav.pardoned')],
];

function renderNav(path: string): void {
  const active =
    LINKS.find(([href]) => href !== '/' && path.startsWith(href))?.[0] ?? '/';
  nav.innerHTML = LINKS.map(
    ([href, label]) =>
      `<a href="${href}" class="btn btn-ghost btn-sm px-2 sm:px-3${href === active ? ' btn-active' : ''}">${escapeHtml(label)}</a>`
  ).join('');
}

/** Points the head at the page: title, description, canonical, robots. */
function updateHead(path: string, feedName?: string): void {
  const meta = pageMeta(path, WRITE_UPS);
  document.title = documentTitle(feedName ?? meta.title);
  document
    .querySelector('meta[name="description"]')
    ?.setAttribute('content', meta.description);
  document
    .querySelector('meta[property="og:title"]')
    ?.setAttribute('content', documentTitle(meta.title));
  document
    .querySelector('meta[property="og:description"]')
    ?.setAttribute('content', meta.description);
  const canonical = document.querySelector('link[rel="canonical"]');
  const ogUrl = document.querySelector('meta[property="og:url"]');
  let robots = document.querySelector('meta[name="robots"]');
  if (meta.canonical) {
    canonical?.setAttribute('href', meta.canonical);
    ogUrl?.setAttribute('content', meta.canonical);
    robots?.remove();
  } else if (!robots) {
    robots = document.createElement('meta');
    robots.setAttribute('name', 'robots');
    robots.setAttribute('content', 'noindex');
    document.head.append(robots);
  }
}

function route(doc: CrimesDoc): void {
  const path = window.location.pathname;
  const [, section, id, extra] = path.split('/');
  let feedName: string | undefined;
  if (section === 'crime' && id) {
    page.innerHTML = renderCrime(doc, id, extra === 'all');
  } else if (section === 'feed' && id) {
    page.innerHTML = renderRapSheet(doc, id);
    feedName = doc.feeds[id]?.name ?? id;
  } else if (section === 'most-wanted') {
    page.innerHTML = renderMostWanted(doc);
  } else if (section === 'pardoned') {
    page.innerHTML = renderPardoned(doc);
  } else {
    page.innerHTML = renderGallery(doc);
  }
  updateHead(path, feedName);
  renderNav(path);
  window.scrollTo(0, 0);
}

/** Follows same-origin links with pushState instead of a page load. */
function followLinks(doc: CrimesDoc): void {
  document.addEventListener('click', (event) => {
    const link = (event.target as Element).closest('a');
    if (
      !link ||
      link.target ||
      link.origin !== window.location.origin ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    if (link.pathname !== window.location.pathname) {
      history.pushState(null, '', link.pathname);
    }
    route(doc);
  });
  window.addEventListener('popstate', () => route(doc));
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
  githubAction('gtfs-zone-crimes'),
]);
// Open the rightmost tooltip leftward so it does not overhang the viewport.
document
  .querySelector('#navbar-actions > .tooltip:last-child')
  ?.classList.replace('tooltip-bottom', 'tooltip-left');
new ThemeController().initialize();
document.getElementById('app-version')!.textContent = `v${__APP_VERSION__}`;
if (window.location.hash.startsWith('#/')) {
  history.replaceState(null, '', window.location.hash.slice(1));
}
renderNav(window.location.pathname);

loadCrimes()
  .then((doc) => {
    // Crimes added to the site before the pipeline has judged them are left out.
    doc.crimes = doc.crimes.filter((c) => WRITE_UPS.has(c.slug));
    renderFooter(doc);
    route(doc);
    followLinks(doc);
  })
  .catch((error: unknown) => {
    page.innerHTML = `<div class="alert alert-error">${escapeHtml(t('error.load', { error: String(error) }))}</div>`;
  });
