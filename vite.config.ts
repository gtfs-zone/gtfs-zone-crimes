import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import { readdirSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { execSync } from 'child_process';
import type { WriteUp } from './web/src/data/write-up-parse';
import { parseWriteUp } from './web/src/data/write-up-parse';
import { en } from './web/src/i18n/catalog.en';
import type { PageMeta } from './web/src/seo';
import { SITE, documentTitle, pageMeta } from './web/src/seo';

let version: string;
try {
  // Exactly on a tag: use the clean tag name (e.g. "0.3.1").
  version = execSync('git describe --tags --exact-match')
    .toString()
    .trim()
    .replace(/^v/, '');
} catch {
  try {
    // Between tags: tag + commit count + hash (e.g. "0.3.1-2-gabc1234").
    version = execSync('git describe --tags --long --always')
      .toString()
      .trim()
      .replace(/^v/, '');
  } catch {
    version = '0.0.0-development';
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function readWriteUps(): Map<string, WriteUp> {
  const dir = resolve(__dirname, 'content/crimes');
  return new Map(
    readdirSync(dir)
      .filter((name) => name.endsWith('.md'))
      .sort()
      .map((name) => {
        const slug = name.replace(/\.md$/, '');
        return [
          slug,
          parseWriteUp(slug, readFileSync(resolve(dir, name), 'utf-8')),
        ];
      })
  );
}

/** Replaces one attribute value in the tag matched by `tag`, or throws. */
function setAttr(html: string, tag: RegExp, value: string): string {
  if (!tag.test(html)) {
    throw new Error(`prerender: no ${tag} in index.html`);
  }
  return html.replace(tag, (_, start: string, end: string) => {
    return `${start}${escapeHtml(value)}${end}`;
  });
}

/** index.html with a page's head and a crawlable body in place of the spinner. */
function renderPage(template: string, meta: PageMeta, body: string): string {
  const title = documentTitle(meta.title);
  let html = template;
  html = setAttr(html, /(<title>)[^<]*(<\/title>)/, title);
  html = setAttr(
    html,
    /(<meta\s+name="description"\s+content=")[^"]*(")/,
    meta.description
  );
  html = setAttr(
    html,
    /(<meta\s+property="og:description"\s+content=")[^"]*(")/,
    meta.description
  );
  html = setAttr(
    html,
    /(<meta\s+property="og:title"\s+content=")[^"]*(")/,
    title
  );
  html = setAttr(
    html,
    /(<link\s+rel="canonical"\s+href=")[^"]*(")/,
    meta.canonical!
  );
  html = setAttr(
    html,
    /(<meta\s+property="og:url"\s+content=")[^"]*(")/,
    meta.canonical!
  );
  const spinner = '<span class="loading loading-dots"></span>';
  if (!html.includes(spinner)) {
    throw new Error('prerender: no spinner in index.html');
  }
  return html.replace(spinner, body);
}

function header(title: string, lede: string): string {
  return `<h1 class="text-3xl font-bold wrap-break-word">${escapeHtml(title)}</h1>
      <p class="mt-2 opacity-80 max-w-3xl">${escapeHtml(lede)}</p>`;
}

function sitemap(paths: string[]): string {
  const urls = paths
    .map((path) => `  <url>\n    <loc>${SITE}${path}</loc>\n  </url>`)
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

/**
 * Writes each crime page, Most Wanted and Pardoned as its own index.html, with
 * that page's head and a static body crawlers can read before the app renders,
 * and a sitemap.xml listing them.
 */
function prerender(): Plugin {
  return {
    name: 'prerender',
    apply: 'build',
    enforce: 'post',
    generateBundle(_, bundle) {
      const index = bundle['index.html'];
      if (index?.type !== 'asset' || typeof index.source !== 'string') {
        throw new Error('prerender: index.html is not in the bundle');
      }
      const template = index.source;
      const writeUps = readWriteUps();
      const crimeLinks = [...writeUps.values()]
        .map(
          (w) =>
            `<li><a href="/crime/${w.slug}" class="link">${escapeHtml(w.title)}</a>: ${escapeHtml(w.tagline)}</li>`
        )
        .join('\n        ');
      const pages: [string, string][] = [
        [
          '/',
          `${header(en['home.title'], en['home.lede'])}
      <ul class="list-disc ml-6 mt-6">
        ${crimeLinks}
      </ul>`,
        ],
        ['/most-wanted', header(en['wanted.title'], en['wanted.lede'])],
        ['/pardoned', header(en['pardoned.title'], en['pardoned.lede'])],
        ...[...writeUps.values()].map((w): [string, string] => [
          `/crime/${w.slug}`,
          `${header(w.title, w.tagline)}
      <article class="write-up max-w-3xl my-6">${w.html}</article>`,
        ]),
      ];
      for (const [path, body] of pages) {
        const meta = pageMeta(path, writeUps);
        if (!meta.canonical) {
          throw new Error(`prerender: ${path} has no canonical URL`);
        }
        const html = renderPage(template, meta, body);
        if (path === '/') {
          index.source = html;
        } else {
          this.emitFile({
            type: 'asset',
            fileName: `${path.slice(1)}/index.html`,
            source: html,
          });
        }
      }
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: sitemap(pages.map(([path]) => path)),
      });
    },
  };
}

export default defineConfig({
  plugins: [prerender()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  root: 'web',
  publicDir: 'public',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    port: 8081,
    host: true,
    // The write-ups live outside the Vite root, in content/crimes.
    fs: { allow: ['.'] },
  },
  css: {
    postcss: './postcss.config.js',
  },
  resolve: {
    alias: {
      'gtfs-zone-web-common': resolve(
        __dirname,
        'node_modules/gtfs-zone-web-common/src'
      ),
    },
  },
  optimizeDeps: {
    // gtfs-zone-web-common ships raw .ts; let vite transform it as source
    exclude: ['gtfs-zone-web-common'],
  },
});
