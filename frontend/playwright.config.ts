import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";

const browserShard = process.env.BROWSER_SHARD;
const browserShardIds = ["1", "2", "3", "4"] as const;
type BrowserShardId = (typeof browserShardIds)[number];
function parseBrowserShard(value: string | undefined): BrowserShardId | undefined {
  if (value === undefined) return undefined;
  if (browserShardIds.includes(value as BrowserShardId)) return value as BrowserShardId;
  throw new Error(`BROWSER_SHARD must be 1, 2, 3, or 4, received ${value}`);
}
const selectedBrowserShard = parseBrowserShard(browserShard);
const browserShardManifest = JSON.parse(
  readFileSync(new URL("./e2e/browser-shard-manifest.json", import.meta.url), "utf8"),
) as Record<BrowserShardId, string[]>;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  testMatch: selectedBrowserShard
    ? browserShardManifest[selectedBrowserShard].map((file) => `**/${file}`)
    : undefined,
  // CI assigns whole specs by historical duration, preserving within-file
  // order; without BROWSER_SHARD local runs still collect the complete suite.
  // Each test owns its own backend/provider or narrow UI fixture and data roots.
  // Limit local simultaneous stacks: the host-default CPU-count pool can
  // starve real-process polling and response-hold contracts.
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
