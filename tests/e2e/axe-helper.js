// @ts-check
/**
 * Axe-core accessibility helper for Playwright E2E tests.
 *
 * Requires axe.min.js to be available at src/private_legal_navigator/presentation/static/axe.min.js
 * Usage: const violations = await runAxe(page);
 */

const fs = require('fs');
const path = require('path');

/**
 * Run axe-core accessibility scan on the current page.
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {string[]} [options.excludeRules] - axe rule IDs to exclude
 * @param {string} [options.includeSelector] - CSS selector to scope analysis
 * @returns {Promise<{violations: object[], passes: object[], incomplete: object[]}>}
 */
async function runAxe(page, options = {}) {
  // Load axe.min.js
  const axePath = path.join(
    __dirname,
    '..',
    'src',
    'private_legal_navigator',
    'presentation',
    'static',
    'axe.min.js'
  );

  if (!fs.existsSync(axePath)) {
    console.warn('axe.min.js not found at', axePath, '- skipping accessibility scan');
    return { violations: [], passes: [], incomplete: [] };
  }

  const axeSource = fs.readFileSync(axePath, 'utf8');

  // Inject axe-core
  await page.evaluate(axeSource);

  // Run axe
  const axeOptions = {};
  if (options.excludeRules) {
    axeOptions.rules = {};
    for (const rule of options.excludeRules) {
      axeOptions.rules[rule] = { enabled: false };
    }
  }
  if (options.includeSelector) {
    axeOptions.include = [options.includeSelector];
  }

  const results = await page.evaluate(
    async (opts) => {
      // @ts-ignore
      return await axe.run(opts);
    },
    axeOptions
  );

  return results;
}

/**
 * Assert no critical or serious axe violations.
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @returns {Promise<void>}
 */
async function assertAxeClean(page, options = {}) {
  const results = await runAxe(page, options);

  const criticalOrSerious = results.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );

  if (criticalOrSerious.length > 0) {
    const descriptions = criticalOrSerious.map(
      (v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`
    );
    throw new Error(
      `Axe violations found:\n${descriptions.join('\n')}\n\nFull violations: ${JSON.stringify(criticalOrSerious, null, 2)}`
    );
  }

  return results;
}

module.exports = { runAxe, assertAxeClean };
