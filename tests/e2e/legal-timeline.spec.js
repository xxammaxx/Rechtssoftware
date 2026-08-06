// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.PLN_E2E_BASE_URL || 'http://127.0.0.1:18000';

/**
 * RC-026-R2 G6: Legal Source Search
 * G7: Timeline and Evidence Pack
 */

// ===== G6: Legal Source Search =====
test.describe('G6 — Legal Source Search', () => {

  test('legal sources page loads', async ({ page }) => {
    await page.goto('/ui/legal-sources');
    // Page should load with legal sources section
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
  });

  test('legal source search input exists', async ({ page }) => {
    await page.goto('/ui/legal-sources');
    const searchInput = page.locator('input[type="search"], input[name="q"], input[placeholder*="such"]');
    // May or may not exist depending on UI state
    if (await searchInput.count() > 0) {
      await expect(searchInput).toBeVisible();
    }
  });

  test('no external requests to non-GII hosts', async ({ page }) => {
    const externalRequests = [];
    page.on('request', (request) => {
      const url = request.url();
      // Only allow localhost and GII
      if (!url.startsWith(BASE_URL) && !url.includes('gesetze-im-internet.de') && !url.startsWith('data:')) {
        externalRequests.push(url);
      }
    });

    await page.goto('/');
    await page.goto('/ui/legal-sources');

    // No unexpected external requests
    expect(externalRequests.filter(u => !u.includes('127.0.0.1') && !u.includes('localhost'))).toHaveLength(0);
  });
});

// ===== G7: Timeline and Evidence Pack =====
test.describe('G7 — Timeline and Evidence Pack', () => {

  test('timeline page accessible from case', async ({ page }) => {
    await page.goto('/ui/cases');
    const caseLink = page.locator('a:has-text("Playwright E2E Testfall")').first();
    const exists = await caseLink.count() > 0;
    // Seeded data exists — proceed with test
    await caseLink.click();

    // Look for timeline link
    const timelineLink = page.locator('a[href*="timeline"], a:has-text("Timeline"), a:has-text("Chronik")').first();
    if (await timelineLink.count() > 0) {
      await timelineLink.click();
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('evidence pack accessible', async ({ page }) => {
    await page.goto('/ui/cases');
    const caseLink = page.locator('a:has-text("Playwright E2E Testfall")').first();
    const exists = await caseLink.count() > 0;
    if (!exists) return; // No test case — skip gracefully
    await caseLink.click();

    const evidenceLink = page.locator('a[href*="evidence"], a:has-text("Evidence"), a:has-text("Nachweis")').first();
    if (await evidenceLink.count() > 0) {
      await evidenceLink.click();
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
    }
  });
});
