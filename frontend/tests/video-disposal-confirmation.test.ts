import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPilotPanel } from "../src/video-pilot";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import type { VideoJob, VideoSegment } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const descriptors = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));
const shot = demoProject.storyboard.shots[0];
const candidate = (id: string, segments: VideoSegment[] = []): VideoJob => ({
  id, projectId: "project", state: "ingested", current: true, selected: false, selectionRevision: 7,
  requestedSeconds: 5, cancelRequestedAt: null, providerPredictionId: null, outputHash: "fixture",
  observed: null, error: null, reviews: [], segments, snapshot: { shot },
});
const retainedSegment: VideoSegment = {
  id: "retained-segment", videoJobId: "protected", shotId: shot.id,
  inFrame: 0, outFrame: 144, authoredDurationUnits: 6000,
  sourceProbe: { frameCount: 192, fps: "24/1" }, derivativeProbe: { frameCount: 144, fps: "24/1" }, derivativeHash: "fixture", current: false,
  selected: false, selectedRevision: null, createdAt: "2026-10-02T00:00:00Z",
};
const dialog = () => document.querySelector<HTMLDialogElement>("dialog")!;
const button = (text: string) => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === text)!;
async function click(element: HTMLButtonElement) { await act(async () => element.click()); }
async function render() {
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId: "project", shot, selectionRevision: 7, storyboardRevision: 1, mediaReadPhase: "ready", readOnly: false,
    storyboard: demoProject.storyboard, sceneBeats: demoProject.sceneBeats, graph: demoProject.storyGraph,
  })));
}
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 0, reservedSeconds: 0, remainingSeconds: 0, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue({ revision: 0, assetId: null });
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
});
afterEach(async () => {
  await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  ["showModal", "close"].forEach((name, index) => { if (descriptors[index]) Object.defineProperty(HTMLDialogElement.prototype, name, descriptors[index]!); else Reflect.deleteProperty(HTMLDialogElement.prototype, name); });
});

it("confirms only explicit disposable targets and excludes retained proposals from single and bulk deletion", async () => {
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [candidate("one"), candidate("two"), candidate("protected", [retainedSegment])] });
  const single = vi.spyOn(plotloomApi, "discardVideoJob").mockResolvedValue({} as never);
  const bulk = vi.spyOn(plotloomApi, "discardUnselectedVideoJobs").mockResolvedValue({} as never);
  await render();
  const protectedCard = host.querySelector('[data-testid="video-job-protected"]')!;
  expect(protectedCard.textContent).toContain("此原片已有保留片段，不能永久删除");
  expect([...protectedCard.querySelectorAll("button")].some(item => item.textContent === "永久删除")).toBe(false);
  await click(button("永久删除")); expect(single).not.toHaveBeenCalled();
  expect(dialog().textContent).toContain("此操作不可撤销");
  await click(dialog().querySelector<HTMLButtonElement>("button")!); expect(single).not.toHaveBeenCalled();
  await click(button("永久删除")); await click(dialog().querySelectorAll<HTMLButtonElement>("button")[1]);
  expect(single).toHaveBeenCalledExactlyOnceWith("project", "one", 7);
  await click(button("删除可清理的未选择候选")); expect(bulk).not.toHaveBeenCalled();
  expect(dialog().textContent).not.toContain("protected");
  await click(dialog().querySelector<HTMLButtonElement>("button")!); expect(bulk).not.toHaveBeenCalled();
  await click(button("删除可清理的未选择候选")); await click(dialog().querySelectorAll<HTMLButtonElement>("button")[1]);
  expect(bulk).toHaveBeenCalledExactlyOnceWith("project", shot.id, ["one", "two"], 7);
});

it("invalidates pending deletion when a retained proposal arrives without a new selection revision", async () => {
  const retrieving = { ...candidate("retrieving"), state: "submitted" as const };
  const jobs = vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [candidate("protected"), retrieving] });
  const single = vi.spyOn(plotloomApi, "discardVideoJob").mockResolvedValue({} as never);
  let finish!: (value: VideoJob) => void;
  vi.spyOn(plotloomApi, "reconcileVideoJob").mockImplementation(() => new Promise(done => { finish = done; }));
  await render(); await click(button("获取结果")); await click(button("永久删除"));
  const oldConfirm = dialog().querySelectorAll<HTMLButtonElement>("button")[1];
  jobs.mockResolvedValue({ jobs: [candidate("protected", [retainedSegment]), retrieving] });
  await act(async () => { finish(retrieving); });
  expect(dialog()).toBeNull(); await click(oldConfirm); expect(single).not.toHaveBeenCalled();
  expect(button("删除可清理的未选择候选")).toBeUndefined();
});
