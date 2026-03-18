const path = require("path");
const { defineConfig } = require("playwright/test");

const port = process.env.PLAYWRIGHT_PORT || "4173";
const baseURL = `http://127.0.0.1:${port}`;

module.exports = defineConfig({
  testDir: "./playwright-tests",
  timeout: 45_000,
  fullyParallel: false,
  retries: 0,
  expect: {
    timeout: 5_000,
  },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  outputDir: "test-results/playwright",
  webServer: {
    command: `python server.py --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      APP_BASE_URL: baseURL,
      VENDOR_ATLAS_DB_PATH: path.join(process.cwd(), ".tmp_playwright", "vendor-atlas-playwright.db"),
    },
  },
});
