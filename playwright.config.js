// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: { timeout: 10000 },
  use: {
    baseURL: 'http://127.0.0.1:18000',
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
    ['json', { outputFile: 'evidence/playwright-report.json' }],
  ],
  // Global setup: no network requests
  globalSetup: undefined,
});
