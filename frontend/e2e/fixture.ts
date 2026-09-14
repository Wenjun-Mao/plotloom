import { test as base, expect } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtemp, mkdir, readdir, rm } from "node:fs/promises";
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
  /** Present only for production project-folder browser journeys. */
  outputsRoot?: string;
  applicationDataRoot?: string;
  /** Stops and starts the owned FastAPI process against its original data paths. */
  restartBackend: (overrides?: NodeJS.ProcessEnv) => Promise<void>;
};

type WorkbenchWorkerFixtures = {
  workbench: Workbench;
};

type ManagedProcess = {
  child: ChildProcess;
  label: string;
  output: () => string;
};

type E2eVideoAdapter = "wan" | "h3";
type E2eStorageMode = "legacy" | "project-folder";

// Retained UI journeys remain on their test-only legacy surface until the
// lifecycle/caller migration is separately accepted. Project-folder journeys
// exercise the shipped production factory directly.
export const test = createWorkbenchTest("wan", "legacy");
export const h3Test = createWorkbenchTest("h3", "legacy");
export const projectFolderTest = createWorkbenchTest("h3", "project-folder");

function createWorkbenchTest(
  videoAdapter: E2eVideoAdapter,
  storageMode: E2eStorageMode,
) {
  return base.extend<{}, WorkbenchWorkerFixtures>({
  workbench: [async ({}, use) => {
    // The retained fixture is a transition-only browser matrix. It never
    // starts through the production entrypoint or its configuration parser.
    const retainedPilotRoot = videoAdapter === "wan" ? process.env.PLOTLOOM_P0_RESTART_PILOT_ROOT : undefined;
    if (retainedPilotRoot && !path.isAbsolute(retainedPilotRoot)) {
      throw new Error("PLOTLOOM_P0_RESTART_PILOT_ROOT must be an absolute path.");
    }
    const temporaryRoot = retainedPilotRoot ?? await mkdtemp(path.join(os.tmpdir(), "plotloom-e2e-"));
    if (retainedPilotRoot) {
      await mkdir(temporaryRoot, { recursive: true });
      const existingEntries = await readdir(temporaryRoot);
      if (existingEntries.length > 0) {
        throw new Error(`Retained P0 restart pilot directory must be empty: ${temporaryRoot}`);
      }
    }
    const outputsRoot = path.join(temporaryRoot, "outputs");
    const applicationDataRoot = path.join(temporaryRoot, "application");
    const legacyDatabasePath = path.join(temporaryRoot, "legacy.sqlite3");
    const legacyArtifactRoot = path.join(temporaryRoot, "legacy-artifacts");
    const legacyImageExchangeRoot = path.join(temporaryRoot, "legacy-image-exchange");
    const backendPort = await reserveLoopbackPort();
    const frontendPort = await reserveLoopbackPort();
    const providerPort = await reserveLoopbackPort();
    const apiOrigin = `http://${loopbackHost}:${backendPort}`;
    const frontendOrigin = `http://${loopbackHost}:${frontendPort}`;
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
      PLOTLOOM_E2E_VIDEO_ADAPTER: videoAdapter,
      ...(storageMode === "project-folder" ? {
        PLOTLOOM_OUTPUTS_DIR: outputsRoot,
        PLOTLOOM_APPLICATION_DATA_DIR: applicationDataRoot,
      } : {
        PLOTLOOM_E2E_LEGACY_DATABASE_PATH: legacyDatabasePath,
        PLOTLOOM_E2E_LEGACY_ARTIFACT_ROOT: legacyArtifactRoot,
        PLOTLOOM_E2E_LEGACY_IMAGE_EXCHANGE_ROOT: legacyImageExchangeRoot,
      }),
    };
    const backendEntrypoint = storageMode === "project-folder"
      ? "frontend/e2e/fake_video_runtime.py"
      : "frontend/e2e/legacy_runtime.py";
    let backend = startProcess("FastAPI", "uv", ["run", "python", backendEntrypoint], backendEnvironment);
    let frontend: ManagedProcess | undefined;

    try {
      if (storageMode === "project-folder") {
        await mkdir(outputsRoot, { recursive: true });
        await mkdir(applicationDataRoot, { recursive: true });
      } else {
        await mkdir(legacyArtifactRoot, { recursive: true });
        await mkdir(legacyImageExchangeRoot, { recursive: true });
      }
      await waitForHttp(`${providerOrigin}/control/status`, provider);
      await waitForHttp(`${apiOrigin}/openapi.json`, backend);
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
      await use({
        apiOrigin,
        frontendOrigin,
        providerOrigin,
        outputsRoot: storageMode === "project-folder" ? outputsRoot : undefined,
        applicationDataRoot: storageMode === "project-folder" ? applicationDataRoot : undefined,
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
            if (!retainedPilotRoot) {
              await rm(temporaryRoot, { recursive: true, force: true });
            }
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
