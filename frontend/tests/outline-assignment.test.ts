import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { OutlineAssignment } from "../src/pages/OutlineAssignment";
import type { OutlineCandidatePreparation } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const task = "请执行大纲任务。\n/path with spaces/request.json\n不要替我接受大纲。";
const result = { assignment: task } as OutlineCandidatePreparation;
const render = async () => { await act(async () => root.render(createElement(OutlineAssignment, { projectId: "p", jobId: "j" }))); };
const click = async (label: string) => { await act(async () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent === label)!.click()); };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("copies the complete displayed assignment and only reports success after the write", async () => {
  vi.spyOn(plotloomApi, "getOutlineAssignment").mockResolvedValue(result);
  let finish!: () => void;
  const writeText = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  await render();
  await click("复制完整任务");
  expect(writeText).toHaveBeenCalledWith(host.querySelector("textarea")!.value);
  expect(writeText).toHaveBeenCalledWith(task);
  expect(host.textContent).not.toContain("已复制完整任务");
  await act(async () => finish());
  expect(host.textContent).toContain("已复制完整任务");
});

it("leaves selectable task text when clipboard permission fails", async () => {
  vi.spyOn(plotloomApi, "getOutlineAssignment").mockResolvedValue(result);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
  await render(); await click("复制完整任务");
  expect(host.textContent).toContain("复制失败");
  expect(host.textContent).not.toContain("已复制完整任务");
  const text = host.querySelector("textarea")!;
  await act(async () => text.focus());
  expect(text.selectionEnd - text.selectionStart).toBe(task.length);
});

it("can retry a failed read without preparing another job", async () => {
  const get = vi.spyOn(plotloomApi, "getOutlineAssignment").mockRejectedValueOnce(new Error("offline")).mockResolvedValue(result);
  const prepare = vi.spyOn(plotloomApi, "prepareOutlineCandidate");
  await render();
  expect(host.textContent).toContain("无法读取完整任务");
  await click("重试读取任务");
  expect(host.querySelector("textarea")!.value).toBe(task);
  expect(get).toHaveBeenCalledTimes(2);
  expect(prepare).not.toHaveBeenCalled();
});
