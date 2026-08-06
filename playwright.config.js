// @ts-check
const { defineConfig } = require('@playwright/test');

const BASE_URL = process.env.PLN_E2E_BASE_URL || 'http://127.0.0.1:18000';

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  expect: { timeout: 15000 },
  use: {
    baseURL: BASE_URL,
    headless: true,
    viewport: { width: 1280, height: 720 },
    reducedMotion: 'reduce',
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        launchOptions: { args: ['--no-sandbox'] },
      },
    },
  ],
  reporter: [
    ['list'],
    ['json', { outputFile: 'evidence/rc026-r2/playwright/playwright-report.json' }],
  ],
  // No video evidence in repo — Phase I policy
});
