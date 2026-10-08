import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import type { Page, TestInfo } from "@playwright/test";
import { afterEach, expect, it, vi } from "vitest";
import { collectNativeMediaDiagnostics } from "../e2e/native-media-diagnostics";

vi.mock("node:fs/promises", async importOriginal => {
  const actual = await importOriginal<typeof import("node:fs/promises")>();
  const writeFile = vi.fn(async () => {});
  return { ...actual, writeFile, default: { ...actual, writeFile } };
});
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

function harness() {
  const handlers = new Map<string, (event: unknown) => void>();
  const cdp = { on: vi.fn(), send: vi.fn(async () => {}), detach: vi.fn(async () => {}) };
  const page = {
    context: () => ({ newCDPSession: async () => cdp }),
    on: vi.fn((type: string, handler: (event: unknown) => void) => handlers.set(type, handler)),
    off: vi.fn((type: string) => handlers.delete(type)),
    evaluate: vi.fn(async () => ({ trace: [], videos: [{ currentTime: 0, ended: false }] })),
  };
  const info = { status: "failed", expectedStatus: "passed", outputPath: (name: string) => `/diagnostics/${name}`, attach: vi.fn(async () => {}) };
  return { page, info, cdp, handlers,
    collect: () => collectNativeMediaDiagnostics(page as unknown as Page, info as unknown as TestInfo) };
}
function response(body: () => Promise<Buffer>) {
  return { url: () => "http://localhost/api/v2/projects/qa/video-jobs/qa/playback", status: () => 206,
    headers: () => ({ "content-range": "bytes 0-3/4" }), body };
}

it("retains exact failed-playback bytes and their identity before cleaning up", async () => {
  const fixture = harness(); const retain = await fixture.collect();
  const bytes = Buffer.from([1, 2, 3, 4]);
  fixture.handlers.get("response")!(response(async () => bytes));
  await retain();
  const evidence = JSON.parse(vi.mocked(writeFile).mock.calls[0][1] as string);
  expect(evidence.snapshot.videos[0]).toMatchObject({ currentTime: 0, ended: false });
  expect(evidence.responses[0]).toMatchObject({ status: 206, bodyState: "complete", byteCount: 4,
    sha256: createHash("sha256").update(bytes).digest("hex") });
  expect(writeFile).toHaveBeenCalledWith("/diagnostics/native-playback-response-0.mp4", bytes);
  expect(fixture.info.attach).toHaveBeenCalledTimes(2);
  expect(fixture.handlers.size).toBe(0); expect(fixture.cdp.detach).toHaveBeenCalledOnce();
});

it("retains pending-body evidence and cleans up even when the renderer and body never settle", async () => {
  vi.useFakeTimers(); const fixture = harness();
  fixture.page.evaluate.mockImplementation(() => new Promise(() => {}));
  const retain = await fixture.collect();
  fixture.handlers.get("response")!(response(() => new Promise(() => {})));
  const retaining = retain(); await vi.advanceTimersByTimeAsync(2100); await retaining;
  const evidence = JSON.parse(vi.mocked(writeFile).mock.calls[0][1] as string);
  expect(evidence.snapshot.unavailable).toContain("diagnostic budget");
  expect(evidence.responses[0]).toMatchObject({ bodyState: "pending", byteCount: null, sha256: null });
  expect(writeFile).toHaveBeenCalledTimes(1);
  expect(fixture.handlers.size).toBe(0); expect(fixture.cdp.detach).toHaveBeenCalledOnce();
});

it("cleans up when evidence persistence fails rather than leaking observers", async () => {
  const fixture = harness(); const retain = await fixture.collect();
  vi.mocked(writeFile).mockRejectedValueOnce(new Error("evidence disk unavailable"));
  await expect(retain()).rejects.toThrow("evidence disk unavailable");
  expect(fixture.handlers.size).toBe(0); expect(fixture.cdp.detach).toHaveBeenCalledOnce();
});

it("labels an incomplete HTTP byte range as data, never as a standalone MP4", async () => {
  const fixture = harness(); const retain = await fixture.collect();
  fixture.handlers.get("response")!({ ...response(async () => Buffer.from([3, 4])),
    headers: () => ({ "content-range": "bytes 2-3/4" }) });
  await retain();
  expect(writeFile).toHaveBeenCalledWith("/diagnostics/native-playback-response-0-range-data.bin", Buffer.from([3, 4]));
  expect(fixture.info.attach).toHaveBeenCalledWith("native-playback-response-0", {
    path: "/diagnostics/native-playback-response-0-range-data.bin", contentType: "application/octet-stream",
  });
  const evidence = JSON.parse(vi.mocked(writeFile).mock.calls[0][1] as string);
  expect(evidence.responses[0]).toMatchObject({ headers: { "content-range": "bytes 2-3/4" }, byteCount: 2 });
});

it("writes passing-run diagnostics without treating a diagnostic detach stall as gameplay", async () => {
  vi.useFakeTimers(); const fixture = harness(); fixture.info.status = "passed";
  fixture.cdp.detach.mockImplementation(() => new Promise(() => {}));
  const retain = await fixture.collect(); const retaining = retain();
  await vi.advanceTimersByTimeAsync(1100); await retaining;
  expect(writeFile).toHaveBeenCalledTimes(1); expect(fixture.info.attach).toHaveBeenCalledOnce();
  expect(fixture.handlers.size).toBe(0);
});
