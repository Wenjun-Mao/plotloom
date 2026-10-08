import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ReviewedVideoPlayer } from "../src/features/media/ReviewedVideoPlayer";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
const props = { src: "/media/original-a", testId: "original-a", kind: "原片" as const, style: { aspectRatio: "832 / 480", objectFit: "contain" as const } };

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
async function render(src = props.src) { await act(async () => root.render(createElement(ReviewedVideoPlayer, { ...props, src }))); }
async function fail(video: HTMLVideoElement) {
  Object.defineProperty(video, "error", { configurable: true, value: { code: 3, message: "PIPELINE_ERROR_DISCONNECTED" } });
  await act(async () => video.dispatchEvent(new Event("error")));
}

it("exposes a readable error with exact secondary evidence and reloads only this media", async () => {
  await render();
  const video = host.querySelector("video")!;
  const load = vi.spyOn(video, "load").mockImplementation(() => {});
  const play = vi.spyOn(video, "play").mockResolvedValue();
  const request = vi.spyOn(globalThis, "fetch");
  expect(video.controls).toBe(true);
  expect(video.style.aspectRatio).toBe("832 / 480");
  expect(video.getAttribute("aria-label")).toBe("原片预览");
  await fail(video);
  const alert = host.querySelector('[role="alert"]')!;
  expect(alert.textContent).toContain("浏览器未能播放这份原片");
  expect(alert.textContent).toContain("不会重新生成、改变选用结果或自动播放");
  expect(alert.textContent).toContain("媒体错误代码：3");
  expect(alert.querySelector("pre")?.textContent).toBe("PIPELINE_ERROR_DISCONNECTED");
  await act(async () => host.querySelector<HTMLButtonElement>("button")!.click());
  expect(load).toHaveBeenCalledOnce();
  expect(play).not.toHaveBeenCalled();
  expect(request).not.toHaveBeenCalled();
  expect(video.getAttribute("src")).toBe(props.src);
  expect(host.querySelector('[role="alert"]')).toBeNull();
});

it("contains an old source failure after changing media and clears error after decoded data arrives", async () => {
  await render(); const oldVideo = host.querySelector("video")!; await fail(oldVideo);
  await render("/media/original-b");
  const current = host.querySelector("video")!;
  expect(current).not.toBe(oldVideo);
  expect(host.querySelector('[role="alert"]')).toBeNull();
  await fail(oldVideo);
  expect(host.querySelector('[role="alert"]')).toBeNull();
  await fail(current);
  expect(host.querySelector('[role="alert"]')).not.toBeNull();
  await act(async () => current.dispatchEvent(new Event("loadeddata")));
  expect(host.querySelector('[role="alert"]')).toBeNull();
});

it("pauses other reviewed originals and segments in either direction without touching story playback", async () => {
  await act(async () => root.render(createElement("div", {},
    createElement(ReviewedVideoPlayer, props),
    createElement(ReviewedVideoPlayer, { ...props, src: "/media/segment", testId: "segment", kind: "播放片段" }),
    createElement("video", { "data-testid": "story-player" }),
  )));
  const [original, segment, story] = [...host.querySelectorAll("video")];
  const originalPause = vi.spyOn(original, "pause").mockImplementation(() => {});
  const segmentPause = vi.spyOn(segment, "pause").mockImplementation(() => {});
  const storyPause = vi.spyOn(story, "pause").mockImplementation(() => {});
  await act(async () => segment.dispatchEvent(new Event("play")));
  expect(originalPause).toHaveBeenCalledOnce(); expect(segmentPause).not.toHaveBeenCalled();
  await act(async () => original.dispatchEvent(new Event("play")));
  expect(segmentPause).toHaveBeenCalledOnce(); expect(originalPause).toHaveBeenCalledOnce();
  expect(storyPause).not.toHaveBeenCalled();
  expect(segment.getAttribute("aria-label")).toBe("播放片段预览");
});
