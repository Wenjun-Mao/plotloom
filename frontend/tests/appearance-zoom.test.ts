import { act, createElement, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AssetZoomDialog, ManagedAssetImage } from "../src/features/media/references/AppearanceReviewPrimitives";

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
