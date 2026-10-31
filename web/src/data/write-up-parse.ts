/**
 * Parses a crime write-up: a frontmatter block (title, tagline, featured feed
 * id) and a markdown body. Shared by the app and the build's prerender.
 */
import { marked } from 'marked';

export interface WriteUp {
  slug: string;
  title: string;
  tagline: string;
  /** A feed whose conviction the crime page shows first. */
  featured?: string;
  /** The body's first paragraph as plain text. */
  summary: string;
  html: string;
}

/** Strips links, emphasis and code marks from one markdown paragraph. */
function plain(markdown: string): string {
  return markdown
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*`]/g, '')
    .replace(/(^|\s)_([^_]+)_(?=[\s.,;:!?]|$)/g, '$1$2')
    .replace(/\s+/g, ' ')
    .trim();
}

export function parseWriteUp(slug: string, text: string): WriteUp {
  const match = /^---\n([\s\S]*?)\n---\n/.exec(text);
  const meta: Record<string, string> = {};
  for (const line of (match?.[1] ?? '').split('\n')) {
    const at = line.indexOf(':');
    if (at > 0) {
      meta[line.slice(0, at).trim()] = line.slice(at + 1).trim();
    }
  }
  const body = match ? text.slice(match[0].length) : text;
  const first = body
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .find((block) => block && !/^[#>|`-]/.test(block));
  return {
    slug,
    title: meta.title ?? slug,
    tagline: meta.tagline ?? '',
    featured: meta.featured,
    summary: plain(first ?? ''),
    html: marked.parse(body, { async: false }),
  };
}
