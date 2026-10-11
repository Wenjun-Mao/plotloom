import { act, createElement, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AssetZoomDialog, ManagedAssetImage } from "../src/features/media/references/AppearanceReviewPrimitives";
import { ManagedAssetViewer } from "../src/features/media/references/ManagedAssetViewer";
import { CandidateCard } from "../src/features/media/assets/MediaCandidates";
import type { ManagedAsset } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
const descriptors = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));

beforeEach(() => {
  // jsdom does not implement the native top layer; browser checks cover it.
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: { configurable: true, value() { this.setAttribute("open", ""); } },
    close: { configurable: true, value() { this.removeAttribute("open"); } },
  });
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => {
  await act(async () => root.unmount()); host.remove(); document.body.style.overflow = "";
  ["showModal", "close"].forEach((name, index) => {
    if (descriptors[index]) Object.defineProperty(HTMLDialogElement.prototype, name, descriptors[index]!);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  });
});

function Harness() {
  const [open, setOpen] = useState(false);
  return createElement("div", null,
    createElement(ManagedAssetImage, { projectId: "p", subjectId: "c", assetId: "a", asset: { id: "a" } as never, alt: "当前查看图片", unavailableLabel: "图片不可用", onZoom: () => setOpen(true) }),
    createElement(AssetZoomDialog, { open, onClose: () => setOpen(false), label: "放大查看图片", children: createElement("img", { alt: "放大图片" }) }),
  );
}
async function open() {
  await act(async () => root.render(createElement(Harness)));
  const trigger = host.querySelector("button")!;
  trigger.focus();
  await act(async () => trigger.querySelector("img")!.click());
  return trigger;
}

it("opens from the image, preserves inside clicks, closes on backdrop and restores focus/scroll", async () => {
  document.body.style.overflow = "auto";
  const trigger = await open();
  const dialog = document.querySelector("dialog")!;
  expect(dialog.open).toBe(true);
  expect(host.contains(dialog)).toBe(false);
  expect(document.body.style.overflow).toBe("hidden");
  await act(async () => dialog.querySelector("img")!.click());
  expect(document.querySelector("dialog")).toBe(dialog);
  await act(async () => dialog.click());
  expect(document.querySelector("dialog")).toBeNull();
  expect(document.body.style.overflow).toBe("auto");
  expect(document.activeElement).toBe(trigger);
});

it.each(["cancel", "close button"])("dismisses with %s without changing the preview", async method => {
  const trigger = await open();
  const dialog = document.querySelector("dialog")!;
  await act(async () => {
    if (method === "cancel") dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
    else dialog.querySelector("button")!.click();
  });
  expect(document.querySelector("dialog")).toBeNull();
  expect(host.querySelector("button")).toBe(trigger);
});

it("leaves thumbnails non-interactive and does not offer zoom for unavailable images", async () => {
  const zoom = vi.fn();
  const props = { projectId: "p", subjectId: "c", assetId: "a", asset: { id: "a" } as never, alt: "图片", unavailableLabel: "图片不可用" };
  await act(async () => root.render(createElement(ManagedAssetImage, props)));
  expect(host.querySelector("button")).toBeNull();
  await act(async () => root.render(createElement(ManagedAssetImage, { ...props, onZoom: zoom })));
  await act(async () => host.querySelector("img")!.dispatchEvent(new Event("error")));
  expect(host.querySelector("button")).toBeNull();
  expect(host.textContent).toContain("图片不可用");
  expect(zoom).not.toHaveBeenCalled();
});

it("releases scroll locking when the owning gallery unmounts", async () => {
  await open();
  await act(async () => root.render(null));
  expect(document.querySelector("dialog")).toBeNull();
  expect(document.body.style.overflow).toBe("");
});

const asset: ManagedAsset = {
  id: "portrait", projectId: "p", originalHash: "a".repeat(64), displayHash: "b".repeat(64),
  mimeType: "image/png", byteSize: 1024, width: 941, height: 1672, createdAt: "2026-10-11T00:00:00Z",
  provenance: { origin: "manual", rights: "unknown", rightsNote: null, declaredAdditions: [] },
};

it("keeps candidate zoom separate from comparison and keyframe retention", async () => {
  const onPick = vi.fn(); const onKeep = vi.fn();
  await act(async () => root.render(createElement(CandidateCard, {
    asset, projectId: "p", shotId: "shot", selected: false, kept: false, onPick, onKeep,
  })));
  const trigger = host.querySelector<HTMLButtonElement>('[data-testid="view-asset-portrait"]')!;
  expect(trigger.parentElement?.tagName).toBe("ARTICLE");
  trigger.focus(); await act(async () => trigger.click());
  const dialog = document.querySelector("dialog")!;
  expect(dialog.querySelector("img")?.getAttribute("src")).toBe(host.querySelector("img")?.getAttribute("src"));
  expect(dialog.textContent).toContain("941×1672");
  expect(dialog.textContent).toContain("仅查看，不改变候选、关键帧或审核决定");
  expect(onPick).not.toHaveBeenCalled(); expect(onKeep).not.toHaveBeenCalled();
  await act(async () => dialog.dispatchEvent(new Event("cancel", { cancelable: true })));
  expect(document.activeElement).toBe(trigger);
  expect(host.querySelector('[aria-pressed="true"]')).toBeNull();
});

it.each(["project", "shot", "asset", "bytes"])("closes rather than reopens the viewer after %s evidence changes", async change => {
  const initial = { projectId: "p", subjectId: "shot", asset, alt: "证据" };
  await act(async () => root.render(createElement(ManagedAssetViewer, initial)));
  await act(async () => host.querySelector<HTMLButtonElement>("button")!.click());
  expect(document.querySelector("dialog")).not.toBeNull();
  const changed = {
    ...initial,
    ...(change === "project" ? { projectId: "q" } : {}),
    ...(change === "shot" ? { subjectId: "other-shot" } : {}),
    ...(change === "asset" ? { asset: { ...asset, id: "other" } } : {}),
    ...(change === "bytes" ? { asset: { ...asset, displayHash: "c".repeat(64) } } : {}),
  };
  await act(async () => root.render(createElement(ManagedAssetViewer, changed)));
  expect(document.querySelector("dialog")).toBeNull();
  expect(document.body.style.overflow).toBe("");
  await act(async () => root.render(createElement(ManagedAssetViewer, initial)));
  expect(document.querySelector("dialog")).toBeNull();
});

it("shows full-image read failures without implying selection or approval", async () => {
  await act(async () => root.render(createElement(ManagedAssetViewer, { projectId: "p", subjectId: "s", asset, alt: "证据" })));
  await act(async () => host.querySelector<HTMLButtonElement>("button")!.click());
  await act(async () => document.querySelector("dialog img")!.dispatchEvent(new Event("error")));
  expect(document.querySelector("dialog")?.textContent).toContain("无法读取完整图片");
  expect(document.querySelector("dialog")?.textContent).toContain("HTTP 读取失败或无法解码");
});
