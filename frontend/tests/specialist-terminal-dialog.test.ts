import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SpecialistSettingsDialog } from "../src/features/specialists/SpecialistSettingsDialog";
import { specialistsApi, type SpecialistSettings } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const settings: SpecialistSettings = { text: { name: "文字助手", taskId: null }, image: { name: "图片助手", taskId: null }, busy: true,
  activeTasks: [{ jobId: "ij_test" }, { jobId: "text_test", projectId: "p", stage: "outline" }] };
const proof = { markerHash: "a".repeat(64), marker: { jobId: "ij_test", taskId: "worker", requestHash: "b".repeat(64), reason: "Synthetic blocked-before-generation fixture." } };
let host: HTMLDivElement, root: Root;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
const button = (label: string) => [...host.querySelectorAll("button")].find(item => item.textContent === label)!;
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function fill(input: HTMLInputElement, value: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function prepare(close: () => void) {
  vi.spyOn(specialistsApi, "imageTerminalPreview").mockResolvedValue(proof);
  await act(async () => root.render(createElement(SpecialistSettingsDialog, { onClose: close })));
  await fill(host.querySelector("details input")!, "synthetic-project");
  await act(async () => button("读取并验证终止声明").click());
  const inputs = [...host.querySelectorAll<HTMLInputElement>("details input")];
  await fill(inputs[1], "synthetic-turn"); await fill(inputs[2], "58"); await fill(inputs[3], "test reviewer");
  await act(async () => inputs[4].click());
}
function expectLocked(locked: boolean) {
  expect(button("关闭").disabled).toBe(locked);
  expect(host.querySelector<HTMLButtonElement>(".modal-backdrop")!.disabled).toBe(locked);
  expect(button("检查此任务的结果").disabled).toBe(locked);
}

it("owns a nested settlement until refresh finishes, then unlocks without dispatch", async () => {
  const refresh = deferred<SpecialistSettings>(), settlement = deferred<{ state: string }>();
  vi.spyOn(specialistsApi, "settings").mockResolvedValueOnce(settings).mockReturnValueOnce(refresh.promise);
  const settle = vi.spyOn(specialistsApi, "settleImageTerminal").mockReturnValue(settlement.promise);
  const send = vi.spyOn(specialistsApi, "sendImage"), check = vi.spyOn(specialistsApi, "check"), close = vi.fn();
  await prepare(close);
  await act(async () => button("记录生成前阻塞并释放此任务预约").click());
  expectLocked(true);
  await act(async () => { button("关闭").click(); host.querySelector<HTMLButtonElement>(".modal-backdrop")!.click(); button("检查此任务的结果").click(); });
  expect(close).not.toHaveBeenCalled(); expect(check).not.toHaveBeenCalled();
  await act(async () => settlement.resolve({ state: "completed" }));
  expectLocked(true);
  await act(async () => refresh.resolve(settings));
  expectLocked(false);
  expect(host.textContent).toContain("仅此任务预约已释放");
  expect(settle).toHaveBeenCalledOnce(); expect(send).not.toHaveBeenCalled();
});

it.each(["settlement", "refresh"])("unlocks after %s failure and retains the precise outcome", async failure => {
  const settlement = deferred<{ state: string }>(), refresh = deferred<SpecialistSettings>();
  vi.spyOn(specialistsApi, "settings").mockResolvedValueOnce(settings).mockReturnValueOnce(refresh.promise);
  const settle = vi.spyOn(specialistsApi, "settleImageTerminal").mockReturnValue(settlement.promise);
  await prepare(vi.fn());
  await act(async () => button("记录生成前阻塞并释放此任务预约").click());
  expectLocked(true);
  if (failure === "settlement") await act(async () => settlement.reject(new Error("测试终止审核失败；预约保留。")));
  else {
    await act(async () => settlement.resolve({ state: "completed" }));
    expectLocked(true);
    await act(async () => refresh.reject(new Error("测试设置刷新失败。")));
  }
  expectLocked(false);
  expect(host.textContent).toContain(failure === "settlement" ? "测试终止审核失败；预约保留。" : "测试设置刷新失败。");
  expect(host.textContent?.includes("仅此任务预约已释放")).toBe(failure === "refresh");
  expect(host.querySelector<HTMLInputElement>("details input")!.value).toBe("synthetic-project");
  expect(settle).toHaveBeenCalledOnce();
});
