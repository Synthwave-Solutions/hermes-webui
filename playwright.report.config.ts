// Report-mode Playwright config (synthwave-test-suite, Part B).
//
// Separate from any CI config on purpose: CI keeps evidence only for failures,
// while the branded QA report needs a screenshot AND a video against every test,
// pass or fail, so a reviewer can see what actually ran.
//
// Parameterised by env so several feature areas can run concurrently, each
// against its own throwaway WebUI instance:
//   QA_BASE_URL   the instance under test        (default http://127.0.0.1:8899)
//   QA_OUT        where the raw evidence lands   (default ./synthwave-report/raw)
import { defineConfig, devices } from '@playwright/test'

const OUT = process.env.QA_OUT || 'synthwave-report/raw'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.QA_BASE_URL || 'http://127.0.0.1:8899',
    screenshot: 'on',
    video: 'on',
    trace: 'retain-on-failure',
    actionTimeout: 15_000,
  },
  reporter: [
    ['list'],
    ['json', { outputFile: `${OUT}/results.json` }],
    ['html', { outputFolder: `${OUT}/playwright-html`, open: 'never' }],
  ],
  outputDir: `${OUT}/test-results`,
})
