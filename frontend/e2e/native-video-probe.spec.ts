import { expect, test } from "./fixture";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const fixturePath = "/__e2e__/offline-h3-fixture.mp4";

async function offlineFixtureBytes(): Promise<Buffer> {
  // The established offline H3 test fixture writes only to TemporaryDirectory.
  // Keeping the bytes in this test process avoids a new tracked or retained clip.
  const program = [
    "import sys",
    "sys.path.insert(0, 'frontend/e2e/video_backends/minimax_h3')",
    "from offline_gateway import OfflineH3GatewayFake",
    "from plotloom.video_backends.minimax_h3 import DEFAULT_H3_PROFILE_ID",
    "gateway = OfflineH3GatewayFake()",
    "gateway.profile_id = DEFAULT_H3_PROFILE_ID",
    "sys.stdout.buffer.write(gateway.download('h3_0123456789abcdef0123456789abcdef'))",
  ].join("; ");
  return await new Promise((resolve, reject) => {
    const process = spawn("uv", ["run", "python", "-c", program], { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
    const output: Buffer[] = [];
    const errors: Buffer[] = [];
    process.stdout.on("data", (chunk: Buffer) => output.push(chunk));
    process.stderr.on("data", (chunk: Buffer) => errors.push(chunk));
    process.on("error", reject);
    process.on("exit", (code) => code === 0
      ? resolve(Buffer.concat(output))
      : reject(new Error(`offline H3 fixture failed (${code}): ${Buffer.concat(errors).toString()}`)));
  });
}

async function serveFixture(page: import("@playwright/test").Page, origin: string) {
  const bytes = await offlineFixtureBytes();
  await page.route(`${origin}${fixturePath}`, async (route) => {
    await route.fulfill({
      body: bytes,
      contentType: "video/mp4",
      headers: { "Accept-Ranges": "bytes", "Cache-Control": "no-store" },
    });
  });
}

async function installPlainPlayer(page: import("@playwright/test").Page, origin: string) {
  await page.goto(`${origin}/v2/`);
  await page.setContent(`
    <video id="player" preload="auto" src="${fixturePath}"></video>
    <button id="play">Play</button>
    <output id="trace"></output>
    <script>
      const video = document.querySelector('#player');
      const trace = [];
      const record = (type, detail = {}) => {
        trace.push({ type, time: Number(video.currentTime.toFixed(3)), paused: video.paused,
          ended: video.ended, connected: video.isConnected, identity: video === document.querySelector('#player'), ...detail });
        document.querySelector('#trace').textContent = JSON.stringify(trace);
      };
      for (const type of ['play', 'playing', 'pause', 'ended', 'error', 'timeupdate']) video.addEventListener(type, () => record(type));
      document.querySelector('#play').addEventListener('click', () => {
        record('click');
        Promise.resolve(video.play()).then(() => record('play-resolved'), (error) => record('play-rejected', { error: String(error) }));
      });
      window.readNativeTrace = () => trace;
    </script>
  `);
}

async function nativeTrace(page: import("@playwright/test").Page) {
  return page.evaluate(() => (window as typeof window & { readNativeTrace: () => unknown[] }).readNativeTrace());
}

test("plain same-origin offline H3 video plays and reaches a native end", async ({ page, workbench }) => {
  test.setTimeout(30_000);
  await serveFixture(page, workbench.frontendOrigin);
  await installPlainPlayer(page, workbench.frontendOrigin);
  const video = page.locator("#player");
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).readyState)).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Play" }).click();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).currentTime)).toBeGreaterThan(0);
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  const trace = await nativeTrace(page) as Array<{ type: string; connected: boolean; identity: boolean }>;
  expect(trace.map((event) => event.type)).toEqual(expect.arrayContaining(["click", "play", "play-resolved", "playing", "ended"]));
  expect(trace).not.toEqual(expect.arrayContaining([expect.objectContaining({ type: "play-rejected" })]));
  expect(trace.every((event) => event.connected && event.identity)).toBeTruthy();
});

test("isolated native video choice sequence holds, chooses, restarts, and reaches both endings", async ({ page, workbench }) => {
  test.setTimeout(65_000);
  await serveFixture(page, workbench.frontendOrigin);
  await installPlainPlayer(page, workbench.frontendOrigin);
  const video = page.locator("#player");
  const play = page.getByRole("button", { name: "Play" });
  const playToEnd = async () => {
    await play.click();
    await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  };
  await playToEnd();

  await page.evaluate((source) => {
    const video = document.querySelector<HTMLVideoElement>("#player")!;
    const trace = (window as typeof window & { readNativeTrace: () => unknown[] }).readNativeTrace;
    const activate = (label: string) => {
      video.src = source;
      video.load();
      document.querySelector("#trace")!.textContent = "";
      (window as typeof window & { readNativeTrace: () => unknown[] }).readNativeTrace = trace;
      document.querySelector("#play")!.textContent = label;
    };
    document.body.insertAdjacentHTML("beforeend", '<button id="left">A</button><button id="right">B</button><button id="restart">Restart</button>');
    document.querySelector("#left")!.addEventListener("click", () => activate("Play A"));
    document.querySelector("#right")!.addEventListener("click", () => activate("Play B"));
    document.querySelector("#restart")!.addEventListener("click", () => activate("Play"));
  }, fixturePath);
  await page.locator("#left").click();
  await page.locator("#play").click();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  await page.locator("#restart").click();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).currentTime)).toBe(0);
  await page.locator("#play").click();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  await page.locator("#right").click();
  await page.locator("#play").click();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).ended), { timeout: 9_000 }).toBeTruthy();
  const trace = await nativeTrace(page) as Array<{ type: string }>;
  expect(trace.filter((event) => event.type === "ended")).toHaveLength(4);
});
