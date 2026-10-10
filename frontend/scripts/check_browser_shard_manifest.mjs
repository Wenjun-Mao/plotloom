import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const e2eRoot = path.join(frontendRoot, "e2e");
const manifestPath = path.join(e2eRoot, "browser-shard-manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const specExtension = /\.(?:spec|test)\.(?:[cm]?[jt]sx?)$/;
const browserGrep = process.env.BROWSER_GREP ?? ".*";

function fail(message) {
  console.error(`Browser shard manifest check failed: ${message}`);
  process.exit(1);
}

function discoverSpecs(directory = e2eRoot, prefix = "") {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...discoverSpecs(fullPath, relative));
    } else if (entry.isFile() && specExtension.test(entry.name)) {
      files.push(relative.replaceAll(path.sep, "/"));
    }
  }
  return files;
}

if (JSON.stringify(Object.keys(manifest).sort()) !== JSON.stringify(["1", "2"])) {
  fail('manifest must contain exactly shard keys "1" and "2"');
}

const expectedSpecs = discoverSpecs();
const assignmentCounts = new Map();
for (const shard of ["1", "2"]) {
  if (!Array.isArray(manifest[shard])) fail(`shard ${shard} must be an array`);
  for (const spec of manifest[shard]) {
    if (typeof spec !== "string") fail(`shard ${shard} contains a non-string spec path`);
    assignmentCounts.set(spec, (assignmentCounts.get(spec) ?? 0) + 1);
  }
}
const missing = expectedSpecs.filter((spec) => assignmentCounts.get(spec) !== 1);
const unexpected = [...assignmentCounts.keys()].filter((spec) => !expectedSpecs.includes(spec));
const repeated = [...assignmentCounts].filter(([, count]) => count > 1).map(([spec]) => spec);
if (missing.length || unexpected.length || repeated.length) {
  fail(JSON.stringify({ missing, unexpected, repeated }, null, 2));
}

function listTests(shard) {
  const env = { ...process.env };
  delete env.BROWSER_SHARD;
  if (shard !== undefined) env.BROWSER_SHARD = shard;
  const cli = path.join(frontendRoot, "node_modules", "@playwright", "test", "cli.js");
  const result = spawnSync(
    process.execPath,
    [cli, "test", "--list", "--config", "playwright.config.ts", `--grep=${browserGrep}`],
    { cwd: frontendRoot, env, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 },
  );
  const emptyShard =
    result.status === 1 &&
    result.stdout.includes("Total: 0 tests in 0 files") &&
    result.stderr.includes("No tests found");
  if (result.status !== 0 && !emptyShard) {
    fail(`Playwright --list failed for shard ${shard ?? "all"}:\n${result.stdout}\n${result.stderr}`);
  }
  const ids = result.stdout
    .split(/\r?\n/)
    .filter((line) => /^\s+.+\.(?:spec|test)\.(?:[cm]?[jt]sx?):\d+:\d+ › /.test(line))
    .map((line) => line.trim());
  if (ids.length === 0 && !emptyShard) {
    fail(`Playwright listed no test IDs for shard ${shard ?? "all"}`);
  }
  if (new Set(ids).size !== ids.length) fail(`Playwright listed duplicate test IDs for shard ${shard ?? "all"}`);
  return new Set(ids);
}

const all = listTests();
if (all.size === 0) fail("BROWSER_GREP selected no tests in the unsharded suite");
const shardOne = listTests("1");
const shardTwo = listTests("2");
if (browserGrep === ".*" && (shardOne.size === 0 || shardTwo.size === 0)) {
  fail("the full-suite BROWSER_GREP='.*' selection must populate both shards");
}
const overlap = [...shardOne].filter((id) => shardTwo.has(id));
const union = new Set([...shardOne, ...shardTwo]);
const missingCases = [...all].filter((id) => !union.has(id));
const unexpectedCases = [...union].filter((id) => !all.has(id));
if (overlap.length || missingCases.length || unexpectedCases.length) {
  fail(JSON.stringify({ overlap, missingCases, unexpectedCases }, null, 2));
}
console.log(
  `Browser shard manifest verified: ${expectedSpecs.length} specs; ${all.size} selected cases across shards ${shardOne.size}/${shardTwo.size}; zero overlap or missing cases (BROWSER_GREP preserved).`,
);
