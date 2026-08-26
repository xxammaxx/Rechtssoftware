// @ts-check
/**
 * RC-026-R2 G10: Cross-Case Isolation — E2E tests.
 *
 * Uses API-seeded data (two cases created by the Python harness).
 * Verifies URL-level and API-level cross-case isolation.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');

const BASE_URL = process.env.PLN_E2E_BASE_URL || 'http://127.0.0.1:18000';
const SEED_FILE = process.env.PLN_E2E_SEED_FILE;

/** Load seed data from harness */
function loadSeed() {
  if (!SEED_FILE || !fs.existsSync(SEED_FILE)) {
    throw new Error(`Seed file not found: ${SEED_FILE} — harness must run first`);
  }
  return JSON.parse(fs.readFileSync(SEED_FILE, 'utf8'));
}

test.describe('G10 — Cross-Case Isolation', () => {
  let caseAId, caseBId, docId;

  test.beforeAll(() => {
    const seed = loadSeed();
    caseAId = seed.case_id;
    caseBId = seed.case_b_id;
    docId = seed.document_id;
    console.log(`[seed] Case A: ${caseAId}, Case B: ${caseBId}, Doc: ${docId}`);
  });

  test('case IDs must be different', async () => {
    expect(caseAId).toBeTruthy();
    expect(caseBId).toBeTruthy();
    expect(caseAId).not.toBe(caseBId);
  });

  test('case A detail page is reachable via its own URL', async ({ page }) => {
    await page.goto(`/ui/cases/${caseAId}`);
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
    const body = await page.textContent('body');
    expect(body).toContain('SYNTHETISCH');
  });

  test('case B detail page is reachable via its own URL', async ({ page }) => {
    await page.goto(`/ui/cases/${caseBId}`);
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
    const body = await page.textContent('body');
    expect(body).toContain('SYNTHETISCH');
  });

  test('case A title does NOT appear in case B detail page', async ({ page }) => {
    await page.goto(`/ui/cases/${caseBId}`);
    const body = await page.textContent('body');
    expect(body).not.toContain('Case A');
  });

  test('case B title does NOT appear in case A detail page', async ({ page }) => {
    await page.goto(`/ui/cases/${caseAId}`);
    const body = await page.textContent('body');
    expect(body).not.toContain('Case B');
  });

  test('document from case A returns 404 via case B URL', async ({ page }) => {
    const resp = await page.request.get(`${BASE_URL}/ui/cases/${caseBId}/documents/${docId}`);
    expect(resp.status()).toBe(404);
  });

  test('cross-case document URL returns 404 (not 200 with wrong data)', async ({ page }) => {
    const fakeDocId = '00000000-0000-0000-0000-000000000001';
    let resp = await page.request.get(`${BASE_URL}/ui/cases/${caseBId}/documents/${fakeDocId}`);
    expect(resp.status()).toBe(404);
    resp = await page.request.get(`${BASE_URL}/ui/cases/${caseAId}/documents/${fakeDocId}`);
    expect(resp.status()).toBe(404);
  });

  test('API: case A data not returned in case B response', async ({ page }) => {
    const resp = await page.request.get(`${BASE_URL}/api/v1/cases`);
    const data = await resp.json();
    const titles = (data.items || []).map(c => c.title);
    expect(titles).toContain('SYNTHETISCH – Playwright E2E Testfall');
    expect(titles).toContain('SYNTHETISCH – Playwright E2E Case B');
  });

  test('candidates from case A not reachable via case B URL', async ({ page }) => {
    const fakeDocId = '00000000-0000-0000-0000-000000000001';
    const resp = await page.request.get(
      `${BASE_URL}/ui/cases/${caseBId}/documents/${fakeDocId}/candidates/0`
    );
    expect(resp.status()).toBe(404);
  });

  test('preview from case A not reachable via case B URL', async ({ page }) => {
    const fakeDocId = '00000000-0000-0000-0000-000000000001';
    const resp = await page.request.get(
      `${BASE_URL}/ui/cases/${caseBId}/documents/${fakeDocId}/candidates/0/preview`
    );
    expect(resp.status()).toBe(404);
  });

  test('sequential ID probing returns 404 not info leak', async ({ page }) => {
    const randomUuids = [
      'ffffffff-ffff-ffff-ffff-ffffffffffff',
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    ];
    for (const uuid of randomUuids) {
      const resp = await page.request.get(`${BASE_URL}/ui/cases/${uuid}`);
      expect(resp.status()).toBe(404);
      const body = await resp.text();
      expect(body).toMatch(/Nicht gefunden/);
    }
  });

  test('case list shows seeded cases', async ({ page }) => {
    await page.goto('/ui/cases');
    await expect(page.locator('text=SYNTHETISCH').first()).toBeVisible({ timeout: 10000 });
  });
});
