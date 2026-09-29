import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { SpecialistTaskActions } from "../src/features/specialists/SpecialistTaskActions";
import { specialistsApi } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

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
    expect(host.textContent).toContain("已发送，等待结果");
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
