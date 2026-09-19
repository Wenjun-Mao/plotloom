import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  // Each worker owns a FastAPI server, a file-SQLite database, and a fake
  // provider. The host-default CPU-count worker pool can starve their polling
  // and response-hold contracts; four workers keep the suite concurrent while
  // preserving those real-process timing guarantees.
  workers: 4,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  outputDir: "./test-results",
  reporter: process.env.CI ? [["list"], ["html", { outputFolder: "./playwright-report", open: "never" }]] : "list",
  use: {
    ...devices["Desktop Chrome"],
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});
