/** The write-up of each crime, from content/crimes/<slug>.md. */
import type { WriteUp } from './write-up-parse';
import { parseWriteUp } from './write-up-parse';

const FILES = import.meta.glob('../../../content/crimes/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

export const WRITE_UPS: Map<string, WriteUp> = new Map(
  Object.entries(FILES).map(([path, text]) => {
    const slug = path.split('/').pop()!.replace(/\.md$/, '');
    return [slug, parseWriteUp(slug, text)];
  })
);
