import { act, createElement, type ComponentProps } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import type { VideoEndFrameDecision } from "../src/api";
import { VideoEndFrameChoice } from "../src/video-end-frame";
import type { ManagedAsset } from "../src/types";
import { ApiError } from "../src/api-transport";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLDivElement;
let root: Root;
let onReadinessChange = vi.fn<(ready: boolean) => void>();
const pending = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const empty = (revision = 0): VideoEndFrameDecision => ({ revision, assetId: null });
const button = (text: string) => Array.from(host.querySelectorAll("button"))
  .find((item) => item.textContent === text) as HTMLButtonElement;
const render = async (projectId: string, onDecision: (decision: VideoEndFrameDecision) => void,
  overrides: Partial<ComponentProps<typeof VideoEndFrameChoice>> = {}) => {
  await act(async () => root.render(createElement(VideoEndFrameChoice, {
    projectId, shotId: "same-shot", approvalId: "approval", storyboardRevision: 1,
    requestAspectPolicy: "reject_mismatch", readOnly: false, onDecision, onReadinessChange, ...overrides,
  })));
};

beforeEach(() => { onReadinessChange = vi.fn<(ready: boolean) => void>(); host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { vi.restoreAllMocks(); await act(async () => root.unmount()); host.remove(); });

it("retries a failed decision read and enables explicit save after recovery", async () => {
  const get = vi.spyOn(plotloomApi, "getVideoEndFrame")
    .mockRejectedValueOnce(new Error("temporary read error"))
    .mockResolvedValueOnce(empty());
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  const choose = vi.spyOn(plotloomApi, "chooseVideoEndFrame").mockResolvedValue(empty(1));
  const onDecision = vi.fn();
  await render("project", onDecision);
  expect(host.textContent).toContain("temporary read error");
  expect(button("保存当前镜头末帧决定").disabled).toBe(true);
  await act(async () => button("刷新末帧与图片列表").click());
  expect(get).toHaveBeenCalledTimes(2);
  expect(button("保存当前镜头末帧决定").disabled).toBe(false);
  await act(async () => button("保存当前镜头末帧决定").click());
  expect(choose).toHaveBeenCalledWith("project", "same-shot", expect.objectContaining({
    assetId: null, expectedRevision: 0, aspectPolicy: null,
  }));
  expect(onDecision).toHaveBeenLastCalledWith(empty(1));
});

it("ignores a late decision read from another project with the same shot ID", async () => {
  const old = pending<VideoEndFrameDecision>();
  vi.spyOn(plotloomApi, "getVideoEndFrame")
    .mockReturnValueOnce(old.promise).mockResolvedValueOnce(empty(2));
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  const onDecision = vi.fn();
  await render("old-project", onDecision);
  await render("new-project", onDecision);
  await act(async () => old.resolve(empty(1)));
  expect(onDecision).toHaveBeenCalledTimes(1);
  expect(onDecision).toHaveBeenLastCalledWith(empty(2));
  expect(host.textContent).toContain("当前已保存：不使用末帧画面 · 第 2 版");
});

it("does not publish a completed mutation after switching projects", async () => {
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValueOnce(empty()).mockResolvedValueOnce(empty(2));
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  const oldMutation = pending<VideoEndFrameDecision>();
  vi.spyOn(plotloomApi, "chooseVideoEndFrame").mockReturnValue(oldMutation.promise);
  const onDecision = vi.fn();
  await render("old-project", onDecision);
  await act(async () => button("保存当前镜头末帧决定").click());
  await render("new-project", onDecision);
  await act(async () => oldMutation.resolve(empty(1)));
  expect(onDecision).toHaveBeenCalledTimes(2);
  expect(onDecision).toHaveBeenLastCalledWith(empty(2));
  expect(host.textContent).toContain("当前已保存：不使用末帧画面 · 第 2 版");
  expect(button("保存当前镜头末帧决定").disabled).toBe(false);
});

it("marks an unsaved image draft and blocks save while a refresh is pending", async () => {
  const asset: ManagedAsset = {
    id: "end-image", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
    mimeType: "image/png", byteSize: 1, width: 576, height: 1024,
    createdAt: "2026-09-25T00:00:00Z", provenance: null,
  };
  const refresh = pending<VideoEndFrameDecision>();
  vi.spyOn(plotloomApi, "getVideoEndFrame")
    .mockResolvedValueOnce(empty()).mockReturnValueOnce(refresh.promise);
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [asset] });
  const onDraftChange = vi.fn();
  await act(async () => root.render(createElement(VideoEndFrameChoice, {
    projectId: "project", shotId: "same-shot", approvalId: "approval", storyboardRevision: 1,
    requestAspectPolicy: "reject_mismatch", readOnly: false, onDecision: vi.fn(), onDraftChange, onReadinessChange: vi.fn(),
  })));
  const select = host.querySelector(".video-end-frame-choice select") as HTMLSelectElement;
  await act(async () => { select.value = asset.id; select.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(onDraftChange).toHaveBeenLastCalledWith(true);
  expect(host.querySelector(".video-end-frame-choice > header")?.textContent).toContain("不保证生成画面精确重合");
  expect(host.querySelector(".video-end-frame-preview img")?.getAttribute("alt")).toBe("待选末帧画面");
  expect(host.querySelector(".video-end-frame-technical code")?.textContent).toContain(asset.originalHash);
  await act(async () => button("刷新末帧与图片列表").click());
  expect(button("保存当前镜头末帧决定").disabled).toBe(true);
  await act(async () => refresh.resolve(empty()));
  expect(onDraftChange).toHaveBeenLastCalledWith(false);
  expect(select.value).toBe("");
  expect(button("保存当前镜头末帧决定").disabled).toBe(false);
});

it.each(["decision", "catalog"])("does not claim a saved empty choice while the %s read is pending", async (operation) => {
  const next = pending<never>();
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockReturnValue(operation === "decision" ? next.promise : Promise.resolve(empty()));
  vi.spyOn(plotloomApi, "getManagedAssets").mockReturnValue(operation === "catalog" ? next.promise : Promise.resolve({ assets: [] }));
  await render("project", vi.fn());
  expect(host.textContent).toContain("正在读取末帧设置与图片列表");
  expect(host.textContent).not.toContain("当前已保存");
  expect(host.textContent).not.toContain("当前设置：不使用末帧画面");
  expect(onReadinessChange).toHaveBeenLastCalledWith(false);
  expect(button("保存当前镜头末帧决定").disabled).toBe(true);
});

it.each(["decision", "catalog"])("retains a truthful unverified state when the initial %s read fails", async (operation) => {
  const failure = new ApiError("server evidence", 503, { reason: "read_busy" });
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockImplementation(() => operation === "decision" ? Promise.reject(failure) : Promise.resolve(empty()));
  vi.spyOn(plotloomApi, "getManagedAssets").mockImplementation(() => operation === "catalog" ? Promise.reject(failure) : Promise.resolve({ assets: [] }));
  await render("project", vi.fn());
  expect(host.querySelector('[role="alert"]')?.textContent).toContain("无法读取末帧设置与图片列表");
  expect(host.querySelector("pre")?.textContent).toContain('HTTP 503\n{\n  "reason": "read_busy"');
  expect(host.textContent).not.toContain("当前已保存");
  expect(onReadinessChange).toHaveBeenLastCalledWith(false);
  expect(button("保存当前镜头末帧决定").disabled).toBe(true);
});

it("distinguishes the revision-zero default from an explicitly saved empty setting", async () => {
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValueOnce(empty()).mockResolvedValueOnce(empty(4));
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  await render("project", vi.fn());
  expect(host.textContent).toContain("当前设置：不使用末帧画面");
  expect(host.textContent).not.toContain("当前已保存");
  await act(async () => button("刷新末帧与图片列表").click());
  expect(host.textContent).toContain("当前已保存：不使用末帧画面 · 第 4 版");
});

it("retains the known image and unsaved draft when a refresh fails, without authorizing a save", async () => {
  const asset: ManagedAsset = { id: "draft-frame", projectId: "project", originalHash: "a".repeat(64), displayHash: "b".repeat(64), mimeType: "image/png", byteSize: 1, width: 832, height: 480, createdAt: "2026-10-08T00:00:00Z", provenance: null };
  const refresh = pending<VideoEndFrameDecision>();
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValueOnce(empty(2)).mockReturnValueOnce(refresh.promise).mockResolvedValueOnce(empty(2));
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [asset] });
  const choose = vi.spyOn(plotloomApi, "chooseVideoEndFrame");
  const onDraftChange = vi.fn();
  await render("project", vi.fn(), { onDraftChange });
  const select = host.querySelector("select")!;
  await act(async () => { select.value = asset.id; select.dispatchEvent(new Event("change", { bubbles: true })); });
  await act(async () => button("刷新末帧与图片列表").click());
  expect(onReadinessChange).toHaveBeenLastCalledWith(false);
  await act(async () => refresh.reject(new Error("Failed to fetch")));
  expect(select.value).toBe(asset.id);
  expect(select.disabled).toBe(true);
  expect(host.textContent).toContain("上次核实：当前已保存：不使用末帧画面 · 第 2 版");
  expect(host.textContent).toContain("当前末帧设置尚未核实");
  expect(onDraftChange).toHaveBeenLastCalledWith(true);
  await act(async () => button("保存当前镜头末帧决定").click());
  expect(choose).not.toHaveBeenCalled();
  await act(async () => button("刷新末帧与图片列表").click());
  expect(select.value).toBe("");
  expect(onReadinessChange).toHaveBeenLastCalledWith(true);
  expect(onDraftChange).toHaveBeenLastCalledWith(false);
});

it("withdraws readiness during saving and requires a reread after an unknown save outcome", async () => {
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockResolvedValueOnce(empty()).mockResolvedValueOnce(empty(1));
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  const mutation = pending<VideoEndFrameDecision>();
  const choose = vi.spyOn(plotloomApi, "chooseVideoEndFrame").mockReturnValue(mutation.promise);
  await render("project", vi.fn());
  await act(async () => button("保存当前镜头末帧决定").click());
  expect(host.textContent).toContain("正在保存末帧设置");
  expect(onReadinessChange).toHaveBeenLastCalledWith(false);
  await act(async () => mutation.reject(new Error("connection lost")));
  expect(host.textContent).toContain("设置可能已经保存；请重新读取核实，不要重复保存");
  expect(button("保存当前镜头末帧决定").disabled).toBe(true);
  await act(async () => button("刷新末帧与图片列表").click());
  expect(onReadinessChange).toHaveBeenLastCalledWith(true);
  expect(host.textContent).toContain("当前已保存：不使用末帧画面 · 第 1 版");
  expect(choose).toHaveBeenCalledTimes(1);
});

it.each([{ approvalId: "new-approval" }, { storyboardRevision: 2 }])("ignores late same-shot reads and errors after ownership changes to %j", async (overrides) => {
  const old = pending<VideoEndFrameDecision>();
  const next = pending<VideoEndFrameDecision>();
  vi.spyOn(plotloomApi, "getVideoEndFrame").mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
  vi.spyOn(plotloomApi, "getManagedAssets").mockResolvedValue({ assets: [] });
  const onDecision = vi.fn();
  await render("project", onDecision);
  await render("project", onDecision, overrides);
  await act(async () => old.reject(new Error("late old error")));
  expect(host.textContent).not.toContain("late old error");
  expect(onReadinessChange).toHaveBeenLastCalledWith(false);
  await act(async () => next.resolve(empty()));
  expect(onDecision).toHaveBeenCalledTimes(1);
  expect(onReadinessChange).toHaveBeenLastCalledWith(true);
});
