import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { ImageTerminalSettlement } from "../src/features/specialists/ImageTerminalSettlement";
import { specialistsApi } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const proof = { markerHash: "a".repeat(64), marker: { jobId: "ij_test", taskId: "worker", requestHash: "b".repeat(64), reason: "Conflicting request; no generation." } };
const button = (host: HTMLElement, text: string) => [...host.querySelectorAll("button")].find(value => value.textContent === text)!;
async function fill(input: HTMLInputElement, value: string) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

it("requires validated marker and explicit native-final review, then settles once without send", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const read = vi.spyOn(specialistsApi, "imageTerminalPreview").mockResolvedValue(proof);
  const settle = vi.spyOn(specialistsApi, "settleImageTerminal").mockResolvedValue({ state: "completed" });
  const send = vi.spyOn(specialistsApi, "sendImage"); const finished = vi.fn().mockResolvedValue(undefined);
  try {
    await act(async () => root.render(createElement(ImageTerminalSettlement, { jobId: "ij_test", onSettled: finished })));
    expect(settle).not.toHaveBeenCalled();
    await fill(host.querySelector("input")!, "project");
    await act(async () => button(host, "读取并验证终止声明").click());
    expect(read).toHaveBeenCalledWith("project", "image_job", "ij_test");
    const action = button(host, "记录生成前阻塞并释放此任务预约");
    expect(action.disabled).toBe(true);
    const inputs = [...host.querySelectorAll<HTMLInputElement>("input")];
    await fill(inputs[1], "terminal-turn"); await fill(inputs[2], "58"); await fill(inputs[3], "reviewer");
    expect(action.disabled).toBe(true);
    await act(async () => inputs[4].click());
    await act(async () => { action.click(); action.click(); });
    expect(settle).toHaveBeenCalledTimes(1);
    expect(settle).toHaveBeenCalledWith("project", "image_job", "ij_test", {
      markerHash: proof.markerHash, taskId: "worker", terminalTurnId: "terminal-turn", terminalRevision: 58,
      reviewer: "reviewer", observedIdle: true, reviewedBlockedVerdict: true,
    });
    expect(finished).toHaveBeenCalledTimes(1); expect(send).not.toHaveBeenCalled();
    expect(host.textContent).toContain("未发布任何图片候选");
  } finally { await act(async () => root.unmount()); }
});

it("invalidates proof when project changes and preserves reservation on invalid proof", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(specialistsApi, "imageTerminalPreview").mockResolvedValueOnce(proof).mockRejectedValueOnce(new Error("缺少终止证明；保留预约。"));
  const settle = vi.spyOn(specialistsApi, "settleImageTerminal");
  try {
    await act(async () => root.render(createElement(ImageTerminalSettlement, { jobId: "ij_test", onSettled: vi.fn() })));
    await fill(host.querySelector("input")!, "old");
    await act(async () => button(host, "读取并验证终止声明").click());
    expect(host.textContent).toContain(proof.markerHash);
    await fill(host.querySelector("input")!, "new");
    expect(host.textContent).not.toContain(proof.markerHash);
    await act(async () => button(host, "读取并验证终止声明").click());
    expect(host.textContent).toContain("保留预约"); expect(settle).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});
