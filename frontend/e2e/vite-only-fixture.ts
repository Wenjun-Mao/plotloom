import { test as base, expect } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pollHttpReadiness } from "./http-readiness";
import { waitForListenerOrigin } from "./listener-address";
import { usePageWithDrainedRoutes } from "./page-route-lifecycle";

const configDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(configDirectory, "..");

type OwnedVite = {
  child: ChildProcess;
  label: string;
  output: () => string;
};

type UiFixtures = {
  frontendOrigin: string;
};

function startVite(): OwnedVite {
  const child = spawn(process.execPath, [path.join(configDirectory, "fixtures", "vite-runtime.mjs")], {
    cwd: frontendRoot,
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  child.stdout?.setEncoding("utf8").on("data", (chunk: string) => { output += chunk; });
  child.stderr?.setEncoding("utf8").on("data", (chunk: string) => { output += chunk; });
  return { child, label: "UI-only Vite", output: () => output };
}

function hasExited(child: ChildProcess): boolean {
  return child.exitCode !== null || child.signalCode !== null;
}

function waitForExit(child: ChildProcess, timeoutMs: number): Promise<boolean> {
  if (hasExited(child)) return Promise.resolve(true);
  return new Promise(resolve => {
    const onExit = () => {
      clearTimeout(timer);
      resolve(true);
    };
    const timer = setTimeout(() => {
      child.removeListener("exit", onExit);
      resolve(hasExited(child));
    }, timeoutMs);
    child.once("exit", onExit);
    if (hasExited(child)) onExit();
  });
}

async function stopVite(process: OwnedVite): Promise<void> {
  const { child, label, output } = process;
  if (hasExited(child)) return;

  child.kill("SIGTERM");
  if (await waitForExit(child, 5_000)) return;

  child.kill("SIGKILL");
  if (!(await waitForExit(child, 5_000))) {
    throw new Error(`${label} did not exit after SIGTERM and SIGKILL.\n${output()}`);
  }
}

export const test = base.extend<{}, UiFixtures>({
  page: async ({ page }, use) => usePageWithDrainedRoutes(page, use),
  frontendOrigin: [async ({}, use) => {
    const vite = startVite();
    try {
      const deadline = Date.now() + 15_000;
      const origin = await waitForListenerOrigin(vite, "frontend", deadline);
      await pollHttpReadiness(`${origin}/v2/e2e/creator-confirmation-fixture.html`, vite, deadline);
      await use(origin);
    } finally {
      await stopVite(vite);
    }
  }, { scope: "worker" }],
});

export { expect };
