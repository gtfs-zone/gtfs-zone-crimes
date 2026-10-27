import type { KnipConfig } from 'knip';

const config: KnipConfig = {
  entry: ['web/index.html', 'web/src/styles/main.css'],
  project: ['web/src/**/*.{ts,css}'],
  ignoreBinaries: [
    'cz', // commitizen CLI
  ],
  ignoreExportsUsedInFile: true,
};

export default config;
