import { test as base, expect } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const configDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(configDirectory, "../..");
const frontendRoot = path.resolve(configDirectory, "..");
const loopbackHost = "127.0.0.1";

export type Workbench = {
  apiOrigin: string;
  frontendOrigin: string;
  /** A test-owned process, deliberately outside the Plotloom API surface. */
  providerOrigin: string;
  /** Test-owned roots supplied to the production project-folder runtime. */
  outputsRoot: string;
  applicationDataRoot: string;
  /** Stops and starts the owned FastAPI process against its original data paths. */
  restartBackend: (overrides?: NodeJS.ProcessEnv) => Promise<void>;
};

type FrontendMode = "vite" | "checked-static";

type WorkbenchWorkerFixtures = {
  workbench: Workbench;
};

type ManagedProcess = {
  child: ChildProcess;
  label: string;
  output: () => string;
};

// Every browser journey starts the shipped project-folder composition. The
// typed offline H3 transport is the only provider seam; it cannot choose an
// alternate persistence model or route surface.
export const test = createWorkbenchTest("vite");
export const checkedStaticTest = createWorkbenchTest("checked-static");

function createWorkbenchTest(frontendMode: FrontendMode) {
  return base.extend<{}, WorkbenchWorkerFixtures>({
  workbench: [async ({}, use) => {
    const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "plotloom-e2e-"));
    const outputsRoot = path.join(temporaryRoot, "outputs");
    const applicationDataRoot = path.join(temporaryRoot, "application");
    const backendPort = await reserveLoopbackPort();
    const frontendPort = frontendMode === "vite" ? await reserveLoopbackPort() : undefined;
    const providerPort = await reserveLoopbackPort();
    const apiOrigin = `http://${loopbackHost}:${backendPort}`;
    const frontendOrigin = frontendPort
      ? `http://${loopbackHost}:${frontendPort}`
      : apiOrigin;
    const providerOrigin = `http://${loopbackHost}:${providerPort}`;
    const provider = startProcess(
      "external OpenAI-compatible fake",
      process.execPath,
      [path.join(configDirectory, "fixtures", "external-openai-provider.mjs"), "--port", String(providerPort)],
      {},
    );
    const backendEnvironment = {
      PLOTLOOM_HOST: loopbackHost,
      PLOTLOOM_PORT: String(backendPort),
      // PORT deliberately disables the runtime's fallback range, so this test
      // cannot accidentally exercise a different backend than its proxy.
      PORT: String(backendPort),
      TEXT_MODEL_API_KEY: "",
      IMAGE_MODEL_API_KEY: "",
      VIDEO_MODEL_API_KEY: "",
      ATLASCLOUD_API_KEY: "",
      PLOTLOOM_OUTPUTS_DIR: outputsRoot,
      PLOTLOOM_APPLICATION_DATA_DIR: applicationDataRoot,
    };
    const backendEntrypoint = "frontend/e2e/fake_video_runtime.py";
    let backend = startProcess("FastAPI", "uv", ["run", "python", backendEntrypoint], backendEnvironment);
    let frontend: ManagedProcess | undefined;

    try {
      await mkdir(outputsRoot, { recursive: true });
      await mkdir(applicationDataRoot, { recursive: true });
      await waitForHttp(`${providerOrigin}/control/status`, provider);
      await waitForHttp(`${apiOrigin}/openapi.json`, backend);
      if (frontendPort) {
        frontend = startProcess(
          "Vite",
          "npm",
          [
            "run",
            "dev",
            "--",
            "--port",
            String(frontendPort),
            "--strictPort",
          ],
          { PLOTLOOM_API_ORIGIN: apiOrigin },
          frontendRoot,
        );
        await waitForHttp(`${frontendOrigin}/v2/`, frontend);
      } else {
        // Exercise the same static mount used by the source-checkout runtime,
        // with no dev-server fallback in this fixture mode.
        await waitForHttp(`${frontendOrigin}/v2/`, backend);
      }
      await use({
        apiOrigin,
        frontendOrigin,
        providerOrigin,
        outputsRoot,
        applicationDataRoot,
        restartBackend: async (overrides = {}) => {
          await stopProcess(backend);
          await waitForHttpUnavailable(`${apiOrigin}/openapi.json`);
          backend = startProcess("FastAPI", "uv", ["run", "python", backendEntrypoint], { ...backendEnvironment, ...overrides });
          await waitForHttp(`${apiOrigin}/openapi.json`, backend);
        },
      });
    } finally {
      try {
        await stopProcess(frontend);
      } finally {
        try {
          await stopProcess(backend);
        } finally {
          try {
            await stopProcess(provider);
          } finally {
            await rm(temporaryRoot, { recursive: true, force: true });
          }
        }
      }
    }
  }, { scope: "worker" }],
  });
}

export { expect };

function startProcess(
  label: string,
  command: string,
  args: string[],
  additions: NodeJS.ProcessEnv,
  cwd = repositoryRoot,
): ManagedProcess {
  let output = "";
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, ...additions },
    detached: process.platform !== "win32",
    stdio: ["ignore", "pipe", "pipe"],
  });
  const append = (chunk: Buffer) => {
    output = `${output}${chunk.toString()}`.slice(-16_000);
  };
  child.stdout?.on("data", append);
  child.stderr?.on("data", append);
  return { child, label, output: () => output };
}

async function reserveLoopbackPort(): Promise<number> {
  const server = net.createServer();
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen({ host: loopbackHost, port: 0 }, resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    server.close();
    throw new Error("Unable to allocate a loopback port for Plotloom E2E.");
  }
  await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return address.port;
}

async function waitForHttpUnavailable(url: string): Promise<void> {
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    try {
      await fetch(url);
    } catch {
      return;
    }
    await delay(50);
  }
  throw new Error(`FastAPI remained reachable after its owned process exited: ${url}`);
}

async function waitForHttp(url: string, process: ManagedProcess): Promise<void> {
  const deadline = Date.now() + 25_000;
  let lastError = "";
  while (Date.now() < deadline) {
    if (process.child.exitCode !== null) {
      throw new Error(`${process.label} exited before becoming ready (code ${process.child.exitCode}).\n${process.output()}`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = `${response.status} ${response.statusText}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await delay(100);
  }
  throw new Error(`${process.label} did not become ready at ${url}: ${lastError}\n${process.output()}`);
}

async function stopProcess(process: ManagedProcess | undefined): Promise<void> {
  if (!process || process.child.exitCode !== null || !process.child.pid) return;
  const signal = (value: NodeJS.Signals) => {
    try {
      globalThis.process.platform !== "win32" ? globalThis.process.kill(-process.child.pid!, value) : process.child.kill(value);
    } catch {
      // The child can exit between the exit-code check and the signal.
    }
  };
  signal("SIGTERM");
  const graceful = await Promise.race([
    new Promise<boolean>((resolve) => process.child.once("exit", () => resolve(true))),
    delay(5_000).then(() => false),
  ]);
  if (!graceful && process.child.exitCode === null) {
    signal("SIGKILL");
    const forced = await Promise.race([
      new Promise<boolean>((resolve) => process.child.once("exit", () => resolve(true))),
      delay(2_000).then(() => false),
    ]);
    if (!forced && process.child.exitCode === null) {
      throw new Error(`${process.label} did not exit after SIGTERM and SIGKILL.\n${process.output()}`);
    }
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
