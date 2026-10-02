import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { useConfirmation } from "../src/confirmation";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const operation = vi.fn<() => void | Promise<void>>();
const descriptors = ["showModal", "close"].map(name => Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name));
function Harness({ identity = "job:revision1", disabled = false }: { identity?: string; disabled?: boolean }) {
  const { requestConfirmation, confirmation } = useConfirmation(identity, disabled);
  return createElement("div", null,
    createElement("button", { onClick: () => requestConfirmation({ title: "拒绝原片", message: "保留证据并撤销选择", details: identity, action: operation }) }, "request"), confirmation);
}
async function render(identity = "job:revision1", disabled = false) {
  await act(async () => root.render(createElement(Harness, { identity, disabled })));
}
async function open() {
  const trigger = host.querySelector<HTMLButtonElement>("button")!;
  trigger.focus(); await act(async () => trigger.click()); return trigger;
}
const dialog = () => document.querySelector<HTMLDialogElement>("dialog")!;
const confirmButton = () => dialog().querySelectorAll<HTMLButtonElement>("button")[1];
beforeEach(() => {
  operation.mockReset(); host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
afterEach(async () => {
  await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  ["showModal", "close"].forEach((name, index) => { if (descriptors[index]) Object.defineProperty(HTMLDialogElement.prototype, name, descriptors[index]!); else Reflect.deleteProperty(HTMLDialogElement.prototype, name); });
});
it("requires DOM confirmation, defaults focus to cancel, cancels without writes and restores focus", async () => {
  await render(); const trigger = await open();
  expect(dialog().getAttribute("role")).toBe("alertdialog"); expect(dialog().getAttribute("aria-describedby")).toBeTruthy();
  expect(document.activeElement?.textContent).toBe("取消"); expect(operation).not.toHaveBeenCalled();
  await act(async () => dialog().querySelector<HTMLButtonElement>("button")!.click());
  expect(operation).not.toHaveBeenCalled(); expect(dialog()).toBeNull(); expect(document.activeElement).toBe(trigger);
  await open(); await act(async () => dialog().dispatchEvent(new Event("cancel", { cancelable: true })));
  expect(dialog()).toBeNull(); expect(operation).not.toHaveBeenCalled();
});
it("dispatches once despite double confirmation, blocks cancellation while busy and recovers", async () => {
  let finish!: () => void; operation.mockImplementation(() => new Promise<void>(done => { finish = done; }));
  await render(); await open(); const button = confirmButton();
  await act(async () => { button.click(); button.click(); });
  expect(operation).toHaveBeenCalledOnce(); expect(confirmButton().disabled).toBe(true);
  await act(async () => dialog().dispatchEvent(new Event("cancel", { cancelable: true })));
  expect(dialog()).not.toBeNull();
  await act(async () => { finish(); }); expect(dialog()).toBeNull();
  operation.mockImplementation(() => undefined); await open(); await act(async () => confirmButton().click()); expect(operation).toHaveBeenCalledTimes(2);
});
it.each(["job:revision2", "different-project:job", "different-job"])("invalidates frozen consent when identity changes to %s", async identity => {
  await render(); await open(); const stale = confirmButton(); await render(identity);
  await act(async () => stale.click()); expect(operation).not.toHaveBeenCalled(); expect(dialog()).toBeNull();
  await open(); expect(dialog().textContent).toContain(identity);
});
it("invalidates read-only consent and does not replay after remount/reload", async () => {
  await render(); await open(); await render("job:revision1", true); expect(dialog()).toBeNull();
  await render(); expect(dialog()).toBeNull(); await open();
  await act(async () => root.unmount()); root = createRoot(host); await render();
  expect(dialog()).toBeNull(); expect(operation).not.toHaveBeenCalled();
});
it("shows failure without automatic retry and requires explicit reconfirmation", async () => {
  operation.mockRejectedValueOnce(new Error("stale server state")); await render(); await open();
  await act(async () => confirmButton().click()); expect(dialog().textContent).toContain("stale server state"); expect(operation).toHaveBeenCalledOnce();
  await act(async () => dialog().querySelector<HTMLButtonElement>("button")!.click());
  operation.mockImplementation(() => undefined); await open(); await act(async () => confirmButton().click()); expect(operation).toHaveBeenCalledTimes(2);
});
it("keeps browser-native confirmation out of creator source", () => {
  function scan(directory: string): string[] {
    return readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? scan(resolve(directory, entry.name)) : /\.tsx?$/.test(entry.name) ? [resolve(directory, entry.name)] : []);
  }
  for (const path of scan(resolve("src"))) expect(readFileSync(path, "utf8"), path).not.toMatch(/\b(?:window\.)?confirm\s*\(/);
});
