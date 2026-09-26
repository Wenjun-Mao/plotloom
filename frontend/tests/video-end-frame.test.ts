import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import type { VideoEndFrameDecision } from "../src/api";
import { VideoEndFrameChoice } from "../src/video-end-frame";
import type { ManagedAsset } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLDivElement;
let root: Root;
const pending = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const empty = (revision = 0): VideoEndFrameDecision => ({ revision, assetId: null });
const button = (text: string) => Array.from(host.querySelectorAll("button"))
  .find((item) => item.textContent === text) as HTMLButtonElement;
const render = async (projectId: string, onDecision: (decision: VideoEndFrameDecision) => void) => {
  await act(async () => root.render(createElement(VideoEndFrameChoice, {
    projectId, shotId: "same-shot", approvalId: "approval", storyboardRevision: 1,
    requestAspectPolicy: "reject_mismatch", readOnly: false, onDecision,
  })));
};

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
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
  expect(host.textContent).toContain("当前已保存：无末帧");
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
  expect(host.textContent).toContain("当前已保存：无末帧");
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
    requestAspectPolicy: "reject_mismatch", readOnly: false, onDecision: vi.fn(), onDraftChange,
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
