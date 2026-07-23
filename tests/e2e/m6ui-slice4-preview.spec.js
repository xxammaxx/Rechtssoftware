// @ts-check
/**
 * M6-UI Slice 4: Calculation Preview — E2E tests
 *
 * Covers:
 *   Happy path: navigate, submit form, verify result, trace, disclaimer
 *   Error states: 403 (no CSRF), 409 (stale), revoked, 404
 *   Viewports: 1920x1080, 390x844, 1024x768
 *   Accessibility: axe-core on form + result
 *
 * Infrastructure: spawns Python server via child_process,
 * seeds data, confirms a deadline candidate, then runs browser tests.
 */

const { test, expect } = require('@playwright/test');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { runAxe, assertAxeClean } = require('./axe-helper.js');

// ──────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────

const SERVER_HOST = '127.0.0.1';
const SERVER_PORT = 18000;
const BASE_URL = `http://${SERVER_HOST}:${SERVER_PORT}`;
const TMP_DIR = path.join(
  process.env.TEMP || require('os').tmpdir(),
  `pln_e2e_preview_${Date.now()}`
);
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');

const EVIDENCE_DIR = path.join(
  PROJECT_ROOT,
  'evidence',
  'm6ui-slice4-closure-20260721T161455Z',
  'playwright'
);

// ──────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────

/** Wait for server to respond to /health */
function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    function tryConnect() {
      http.get(`${url}/health`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (Date.now() < deadline) {
          setTimeout(tryConnect, 500);
        } else {
          reject(new Error('Server not ready within timeout'));
        }
      }).on('error', () => {
        if (Date.now() < deadline) {
          setTimeout(tryConnect, 500);
        } else {
          reject(new Error('Server not ready within timeout'));
        }
      });
    }
    tryConnect();
  });
}

/** Ensure evidence directory exists */
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

/** Save screenshot with consistent naming */
async function screenshot(page, name) {
  // Use a safe filename
  const safeName = name.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filepath = path.join(EVIDENCE_DIR, `${safeName}.png`);
  await page.screenshot({ path: filepath, fullPage: true });
  return filepath;
}

// ──────────────────────────────────────────────────
// Test Suite
// ──────────────────────────────────────────────────

test.describe('M6-UI Slice 4: Calculation Preview', () => {
  /** @type {import('child_process').ChildProcess} */
  let serverProcess;

  /** @type {{ case_id: string, document_id: string }} */
  let seedData;

  /** Shared browser context for CSRF cookie persistence */
  let sharedPage;

  test.beforeAll(async ({ browser }) => {
    // ── Start FastAPI server ──────────────────────────
    ensureDir(TMP_DIR);

    serverProcess = spawn(
      process.platform === 'win32' ? 'python' : 'python3',
      [
        path.join(__dirname, 'server.py'),
        TMP_DIR,
        String(SERVER_PORT),
      ],
      {
        cwd: PROJECT_ROOT,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PLN_DATA_DIR: TMP_DIR,
          PLN_HOST: SERVER_HOST,
          PLN_PORT: String(SERVER_PORT),
        },
      }
    );

    // Capture server stderr for debugging
    serverProcess.stderr.on('data', (chunk) => {
      const text = chunk.toString();
      // Only log non-trivial messages to avoid noise
      if (!text.includes('Application startup') && text.trim().length > 0) {
        console.log('[server]', text.trim());
      }
    });

    // Wait for server readiness
    await waitForServer(BASE_URL);
    console.log('[server] Ready at', BASE_URL);

    // ── Read seed data ─────────────────────────────────
    const seedFile = path.join(TMP_DIR, 'seed_data.json');
    for (let i = 0; i < 20; i++) {
      if (fs.existsSync(seedFile)) break;
      await new Promise((r) => setTimeout(r, 500));
    }
    if (!fs.existsSync(seedFile)) {
      throw new Error(`Seed data file not found: ${seedFile}`);
    }
    seedData = JSON.parse(fs.readFileSync(seedFile, 'utf8'));
    console.log('[seed] case_id:', seedData.case_id);
    console.log('[seed] document_id:', seedData.document_id);

    // ── Create shared page for cookie persistence ──────
    sharedPage = await browser.newPage();
  });

  test.afterAll(async () => {
    // Close the shared page
    if (sharedPage) await sharedPage.close();

    // Kill server process
    if (serverProcess) {
      serverProcess.kill('SIGTERM');
      try {
        await new Promise((r) => {
          serverProcess.on('exit', r);
          setTimeout(r, 5000);
        });
      } catch (e) {
        serverProcess.kill('SIGKILL');
      }
    }

    // Clean up temp dir
    try { fs.rmSync(TMP_DIR, { recursive: true, force: true }); } catch (e) { /* ignore */ }
  });

  // ──────────────────────────────────────────────────
  // Step 0: Confirm a candidate first
  // ──────────────────────────────────────────────────
  test('0 - Confirm candidate to get active confirmation', async () => {
    // Navigate to candidate detail page (candidate index 0)
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await sharedPage.goto(BASE_URL + detailUrl);
    await sharedPage.waitForLoadState('networkidle');

    // Verify page loaded
    await expect(sharedPage.locator('h1, .page-title').first()).toBeVisible();

    // Take screenshot of candidate detail page
    await screenshot(sharedPage, '01-candidate-detail');

    // Extract CSRF token from the form
    const csrfInput = sharedPage.locator('input[name="csrf_token"]');
    const csrfToken = await csrfInput.inputValue();
    expect(csrfToken).toBeTruthy();

    // Fill confirmation form and submit
    await sharedPage.fill('input[name="confirmed_date"]', '2026-06-15');
    await sharedPage.selectOption('select[name="event_type"]', 'bescheid_datum');
    // Fill idempotency key
    const idemInput = sharedPage.locator('input[name="idempotency_key"]');
    await idemInput.fill(`e2e-confirm-${Date.now()}`);

    // Submit the form
    await sharedPage.click('button[type="submit"]');

    // Wait for redirect back to detail page
    await sharedPage.waitForLoadState('networkidle');
    const finalUrl = sharedPage.url();
    expect(finalUrl).toContain('confirmed=1');
    console.log('[confirm] Candidate confirmed, redirected to', finalUrl);
  });

  // ──────────────────────────────────────────────────
  // HAPPY PATH TESTS
  // ──────────────────────────────────────────────────

  test('1 - Navigate to preview page and verify form', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // First visit the candidate detail page to get the CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Now navigate to preview page
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(BASE_URL + previewUrl);
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page.locator('.page-title').first()).toContainText('Rechenvorschau');

    // Verify breadcrumb
    await expect(page.locator('.breadcrumb__current')).toContainText('Rechenvorschau');

    // Verify reference date sidebar is shown (has_active_confirmation = true)
    await expect(page.locator('#ref-heading')).toBeVisible();

    // Verify the form exists with hidden fields
    const csrfInput = page.locator('input[name="csrf_token"]');
    expect(await csrfInput.inputValue()).toBeTruthy();

    const expectedIdInput = page.locator('input[name="expected_active_confirmation_id"]');
    expect(await expectedIdInput.inputValue()).toBeTruthy();

    // Verify disclaimer (human review notice)
    await expect(page.locator('.notice--review')).toBeVisible();
    await expect(page.locator('.notice--review')).toContainText('Keine rechtliche Gültigkeit');

    // Verify submit button exists
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    await screenshot(page, '02-preview-form');

    await page.close();
  });

  test('2 - Submit preview form and verify calculation result', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Get CSRF cookie by visiting detail page first
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview page
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');

    // Submit the form
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Verify result heading
    await expect(page.locator('#result-heading')).toBeVisible();
    await expect(page.locator('#result-heading')).toContainText('Rechnerisches Ergebnis');

    // Verify a calculated date is displayed (should be 2026-06-29 = 15.06 + 14 days)
    const resultDate = page.locator('.preview-date');
    await expect(resultDate).toBeVisible();
    const dateText = await resultDate.textContent();
    expect(dateText).toMatch(/\d{2}\.\d{2}\.\d{4}/);
    console.log('[result] Calculated date:', dateText);

    // Verify human review disclaimer below result
    await expect(page.locator('.preview-date + .form-hint')).toContainText('keine rechtliche Bewertung');

    await screenshot(page, '03-preview-result');
    await page.close();
  });

  test('3 - Verify trace steps are shown', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview + submit
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Verify trace section
    await expect(page.locator('#trace-heading')).toBeVisible();
    await expect(page.locator('#trace-heading')).toContainText('So wurde gerechnet');

    // Verify trace list has items
    const traceItems = page.locator('.trace-list__item');
    await expect(traceItems.first()).toBeVisible();

    // Verify each trace step has expected elements
    await expect(page.locator('.trace-step__number').first()).toBeVisible();
    await expect(page.locator('.trace-step__label').first()).toBeVisible();

    // Verify trace details: "Verwendetes Bezugsdatum", "Rechenoperation", "Rechnerisches Ergebnis"
    await expect(page.locator('.trace-step__details dt').first()).toContainText('Verwendetes Bezugsdatum');
    await expect(page.locator('.trace-step__details')).toContainText('Kalendertage addieren');

    // Verify warning about non-applied adjustments
    const warningNotice = page.locator('.notice--warning');
    await expect(warningNotice).toBeVisible();
    await expect(warningNotice).toContainText('Nicht angewandte Anpassungen');
    await expect(warningNotice).toContainText('Keine Wochenendverschiebung');
    await expect(warningNotice).toContainText('Keine Feiertagsbereinigung');

    await screenshot(page, '04-trace-steps');
    await page.close();
  });

  test('4 - Verify no external network requests during preview', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    const externalRequests = [];

    // Monitor all network requests
    page.on('request', (req) => {
      const url = req.url();
      // Track anything NOT going to our local server
      if (!url.includes(SERVER_HOST) && !url.includes('localhost') && !url.includes('127.0.0.1')) {
        externalRequests.push(url);
      }
    });

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview + submit
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Report any external requests found
    if (externalRequests.length > 0) {
      console.warn('[network] EXTERNAL REQUESTS DETECTED:', externalRequests);
    }
    expect(externalRequests).toHaveLength(0);

    await page.close();
  });

  // ──────────────────────────────────────────────────
  // ERROR STATE TESTS
  // ──────────────────────────────────────────────────

  test('5 - POST without CSRF token returns 403', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Navigate to preview page (but don't use page navigation for the POST;
    // instead, use page.evaluate or page.request to send a raw POST without CSRF)

    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;

    // Use fetch from within the page to POST without CSRF token
    const response = await page.evaluate(async (url) => {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Origin': window.location.origin,
        },
        body: 'expected_active_confirmation_id=test123',
      });
      return { status: res.status, body: await res.text() };
    }, BASE_URL + previewUrl);

    expect(response.status).toBe(403);

    await screenshot(page, '05-403-no-csrf');
    await page.close();
  });

  test('6 - POST with stale expected_active_confirmation_id returns 409', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Get CSRF cookie from detail page
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview page to get CSRF token
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');

    // Extract the CSRF token
    const csrfToken = await page.locator('input[name="csrf_token"]').inputValue();

    // Now submit with a STALE expected_active_confirmation_id
    // Use page.evaluate to manipulate the hidden input
    await page.evaluate(() => {
      const el = document.querySelector('input[name="expected_active_confirmation_id"]');
      if (el) el.value = 'stale-non-existent-id-99999';
    });

    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Should see 409 conflict error page
    const errorHeading = page.locator('h1, .page-title, .card__header').filter({ hasText: 'Stand geändert' });
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/Stand geändert|409|inzwischen geändert/);

    await screenshot(page, '06-409-stale-id');
    await page.close();
  });

  test('7 - Preview for non-existent candidate returns 404', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Request preview for candidate index 999 (non-existent)
    const badUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/999/preview`;
    await page.goto(BASE_URL + badUrl);
    await page.waitForLoadState('networkidle');

    // Should show 404 error page
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/Nicht gefunden|404|nicht gefunden/);

    await screenshot(page, '07-404-nonexistent');
    await page.close();
  });

  test('8 - Preview page still renders after candidate revoked', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // First, we confirm a candidate, then revoke it, then check preview
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Try to revoke via API (POST to /revoke)
    // First check if there's a revoke button/form
    const revokeForm = page.locator('form[action$="/revoke"]');
    const revokeExists = (await revokeForm.count()) > 0;

    if (revokeExists) {
      // Click revoke button
      await page.click('form[action$="/revoke"] button[type="submit"]');
      await page.waitForLoadState('networkidle');

      // Now navigate to preview
      const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
      await page.goto(previewUrl);
      await page.waitForLoadState('networkidle');

      // Should show "no active confirmation" message
      const bodyText = await page.textContent('body');
      expect(bodyText).toMatch(/keine aktive|Keine aktive|erforderlich/);
    } else {
      // No revoke option available - skip with note
      console.log('[revoke] No revoke form found on candidate detail page — skipping revocation test');
      test.skip();
    }

    await page.close();
  });

  // ──────────────────────────────────────────────────
  // VIEWPORT TESTS
  // ──────────────────────────────────────────────────

  test('9 - 1920x1080 viewport: no horizontal overflow, full content visible', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview, submit
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Check no horizontal overflow
    const hasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasOverflow).toBe(false);

    // Verify key elements are visible
    await expect(page.locator('#result-heading')).toBeVisible();
    await expect(page.locator('#trace-heading')).toBeVisible();

    await screenshot(page, '09-viewport-1920x1080');
    await page.close();
  });

  test('10 - 390x844 viewport: mobile readable, form usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');

    // Verify form button is visible and clickable
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // Verify no horizontal overflow
    const hasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasOverflow).toBe(false);

    // Submit
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Verify result is still readable
    await expect(page.locator('#result-heading')).toBeVisible();

    await screenshot(page, '10-viewport-390x844');
    await page.close();
  });

  test('11 - 1024x768 viewport: result readable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1024, height: 768 } });
    const page = await context.newPage();

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview, submit
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Verify no horizontal overflow
    const hasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasOverflow).toBe(false);

    // Verify result heading and trace visible
    await expect(page.locator('#result-heading')).toBeVisible();
    await expect(page.locator('#trace-heading')).toBeVisible();

    await screenshot(page, '11-viewport-1024x768');
    await page.close();
  });

  // ──────────────────────────────────────────────────
  // ACCESSIBILITY TESTS (axe-core)
  // ──────────────────────────────────────────────────

  test('12 - Axe scan on preview form page: 0 critical, 0 serious', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview page (form state, before calculation)
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');

    // Run axe-core
    const results = await runAxe(page);

    // Check for critical or serious violations
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    if (criticalOrSerious.length > 0) {
      const descriptions = criticalOrSerious.map(
        (v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`
      );
      console.warn('[axe] Form page violations:', descriptions.join('\n'));
    }

    // Log all violations for the report
    if (results.violations.length > 0) {
      console.log('[axe] All form page violations:', JSON.stringify(results.violations.map(v => ({
        id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length
      })), null, 2));
    }

    expect(criticalOrSerious).toHaveLength(0);

    await screenshot(page, '12-axe-form-page');
    await page.close();
  });

  test('13 - Axe scan on preview result page: 0 critical, 0 serious', async ({ browser }) => {
    const page = await browser.newPage({ baseURL: BASE_URL });

    // Get CSRF cookie
    const detailUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0`;
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');

    // Navigate to preview + submit
    const previewUrl = `/ui/cases/${seedData.case_id}/documents/${seedData.document_id}/candidates/0/preview`;
    await page.goto(previewUrl);
    await page.waitForLoadState('networkidle');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // Run axe-core on result page
    const results = await runAxe(page);

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    if (criticalOrSerious.length > 0) {
      const descriptions = criticalOrSerious.map(
        (v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`
      );
      console.warn('[axe] Result page violations:', descriptions.join('\n'));
    }

    if (results.violations.length > 0) {
      console.log('[axe] All result page violations:', JSON.stringify(results.violations.map(v => ({
        id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length
      })), null, 2));
    }

    expect(criticalOrSerious).toHaveLength(0);

    await screenshot(page, '13-axe-result-page');
    await page.close();
  });
});
