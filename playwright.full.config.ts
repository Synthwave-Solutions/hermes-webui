import { defineConfig, devices } from '@playwright/test';
// This suite targets ONLY the loopback fixture with synthetic state and signed users.
const baseURL = process.env.QA_BASE_URL || 'http://127.0.0.1:19086';
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(baseURL)) throw new Error('Full mutation suite requires the isolated loopback fixture');
const out = process.env.QA_OUT || '../e2e-results';
export default defineConfig({
  testDir: './tests/e2e/full', fullyParallel: false, workers: 1, retries: 0,
  timeout: 45_000, expect: { timeout: 10_000 },
  use: { ...devices['Desktop Chrome'], baseURL, viewport: { width: 1440, height: 1000 },
    screenshot: 'on', video: 'retain-on-failure', trace: 'retain-on-failure', actionTimeout: 10_000 },
  reporter: [['list'], ['json', { outputFile: `${out}/results.json` }], ['html', { outputFolder: `${out}/html`, open: 'never' }]],
  outputDir: `${out}/artifacts`,
});
