import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { SpecialistTaskActions } from "../src/features/specialists/SpecialistTaskActions";
import { SpecialistApiError, specialistsApi } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

it.each([true, false])("backs off transient failures and pauses integrity failures: transient=%s", async recover => {
  vi.useFakeTimers();
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "queued", configured: true });
  const send = vi.spyOn(specialistsApi, "send");
  const check = vi.spyOn(specialistsApi, "check").mockRejectedValueOnce(new SpecialistApiError("read failed", recover ? 503 : 409, recover ? undefined : "delivery_identity_mismatch")).mockResolvedValue({ state: "completed" });
  const delivered = vi.fn();
  try {
    await act(async () => root.render(createElement(SpecialistTaskActions, { projectId: "p", stage: "branches", jobId: "j", disabled: false, onDelivered: delivered })));
    await act(async () => vi.advanceTimersByTimeAsync(3000));
    expect(check).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTimeAsync(5999));
    expect(check).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTimeAsync(1));
    expect(check).toHaveBeenCalledTimes(recover ? 2 : 1);
    if (!recover) {
      expect(host.textContent).toContain("自动检查已暂停");
      await act(async () => vi.advanceTimersByTimeAsync(60_000));
      expect(check).toHaveBeenCalledTimes(1);
      await act(async () => [...host.querySelectorAll("button")].find(button => button.textContent === "立即检查")!.click());
    }
    expect(delivered).toHaveBeenCalledTimes(1);
    expect(send).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it("recovers a failed initial status read without sending or checking a delivery", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const status = vi.spyOn(specialistsApi, "status").mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ state: "prepared", configured: true });
  const send = vi.spyOn(specialistsApi, "send");
  const check = vi.spyOn(specialistsApi, "check");
  try {
    await act(async () => root.render(createElement(SpecialistTaskActions, { projectId: "p", stage: "outline", jobId: "j", disabled: false, onDelivered: vi.fn() })));
    expect(host.textContent).toContain("无法读取任务状态");
    expect(host.textContent).not.toContain("正在读取任务状态");
    await act(async () => [...host.querySelectorAll("button")].find(button => button.textContent === "重试读取任务状态")!.click());
    expect(status).toHaveBeenCalledTimes(2);
    expect(host.textContent).toContain("任务已准备，尚未发送");
    expect(send).not.toHaveBeenCalled();
    expect(check).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it("queues once, automatically checks delivery, and never creatively accepts", async () => {
  vi.useFakeTimers();
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "prepared", configured: true });
  const send = vi.spyOn(specialistsApi, "send").mockResolvedValue({ state: "queued" });
  const check = vi.spyOn(specialistsApi, "check").mockResolvedValue({ state: "completed" });
  const delivered = vi.fn();
  try {
    await act(async () => root.render(createElement(SpecialistTaskActions, { projectId: "p", stage: "characters", jobId: "j", disabled: false, onDelivered: delivered })));
    const button = [...host.querySelectorAll("button")].find(b => b.textContent === "发送给文字创作助手")!;
    await act(async () => { button.click(); button.click(); });
    expect(send).toHaveBeenCalledTimes(1);
    expect(host.textContent).toContain("已发送，等待助手返回结果");
    expect(delivered).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(check).toHaveBeenCalledTimes(1);
    expect(delivered).toHaveBeenCalledTimes(1);
    expect(host.textContent).toContain("结果已交付，请审核");
  } finally { await act(async () => root.unmount()); }
});

it("does not resend an uncertain outcome after reload", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "outcome_unknown", configured: true });
  const send = vi.spyOn(specialistsApi, "send");
  try {
    await act(async () => root.render(createElement(SpecialistTaskActions, { projectId: "p", stage: "script", jobId: "j", disabled: false, onDelivered: vi.fn() })));
    expect(host.textContent).toContain("请勿重复发送");
    expect([...host.querySelectorAll("button")].some(b => b.textContent === "发送给文字创作助手")).toBe(false);
    expect(send).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it("does not publish a held result across a project switch", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "prepared", configured: true });
  let finish!: (value: { state: "completed" }) => void;
  vi.spyOn(specialistsApi, "send").mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const delivered = vi.fn();
  const render = (projectId: string) => act(async () => root.render(createElement(SpecialistTaskActions, { projectId, stage: "outline", jobId: "j", disabled: false, onDelivered: delivered })));
  try {
    await render("old");
    await act(async () => host.querySelector("button")!.click());
    await render("new");
    await act(async () => finish({ state: "completed" }));
    expect(delivered).not.toHaveBeenCalled();
    expect(host.textContent).toContain("任务已准备，尚未发送");
  } finally { await act(async () => root.unmount()); }
});
