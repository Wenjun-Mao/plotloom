import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SpecialistSettingsDialog } from "../src/features/specialists/SpecialistSettingsDialog";
import { specialistsApi, type SpecialistSettings } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const settings: SpecialistSettings = { text: { name: "文字助手", taskId: null }, image: { name: "图片助手", taskId: null }, busy: false };
let host: HTMLDivElement, root: Root;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
const button = (label: string) => [...host.querySelectorAll("button")].find(item => item.textContent === label)!;
const render = (onClose = vi.fn()) => act(async () => root.render(createElement(SpecialistSettingsDialog, { onClose })));

it("distinguishes loading, failed read and explicit read-only retry", async () => {
  let reject!: (reason: Error) => void;
  const read = vi.spyOn(specialistsApi, "settings").mockReturnValueOnce(new Promise((_, fail) => { reject = fail; })).mockResolvedValue(settings);
  const save = vi.spyOn(specialistsApi, "save");
  const check = vi.spyOn(specialistsApi, "check");
  await render();
  expect(host.textContent).toContain("正在读取助手设置…");
  expect(button("保存助手设置").disabled).toBe(true);
  expect(button("关闭").disabled).toBe(false);
  await act(async () => reject(new Error("设置暂时不可用。")));
  expect(host.textContent).not.toContain("正在读取助手设置…");
  expect(host.textContent).toContain("设置暂时不可用。");
  expect(host.textContent).not.toContain("Error:");
  await act(async () => button("重试读取助手设置").click());
  expect(read).toHaveBeenCalledTimes(2);
  expect(host.querySelectorAll("input")).toHaveLength(4);
  expect(button("保存助手设置").disabled).toBe(false);
  expect(host.textContent).not.toContain("设置暂时不可用。");
  expect(save).not.toHaveBeenCalled(); expect(check).not.toHaveBeenCalled();
});

it("names a held save and preserves editable input after failure", async () => {
  vi.spyOn(specialistsApi, "settings").mockResolvedValue(settings);
  let reject!: (reason: Error) => void;
  const save = vi.spyOn(specialistsApi, "save").mockReturnValue(new Promise((_, fail) => { reject = fail; }));
  const close = vi.fn();
  await render(close);
  const input = host.querySelector("input")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "保留名称");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => button("保存助手设置").click());
  expect(button("正在保存…").disabled).toBe(true);
  expect(host.querySelector("fieldset")!.disabled).toBe(true);
  expect(button("关闭").disabled).toBe(true);
  const backdrop = host.querySelector<HTMLButtonElement>(".modal-backdrop")!;
  expect(backdrop.disabled).toBe(true);
  await act(async () => { button("关闭").click(); backdrop.click(); });
  expect(close).not.toHaveBeenCalled();
  await act(async () => reject(new Error("保存暂时不可用。")));
  expect(input.value).toBe("保留名称");
  expect(host.querySelector("fieldset")!.disabled).toBe(false);
  expect(button("保存助手设置").disabled).toBe(false);
  expect(button("关闭").disabled).toBe(false);
  expect(backdrop.disabled).toBe(false);
  expect(host.textContent).not.toContain("设置已保存");
  expect(save).toHaveBeenCalledTimes(1);
  await act(async () => button("关闭").click());
  expect(close).toHaveBeenCalledOnce();
});

it("keeps server-busy bindings locked after a successful read", async () => {
  vi.spyOn(specialistsApi, "settings").mockResolvedValue({ ...settings, busy: true });
  await render();
  expect(host.textContent).toContain("助手还有未完成的任务");
  expect(host.textContent).not.toContain("正在读取助手设置");
  expect(button("保存助手设置").disabled).toBe(true);
  expect(host.querySelector("fieldset")!.disabled).toBe(true);
  expect(button("关闭").disabled).toBe(false);
});

it("labels an explicit held task check without saving or sending", async () => {
  const read = vi.spyOn(specialistsApi, "settings")
    .mockResolvedValueOnce({ ...settings, busy: true, activeTasks: [{ projectId: "p", stage: "outline", jobId: "j" }] })
    .mockResolvedValue(settings);
  let finish!: (value: { state: "completed" }) => void;
  const check = vi.spyOn(specialistsApi, "check").mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const save = vi.spyOn(specialistsApi, "save"), send = vi.spyOn(specialistsApi, "send");
  await render();
  await act(async () => button("检查此任务的结果").click());
  expect(host.textContent).toContain("正在检查任务结果…");
  expect(button("检查此任务的结果").disabled).toBe(true);
  expect(button("保存助手设置").disabled).toBe(true);
  expect(button("关闭").disabled).toBe(true);
  expect(host.querySelector<HTMLButtonElement>(".modal-backdrop")!.disabled).toBe(true);
  await act(async () => finish({ state: "completed" }));
  expect(check).toHaveBeenCalledExactlyOnceWith("p", "outline", "j");
  expect(read).toHaveBeenCalledTimes(2);
  expect(host.textContent).not.toContain("正在检查任务结果…");
  expect(button("保存助手设置").disabled).toBe(false);
  expect(button("关闭").disabled).toBe(false);
  expect(save).not.toHaveBeenCalled(); expect(send).not.toHaveBeenCalled();
});
