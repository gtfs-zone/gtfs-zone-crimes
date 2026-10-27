import { defineConfig } from 'vite';
import { resolve } from 'path';
import { execSync } from 'child_process';

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

export default defineConfig({
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
