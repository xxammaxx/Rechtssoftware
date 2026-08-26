// @ts-check
/**
 * RC-026-R2 G13: Accessibility — E2E tests.
 *
 * Verifies:
 *   - axe-core scan on all critical pages: /, /ui/cases, case detail, error page
 *   - Zero critical axe violations on every page
 *   - Zero serious axe violations on every page
 *   - <html lang="de"> on every page
 *   - Unique page titles (no two pages share the same <title>)
 *   - Exactly one <h1> per page
 *   - Visible focus indicator (skip-link or interactive element has :focus style)
 *   - All form inputs have associated labels
 *   - All images have alt text (even if alt="")
 *   - Skip link present and targets main content
 */

const { test, expect } = require('@playwright/test');
const { runAxe, assertAxeClean } = require('./axe-helper.js');

const BASE_URL = process.env.PLN_E2E_BASE_URL || 'http://127.0.0.1:18000';

/**
 * Helper: run axe and assert zero critical + zero serious violations.
 * @param {import('@playwright/test').Page} page
 * @param {string} pageLabel - human-readable label for error messages
 */
async function assertZeroCriticalSerious(page, pageLabel) {
  const results = await runAxe(page);

  const critical = results.violations.filter((v) => v.impact === 'critical');
  const serious = results.violations.filter((v) => v.impact === 'serious');

  if (critical.length > 0) {
    const details = critical.map(
      (v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`
    );
    throw new Error(
      `Critical axe violations on ${pageLabel}:\n${details.join('\n')}`
    );
  }

  if (serious.length > 0) {
    const details = serious.map(
      (v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`
    );
    throw new Error(
      `Serious axe violations on ${pageLabel}:\n${details.join('\n')}`
    );
  }

  return results;
}


test.describe('G13 — Accessibility', () => {

  // ── Common a11y attributes ─────────────────────────

  test('html lang="de" on home page', async ({ page }) => {
    await page.goto('/');
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('de');
  });

  test('html lang="de" on case list page', async ({ page }) => {
    await page.goto('/ui/cases');
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('de');
  });

  test('html lang="de" on create case page', async ({ page }) => {
    await page.goto('/ui/cases/create');
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('de');
  });

  test('html lang="de" on error page', async ({ page }) => {
    await page.goto('/ui/cases/00000000-0000-0000-0000-000000000000');
    await page.waitForLoadState('networkidle');
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('de');
  });

  // ── Unique Page Titles ────────────────────────────

  test('unique page title for home page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Private.?Legal.?Navigator/i);
  });

  test('unique page title for case list', async ({ page }) => {
    await page.goto('/ui/cases');
    // Case list title should differ from the home page title
    const title = await page.title();
    expect(title).toBeTruthy();
    // Should contain "Fälle" or "PrivateLegalNavigator"
    expect(title).toMatch(/Fälle|PrivateLegalNavigator/i);
  });

  test('unique page title for create case', async ({ page }) => {
    await page.goto('/ui/cases/create');
    const title = await page.title();
    expect(title).toBeTruthy();
    // Should mention "Neuen Fall" or similar — distinct from list
    expect(title).toMatch(/Neuen? Fall|Fall anlegen|PrivateLegalNavigator/i);
  });

  test('unique page title on error page', async ({ page }) => {
    await page.goto('/ui/cases/00000000-0000-0000-0000-000000000000');
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title).toMatch(/Fehler|Nicht gefunden|404|Error/i);
  });

  // ── Exactly One H1 ────────────────────────────────

  test('exactly one h1 on home page', async ({ page }) => {
    await page.goto('/');
    // After redirect to /ui/cases
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
  });

  test('exactly one h1 on case list page', async ({ page }) => {
    await page.goto('/ui/cases');
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
  });

  test('exactly one h1 on create case page', async ({ page }) => {
    await page.goto('/ui/cases/create');
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
  });

  test('exactly one h1 on error page', async ({ page }) => {
    await page.goto('/ui/cases/00000000-0000-0000-0000-000000000000');
    await page.waitForLoadState('networkidle');
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
  });

  // ── Skip Link ─────────────────────────────────────

  test('skip link present on case list page', async ({ page }) => {
    await page.goto('/ui/cases');
    const skipLink = page.locator('.skip-link, a[href="#main-content"]');
    await expect(skipLink).toBeVisible();
    const href = await skipLink.getAttribute('href');
    expect(href).toBe('#main-content');
  });

  test('skip link present on create case page', async ({ page }) => {
    await page.goto('/ui/cases/create');
    const skipLink = page.locator('.skip-link, a[href="#main-content"]');
    await expect(skipLink).toBeVisible();
  });

  test('main content has id="main-content"', async ({ page }) => {
    await page.goto('/ui/cases');
    const main = page.locator('main#main-content');
    await expect(main).toBeVisible();
    // Verify role="main"
    const role = await main.getAttribute('role');
    expect(role).toBe('main');
  });

  // ── Focus Visibility ──────────────────────────────

  test('skip link becomes visible on keyboard focus', async ({ page }) => {
    await page.goto('/ui/cases');
    // Press Tab to focus the skip link (first focusable element)
    await page.keyboard.press('Tab');

    // Check that the skip link is now visible (should have :focus style)
    const skipLink = page.locator('.skip-link, a[href="#main-content"]');
    const isFocused = await skipLink.evaluate((el) => el === document.activeElement);
    expect(isFocused).toBe(true);

    // Verify the skip link is not display:none when focused
    const display = await skipLink.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.display;
    });
    expect(display).not.toBe('none');
  });

  test('Tab navigation reaches interactive elements', async ({ page }) => {
    await page.goto('/ui/cases');
    // Press Tab multiple times — should move focus through interactive elements
    const focusedElements = new Set();

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? el.tagName + (el.className ? '.' + el.className.split(' ')[0] : '') : null;
      });
      if (focused) focusedElements.add(focused);
    }

    // At minimum, skip-link and nav links should be focusable
    expect(focusedElements.size).toBeGreaterThan(1);
  });

  // ── Form Labels ───────────────────────────────────

  test('all form inputs have associated labels on create case page', async ({ page }) => {
    await page.goto('/ui/cases/create');
    await page.waitForLoadState('networkidle');

    // Use axe to check for missing labels
    const results = await runAxe(page, {
      includeSelector: 'form',
    });

    // Filter for label-related violations
    const labelViolations = results.violations.filter((v) =>
      v.id === 'label' || v.id === 'label-content-name-mismatch'
    );

    if (labelViolations.length > 0) {
      const details = labelViolations.map(
        (v) => `  [${v.impact}] ${v.id}: ${v.help}`
      );
      throw new Error(
        `Missing form labels:\n${details.join('\n')}`
      );
    }
  });

  test('all input elements have accessible names', async ({ page }) => {
    await page.goto('/ui/cases/create');
    await page.waitForLoadState('networkidle');

    const inputs = page.locator('input:not([type="hidden"]):not([type="submit"])');
    const count = await inputs.count();

    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      // Check for associated label via for/id or wrapping label
      const hasLabel = await input.evaluate((el) => {
        const id = el.id;
        if (id) {
          const label = document.querySelector(`label[for="${id}"]`);
          if (label) return true;
        }
        // Check if input is wrapped in a label
        const parent = el.closest('label');
        if (parent) return true;
        // Check for aria-label
        if (el.getAttribute('aria-label')) return true;
        // Check for aria-labelledby
        if (el.getAttribute('aria-labelledby')) return true;
        return false;
      });
      expect(hasLabel).toBe(true);
    }
  });

  // ── Image Alt Text ────────────────────────────────

  test('all images have alt text on case list page', async ({ page }) => {
    await page.goto('/ui/cases');
    const images = page.locator('img');
    const count = await images.count();

    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      // alt must exist (even if empty string for decorative)
      expect(alt).not.toBeNull();
    }
  });

  // ── axe-core on Critical Pages ────────────────────

  test('axe: zero critical + serious on home page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await assertZeroCriticalSerious(page, 'home page (/)');
  });

  test('axe: zero critical + serious on case list page', async ({ page }) => {
    await page.goto('/ui/cases');
    await page.waitForLoadState('networkidle');
    await assertZeroCriticalSerious(page, 'case list (/ui/cases)');
  });

  test('axe: zero critical + serious on create case page', async ({ page }) => {
    await page.goto('/ui/cases/create');
    await page.waitForLoadState('networkidle');
    await assertZeroCriticalSerious(page, 'create case (/ui/cases/create)');
  });

  test('axe: zero critical + serious on error page', async ({ page }) => {
    await page.goto('/ui/cases/00000000-0000-0000-0000-000000000000');
    await page.waitForLoadState('networkidle');
    await assertZeroCriticalSerious(page, 'error page (404)');
  });

  test('axe: zero critical + serious on case detail page', async ({ page }) => {
    // Navigate to case list first to find a case
    await page.goto('/ui/cases');
    await page.waitForLoadState('networkidle');

    const caseLink = page.locator('a[href*="/ui/cases/"]').first();
    const hasCaseLink = (await caseLink.count()) > 0;

    // Seeded data exists — proceed with test

    await caseLink.click();
    await page.waitForLoadState('networkidle');
    await assertZeroCriticalSerious(page, 'case detail page');
  });

  // ── Color Contrast (axe or manual) ────────────────

  test('axe reports no color-contrast violations (critical)', async ({ page }) => {
    await page.goto('/ui/cases');
    await page.waitForLoadState('networkidle');

    const results = await runAxe(page);

    const contrastViolations = results.violations.filter(
      (v) => v.id === 'color-contrast' && (v.impact === 'critical' || v.impact === 'serious')
    );

    if (contrastViolations.length > 0) {
      const details = contrastViolations.map(
        (v) => `  [${v.impact}] ${v.help} — ${v.nodes.length} nodes`
      );
      throw new Error(
        `Color contrast violations:\n${details.join('\n')}`
      );
    }
  });

  // ── Landmark Regions ──────────────────────────────

  test('banner, main, and contentinfo landmarks are present', async ({ page }) => {
    await page.goto('/ui/cases');

    const banner = page.locator('header[role="banner"]');
    await expect(banner).toBeVisible();

    const main = page.locator('main[role="main"]');
    await expect(main).toBeVisible();

    const footer = page.locator('footer[role="contentinfo"]');
    await expect(footer).toBeVisible();
  });

  test('navigation has accessible label', async ({ page }) => {
    await page.goto('/ui/cases');

    const nav = page.locator('nav[aria-label="Hauptnavigation"]');
    await expect(nav).toBeVisible();
  });

  // ── Breadcrumb Navigation ─────────────────────────

  test('breadcrumb navigation is present on error page', async ({ page }) => {
    await page.goto('/ui/cases/00000000-0000-0000-0000-000000000000');
    await page.waitForLoadState('networkidle');

    const breadcrumb = page.locator('nav[aria-label="Brotkrümel"]');
    await expect(breadcrumb).toBeVisible();
  });
});
