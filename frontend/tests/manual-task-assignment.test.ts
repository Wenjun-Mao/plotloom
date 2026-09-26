import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ManualTaskAssignment } from "../src/pages/ManualTaskAssignment";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const assignment = "请执行任务。\n不要自动确认内容。";

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

async function render(task = assignment) { await act(async () => root.render(createElement(ManualTaskAssignment, { assignment: task, taskName: "剧本" }))); }
async function copy() { await act(async () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "复制完整任务")!.click()); }

it("reports copying success only after the displayed task is written", async () => {
  let finish!: () => void;
  const writeText = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  await render(); await copy();
  expect(writeText).toHaveBeenCalledWith(assignment);
  expect(host.textContent).not.toContain("已复制完整任务");
  await act(async () => finish());
  expect(host.textContent).toContain("已复制完整任务");
});

it("retains selectable task text when clipboard copying fails", async () => {
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
  await render(); await copy();
  expect(host.textContent).toContain("复制失败");
  const text = host.querySelector("textarea")!;
  await act(async () => text.focus());
  expect(text.selectionEnd - text.selectionStart).toBe(assignment.length);
});

it("does not mark a replacement assignment copied after an earlier clipboard write settles", async () => {
  let finish!: () => void;
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn(() => new Promise<void>((resolve) => { finish = resolve; })) } });
  await render("Task A"); await copy();
  await render("Task B");
  await act(async () => finish());
  expect(host.querySelector("textarea")?.value).toBe("Task B");
  expect(host.textContent).not.toContain("已复制完整任务");
});
