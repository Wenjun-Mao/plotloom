import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TextFailureCard } from "../src/features/autopilot/TextFailureCard";
import { correctionCount } from "../src/features/autopilot/CorrectionCount";
import { autopilotApi } from "../src/features/autopilot/api";
import { ApiError } from "../src/api-transport";
import { fixtureRun } from "./autopilot-fixture";
import type { TextFailure } from "../src/features/autopilot/contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, host: HTMLDivElement;
const failure: TextFailure = { runId: fixtureRun.id, runRevision: fixtureRun.revision, stage: "art", stageLabel: "美术方向",
  failedAttemptId: "11111111-1111-4111-8111-111111111111", rejectionHash: "a".repeat(64), terminalContentFailure: true,
  canRetry: true, reason: "只追加一次", automaticUsed: 2, automaticLimit: 2,
  issues: [{ code: "candidate_content_invalid", field: "$", item: "整份候选", rule: "完整来源规则", excerpt: null }],
  diagnostics: ["<script>literal candidate explanation</script>"],
  history: [{ ordinal: 0, mode: "original", state: "failed", outcome: "failure", comparison: "unknown" }] };
const execute = vi.fn(async (operation: () => Promise<unknown>) => { try { await operation(); } catch { /* uncertain ACK */ } });
async function render(id = "a", value = fixtureRun) {
  await act(async () => root.render(createElement(TextFailureCard, { projectId: id, run: value, disabled: false, execute })));
}
async function click(text: string) {
  await act(async () => Array.from(host.querySelectorAll("button")).find(button => button.textContent === text)!.click());
}
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  execute.mockClear();
  vi.spyOn(autopilotApi, "textFailure").mockResolvedValue(failure);
  vi.spyOn(autopilotApi, "current").mockResolvedValue(fixtureRun);
  vi.spyOn(autopilotApi, "retryText").mockRejectedValue(new Error("acknowledgement lost"));
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it.each(["", "-1", "1.5", "NaN", "9007199254740992"])("rejects invalid auto-count input %s", input => {
  expect(correctionCount(input)).toBeUndefined();
});
it("supports automatic off and a finite count above one", () => {
  expect(correctionCount("0")).toBe(0); expect(correctionCount("2")).toBe(2);
});
it("renders literal source diagnostics and labels whole-candidate precision honestly", async () => {
  await render(); await click("查看问题");
  expect(host.textContent).toContain("整份候选（来源未提供精确字段）");
  expect(host.textContent).toContain("<script>literal candidate explanation</script>");
  expect(host.querySelector("script")).toBeNull();
});
async function directions(value: string) {
  const textarea = host.querySelector("textarea")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
it("retains one exact command after a lost ACK and explicitly resends it only after reconciliation", async () => {
  await render(); await click("修改要求后重试");
  await directions("保留原简报");
  await click("再修正一次"); await click("再修正一次");
  expect(autopilotApi.retryText).toHaveBeenCalledTimes(1);
  expect(autopilotApi.retryText).toHaveBeenCalledWith("a", expect.objectContaining({ expectedRunId: failure.runId,
    failedAttemptId: failure.failedAttemptId, rejectionHash: failure.rejectionHash, directions: "保留原简报" }));
  expect(host.querySelector("textarea")?.value).toBe("保留原简报");
  expect(host.textContent).toContain("不会自动重发");
  const body = vi.mocked(autopilotApi.retryText).mock.calls[0][1];
  await click("核对本次修正");
  expect(autopilotApi.retryText).toHaveBeenCalledTimes(1);
  await click("重发同一本次请求");
  expect(autopilotApi.retryText).toHaveBeenCalledTimes(2);
  expect(vi.mocked(autopilotApi.retryText).mock.calls[1][1]).toBe(body);
});
it("restores the preserved draft after a definite refusal and fresh same-failure reconciliation", async () => {
  vi.mocked(autopilotApi.retryText).mockRejectedValue(new ApiError("not accepted", 422));
  await render(); await click("修改要求后重试"); await directions("保留原简报");
  await click("再修正一次");
  expect(host.querySelector("textarea")?.disabled).toBe(true);
  await click("核对本次修正");
  expect(host.querySelector("textarea")?.disabled).toBe(false);
  expect(host.querySelector("textarea")?.value).toBe("保留原简报");
  expect(autopilotApi.retryText).toHaveBeenCalledTimes(1);
  await directions("修改后的要求"); await click("再修正一次");
  const calls = vi.mocked(autopilotApi.retryText).mock.calls;
  expect(calls[1][1].commandId).not.toBe(calls[0][1].commandId);
  expect(calls[1][1].directions).toBe("修改后的要求");
});
it("keeps an unsent draft on revision churn but never transfers it to another failed attempt", async () => {
  await render(); await click("修改要求后重试"); await directions("保留原简报");
  vi.mocked(autopilotApi.textFailure).mockResolvedValue({ ...failure, runRevision: fixtureRun.revision + 1 });
  await render("a", { ...fixtureRun, revision: fixtureRun.revision + 1 });
  expect(host.querySelector("textarea")?.value).toBe("保留原简报");
  vi.mocked(autopilotApi.textFailure).mockResolvedValue({ ...failure, runRevision: fixtureRun.revision + 2, failedAttemptId: "22222222-2222-4222-8222-222222222222" });
  await render("a", { ...fixtureRun, revision: fixtureRun.revision + 2 });
  expect(host.querySelector("textarea")).toBeNull();
  await click("修改要求后重试"); expect(host.querySelector("textarea")?.value).toBe("");
});
it("ignores a late read after an A-B-A transition", async () => {
  let complete!: (value: TextFailure) => void;
  vi.mocked(autopilotApi.textFailure).mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
  await render("a"); await render("b"); await render("a");
  await act(async () => complete({ ...failure, reason: "stale first A" }));
  expect(host.textContent).not.toContain("stale first A");
  expect(autopilotApi.retryText).not.toHaveBeenCalled();
});
it("recovers an initial details read failure at the same revision through a read-only action", async () => {
  vi.mocked(autopilotApi.textFailure).mockRejectedValueOnce(new Error("transient read"));
  await render(); expect(host.textContent).toContain("暂时无法读取");
  await click("重新读取问题");
  expect(host.textContent).toContain("美术方向");
  expect(host.textContent).toContain("再修正一次");
  expect(autopilotApi.retryText).not.toHaveBeenCalled();
});
