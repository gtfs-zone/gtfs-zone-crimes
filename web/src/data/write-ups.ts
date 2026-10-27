/**
 * The write-up of each crime, from content/crimes/<slug>.md: a frontmatter
 * block (title, tagline, featured feed id) and a markdown body.
 */
import { marked } from 'marked';

export interface WriteUp {
  slug: string;
  title: string;
  tagline: string;
  /** A feed whose conviction the crime page shows first. */
  featured?: string;
  html: string;
}

const FILES = import.meta.glob('../../../content/crimes/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

function parse(path: string, text: string): WriteUp {
  const slug = path.split('/').pop()!.replace(/\.md$/, '');
  const match = /^---\n([\s\S]*?)\n---\n/.exec(text);
  const meta: Record<string, string> = {};
  for (const line of (match?.[1] ?? '').split('\n')) {
    const at = line.indexOf(':');
    if (at > 0) {
      meta[line.slice(0, at).trim()] = line.slice(at + 1).trim();
    }
  }
  const body = match ? text.slice(match[0].length) : text;
  return {
    slug,
    title: meta.title ?? slug,
    tagline: meta.tagline ?? '',
    featured: meta.featured,
    html: marked.parse(body, { async: false }),
  };
}

export const WRITE_UPS: Map<string, WriteUp> = new Map(
  Object.entries(FILES).map(([path, text]) => {
    const writeUp = parse(path, text);
    return [writeUp.slug, writeUp];
  })
);
