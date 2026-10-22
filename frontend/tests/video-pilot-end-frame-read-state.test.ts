import { act, createElement, type ComponentProps } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi, type H3PromptPreview, type VideoEndFrameDecision } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoPilotPanel } from "../src/video-pilot";
import type { ManagedAsset, ReviewedKeyframe, VideoBackend, VideoJob } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const shot = { ...demoProject.storyboard.shots[0], durationUnits: 5_000 };
const keyframe: ManagedAsset = { id: "frame", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64), mimeType: "image/png", byteSize: 1, width: 832, height: 480, createdAt: "2026-10-08T00:00:00Z", provenance: null };
const binding: ReviewedKeyframe = { id: "binding", assetId: keyframe.id, shotId: shot.id, sceneId: shot.sceneId, selectionRevision: 1, visualIntentId: "intent", visualIntentRevision: 1, compatibilityNote: "technical fixture" };
const backend: VideoBackend = {
  enabled: true, adapterId: "minimax_h3_gateway", nativeAudio: true, tracksPaidWanPilot: false,
  qualifiedDurationSeconds: [5], defaultProfileId: "landscape",
  profiles: [{ id: "landscape", version: 2, label: "Landscape", quality: 8, orientation: "landscape", tier: "fast", width: 832, height: 480, durationSeconds: 5, fps: 24, frameCount: 124, nativeAudio: true }],
};
const source: H3PromptPreview = { sourceHash: "c".repeat(64), compiledPrompt: null, sources: [{ path: "shot.action", text: "作者动作", label: "动作" }] };
const compiled = { ...source, compiledPrompt: "Exact reviewed prompt", compiledPromptSha256: "d".repeat(64) };
const empty: VideoEndFrameDecision = { revision: 0, assetId: null };
function pending<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const button = (name: string) => [...host.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === name);
const editor = () => host.querySelector<HTMLTextAreaElement>(".h3-direction-field textarea")!;
const seed = () => host.querySelector<HTMLInputElement>('[aria-label="H3 随机种子"]')!;
const consent = () => host.querySelector<HTMLInputElement>(".h3-direction-check input")!;
async function click(name: string) { await act(async () => button(name)!.click()); }
async function edit(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  await act(async () => {
    const prototype = element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function render(overrides: Partial<ComponentProps<typeof VideoPilotPanel>> = {}) {
  await act(async () => root.render(createElement(VideoPilotPanel, {
    projectId: "project", shot, approvalId: "approval", storyboardRevision: 1, selectionRevision: 1,
    keyframe, reviewedBinding: binding, mediaReadPhase: "ready", readOnly: false,
    storyboard: { ...demoProject.storyboard, shots: [shot] }, sceneBeats: demoProject.sceneBeats, graph: demoProject.storyGraph,
    ...overrides,
  })));
}
async function beginReview() {
  await render(); await edit(seed(), "20261008"); await click("读取当前来源");
  await edit(editor(), "The visible lamp remains by the window.");
  await act(async () => consent().click());
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getVideoPilotBudget").mockResolvedValue({ limitSeconds: 100, reservedSeconds: 0, remainingSeconds: 100, attempts: [] });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue(backend);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValue(empty);
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [keyframe] });
  vi.spyOn(plotloomApi, "previewH3Prompt").mockImplementation(async (_id, body) => body.reviewedDirections ? compiled : source);
  vi.spyOn(plotloomApi, "prepareVideoJob").mockResolvedValue({} as never);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it.each(["decision", "catalog"])("gates H3 during pending %s and recovery without writes", async operation => {
  const read = pending<never>();
  if (operation === "decision") vi.mocked(plotloomApi.getVideoEndFrame).mockReturnValueOnce(read.promise);
  else vi.mocked(plotloomApi.getManagedAssets).mockReturnValueOnce(read.promise);
  const save = vi.spyOn(plotloomApi, "chooseVideoEndFrame");
  await render();
  expect(button("读取当前来源")?.disabled).toBe(true);
  expect(host.textContent).not.toContain("当前已保存：");
  await act(async () => read.reject(new Error("offline")));
  expect(button("读取当前来源")?.disabled).toBe(true);
  await click("刷新末帧与图片列表");
  expect(button("读取当前来源")?.disabled).toBe(false);
  expect(host.textContent).toContain("当前设置：不使用末帧画面");
  expect(save).not.toHaveBeenCalled(); expect(plotloomApi.prepareVideoJob).not.toHaveBeenCalled();
});

it("withdraws compiled consent during a failed refresh and preserves seed/text for an exact reread", async () => {
  const refresh = pending<VideoEndFrameDecision>();
  vi.mocked(plotloomApi.getVideoEndFrame).mockResolvedValueOnce(empty).mockReturnValueOnce(refresh.promise).mockResolvedValueOnce(empty);
  await beginReview(); await click("预览完整 H3 提示词");
  expect(button("冻结此说明并准备原片")).toBeDefined();
  await click("刷新末帧与图片列表");
  expect(button("读取当前来源")?.disabled).toBe(true);
  expect(button("冻结此说明并准备原片")).toBeUndefined();
  expect(consent().checked).toBe(false);
  await act(async () => refresh.reject(new Error("refresh failed")));
  expect(seed().value).toBe("20261008");
  expect(editor().value).toBe("The visible lamp remains by the window.");
  await click("刷新末帧与图片列表");
  expect(button("读取当前来源")?.disabled).toBe(false);
  expect(editor().disabled).toBe(true);
  expect(button("预览完整 H3 提示词")?.disabled).toBe(true);
  await click("读取当前来源");
  expect(editor().value).toBe("The visible lamp remains by the window.");
  expect(editor().disabled).toBe(false); expect(consent().checked).toBe(false);
  expect(plotloomApi.prepareVideoJob).not.toHaveBeenCalled();
});

it.each([["read", "resolve"], ["read", "reject"], ["preview", "resolve"], ["preview", "reject"]])("ignores late %s/%s after end-frame readiness withdrawal", async (operation, disposition) => {
  const refresh = pending<VideoEndFrameDecision>();
  const prompt = pending<H3PromptPreview>();
  vi.mocked(plotloomApi.getVideoEndFrame).mockResolvedValueOnce(empty).mockReturnValueOnce(refresh.promise).mockResolvedValueOnce(empty);
  await beginReview();
  vi.mocked(plotloomApi.previewH3Prompt).mockReturnValueOnce(prompt.promise);
  await click(operation === "read" ? "读取当前来源" : "预览完整 H3 提示词");
  await click("刷新末帧与图片列表");
  await act(async () => refresh.reject(new Error("end-frame offline")));
  await act(async () => disposition === "resolve" ? prompt.resolve(operation === "read" ? { ...source, sourceHash: "e".repeat(64) } : compiled) : prompt.reject(new Error("late prompt failure")));
  expect(host.textContent).not.toContain("Exact reviewed prompt");
  expect(host.textContent).not.toContain("late prompt failure");
  expect(seed().value).toBe("20261008");
  expect(editor().value).toBe("The visible lamp remains by the window.");
  expect(button("读取当前来源")?.disabled).toBe(true);
  await click("刷新末帧与图片列表"); await click("读取当前来源");
  expect(editor().value).toBe("The visible lamp remains by the window.");
  expect(consent().checked).toBe(false); expect(plotloomApi.prepareVideoJob).not.toHaveBeenCalled();
});

it.each([{ projectId: "next-project" }, { shot: { ...shot, id: "next-shot" } }, { approvalId: "next-approval" }, { storyboardRevision: 2 }])("cannot inherit end-frame readiness after owner change %j", async overrides => {
  const old = pending<VideoEndFrameDecision>();
  const next = pending<VideoEndFrameDecision>();
  vi.mocked(plotloomApi.getVideoEndFrame).mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
  await render(); await render(overrides);
  await act(async () => old.resolve(empty));
  expect(button("读取当前来源")?.disabled).toBe(true);
  await act(async () => next.resolve(empty));
  expect(button("读取当前来源")?.disabled).toBe(false);
  expect(plotloomApi.prepareVideoJob).not.toHaveBeenCalled();
});

it("withdraws H3 eligibility while saving and after an unknown save outcome", async () => {
  const write = pending<VideoEndFrameDecision>();
  const save = vi.spyOn(plotloomApi, "chooseVideoEndFrame").mockReturnValue(write.promise);
  await beginReview(); await click("预览完整 H3 提示词");
  await click("保存当前镜头末帧决定");
  expect(button("读取当前来源")?.disabled).toBe(true);
  expect(button("冻结此说明并准备原片")).toBeUndefined();
  await act(async () => write.reject(new Error("unknown save")));
  expect(button("读取当前来源")?.disabled).toBe(true);
  expect(editor().value).toBe("The visible lamp remains by the window.");
  await click("刷新末帧与图片列表");
  expect(button("读取当前来源")?.disabled).toBe(false);
  expect(consent().checked).toBe(false); expect(save).toHaveBeenCalledTimes(1);
  expect(plotloomApi.prepareVideoJob).not.toHaveBeenCalled();
});

it.each([undefined, 1, 8])("shows only explicit frozen quality %s, without a retired profile-name inference", async quality => {
  const job = { id: "frozen", projectId: "project", state: "prepared", current: true, selected: false, selectionRevision: 0, reviews: [], requestedSeconds: 5, snapshot: { shot, provider: { adapterId: "minimax_h3_gateway" }, request: { profileId: "retired_quality1_profile", quality } } } as unknown as VideoJob;
  vi.mocked(plotloomApi.getVideoJobs).mockResolvedValue({ jobs: [job] });
  await render();
  expect(host.querySelector('[data-testid="video-job-frozen"]')?.textContent).toContain(`质量 ${quality ?? "未知"}`);
});
