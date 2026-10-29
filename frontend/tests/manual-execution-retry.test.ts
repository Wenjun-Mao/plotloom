import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ManualExecutionRetry, exhaustedExecution } from "../src/features/generation-retry/ManualExecutionRetry";
import type { GenerationRetryStatus } from "../src/features/generation-retry/contracts";
import { GenerationRetryStatus as StatusView } from "../src/features/generation-retry/GenerationRetryStatus";
import { LanguageTaskObserver } from "../src/features/content-language/LanguageTaskObserver";
import { ContentLanguageReview } from "../src/features/content-language/ContentLanguageReview";
import { useContentLanguageCheck } from "../src/features/content-language/useContentLanguageCheck";
import { contentLanguageApi } from "../src/features/content-language/api";
import { ExecutionRetries } from "../src/features/autopilot/ExecutionRetries";
import { AutopilotWorkspace } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { BatchExecutionRetries } from "../src/features/video-batch/ExecutionRetries";
import { plotloomApi } from "../src/api";
import { ApiTransport } from "../src/api-transport";
import type { VideoJob } from "../src/types";
import { fixtureRun } from "./autopilot-fixture";
import { languagePass } from "./content-language-fixture";
import { productionBatch } from "./h3-production-fixtures";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, host: HTMLDivElement;
const retry: GenerationRetryStatus = { retryCount: 2, automaticRetriesUsed: 1, automaticRetryLimit: 1,
  currentJobId: "physical-failed", currentAttemptId: "attempt-failed", predecessorJobIds: ["physical-old"], state: "exhausted", possiblePriorCost: true };
const button = (name = "手动重试此任务") => [...host.querySelectorAll("button")].find(item => item.textContent === name)!;
const click = async (name?: string) => act(async () => button(name).click());
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
it.each(["ready", "running", "retry_pending", "stopped"] as const)("does not offer manual retry for %s", async state => {
  const post = vi.fn();
  await act(async () => root.render(createElement(ManualExecutionRetry, { identity: "owner", status: { ...retry, state }, disabled: false, onRetry: post, onObserve: vi.fn() })));
  expect(button()).toBeUndefined(); expect(post).not.toHaveBeenCalled();
});
it("requires current native attempt identity; H3 uses only its exact current job", () => {
  expect(exhaustedExecution({ ...retry, currentAttemptId: null })).toBeNull();
  expect(exhaustedExecution({ ...retry, currentJobId: null }, false)).toBeNull();
  expect(exhaustedExecution(retry, false)).toEqual({ failedJobId: "physical-failed" });
});
it("one explicit UUID intent survives lost ACK and disables replay until a fresh owner read", async () => {
  const post = vi.fn().mockRejectedValue(new Error("lost acknowledgement")), read = vi.fn().mockResolvedValue(undefined);
  const uuid = vi.spyOn(crypto, "randomUUID");
  await act(async () => root.render(createElement(ManualExecutionRetry, { identity: "owner:revision1", status: retry, disabled: false, onRetry: post, onObserve: read })));
  expect(post).not.toHaveBeenCalled(); expect(uuid).not.toHaveBeenCalled();
  await click(); await click();
  expect(post).toHaveBeenCalledTimes(1); expect(uuid).toHaveBeenCalledTimes(1); expect(button().disabled).toBe(true);
  expect(post.mock.calls[0][0]).toMatchObject({ commandId: expect.stringMatching(/^[a-f0-9-]{36}$/), failedJobId: retry.currentJobId, failedAttemptId: retry.currentAttemptId });
  const notice = host.querySelector('[role="alert"]')!;
  expect(notice.querySelector("span")?.textContent).toContain("请读取当前任务后再决定");
  expect(notice.querySelector("span")?.textContent).not.toContain("lost acknowledgement");
  expect(notice.querySelector("details")?.hasAttribute("open")).toBe(false);
  expect(notice.querySelector("pre")?.textContent).toBe("lost acknowledgement");
  expect(read).not.toHaveBeenCalled(); await click("读取当前任务后再决定");
  expect(read).toHaveBeenCalledTimes(1); expect(button().disabled).toBe(false);
  await click(); expect(post).toHaveBeenCalledTimes(2); expect(post.mock.calls[0][0].commandId).not.toBe(post.mock.calls[1][0].commandId);
});
it("a failed observation retains the original intent and cannot unlock a replay", async () => {
  const post = vi.fn().mockRejectedValue(new Error("unknown")), read = vi.fn().mockRejectedValue(new Error("read failed"));
  await act(async () => root.render(createElement(ManualExecutionRetry, { identity: "owner", status: retry, disabled: false, onRetry: post, onObserve: read })));
  await click(); await click("读取当前任务后再决定"); await click(); expect(post).toHaveBeenCalledTimes(1); expect(button().disabled).toBe(true);
});
it("a late old response cannot poison the current owner or retry its old child", async () => {
  let reject!: (reason: Error) => void;
  const post = vi.fn().mockReturnValueOnce(new Promise((_resolve, no) => { reject = no; })).mockResolvedValue(undefined);
  const props = { status: retry, disabled: false, onRetry: post, onObserve: vi.fn() };
  await act(async () => root.render(createElement(ManualExecutionRetry, { ...props, identity: "old" })));
  await click();
  await act(async () => root.render(createElement(ManualExecutionRetry, { ...props, identity: "new", status: { ...retry, currentJobId: "new-child", currentAttemptId: "new-attempt" } })));
  await act(async () => reject(new Error("late old ACK")));
  expect(button().disabled).toBe(false); await click(); expect(post.mock.calls[1][0].failedJobId).toBe("new-child");
});
it("separates actual automatic use from manual successors and keeps current IDs technical", async () => {
  await act(async () => root.render(createElement(StatusView, { status: retry })));
  expect(host.textContent).toContain("已用 1 次"); expect(host.textContent).toContain("另有 1 次手动重试");
  expect(host.querySelector("details")?.textContent).toContain("physical-failed"); expect(host.querySelector("details")?.hasAttribute("open")).toBe(false);
});
it("language manual retry keeps its logical anchor while targeting the current physical successor", async () => {
  const original = { prose: "A keeper leaves." };
  const status = { ...languagePass(), state: "failed" as const, verdict: null, retry };
  vi.spyOn(contentLanguageApi, "status").mockResolvedValue(status);
  const post = vi.spyOn(contentLanguageApi, "retry").mockResolvedValue({ ...status, state: "running", retry: { ...retry, retryCount: 3, currentJobId: "physical-next", currentAttemptId: "attempt-next", state: "running" } });
  const check = vi.spyOn(contentLanguageApi, "check");
  function Host() { const value = useContentLanguageCheck({ projectId: "project", stage: "art", jobId: "candidate", candidate: original, original }); return createElement(ContentLanguageReview, { check: value }); }
  await act(async () => root.render(createElement(Host))); expect(post).not.toHaveBeenCalled(); await click();
  expect(post).toHaveBeenCalledWith("project", "check-original", { commandId: expect.any(String), failedJobId: "physical-failed", failedAttemptId: "attempt-failed" });
  expect(check).not.toHaveBeenCalled(); expect(button()).toBeUndefined();
  expect(host.querySelector("details")?.textContent).toContain("physical-next");
});
it("autopilot sends exact run/CAS/current-attempt ownership and reads after an ambiguous response", async () => {
  const run = { ...fixtureRun, state: "waiting" as const, phase: "references", revision: 40,
    checkpoints: [{ operationKey: "image:shot", state: "failed", retry, evidence: { owner: "image", result: {} } }] };
  vi.spyOn(autopilotApi, "current").mockResolvedValue(run);
  const post = vi.spyOn(autopilotApi, "retryExecution").mockRejectedValue(new Error("ACK lost"));
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1, readOnly: false, onChanged: vi.fn(), onVideo: vi.fn(), children: null })));
  await click(); expect(post).toHaveBeenCalledWith("disposable", { commandId: expect.any(String), expectedRunId: run.id, expectedRevision: 40, failedJobId: "physical-failed", failedAttemptId: "attempt-failed" });
  expect(button().disabled).toBe(true); await click("读取当前任务后再决定"); expect(button().disabled).toBe(false);
});
it("batch H3 retry selects only the current exhausted job; cancelled and obsolete predecessors stay unavailable", async () => {
  const batch = productionBatch({ shotId: "shot", seed: 1, profileId: "h3", aspectPolicy: "cover_center_crop" } as never);
  batch.state = "blocked"; batch.execution.jobs = { shot: "physical-failed" };
  const job = { id: "physical-failed", projectId: "project", state: "outcome_unknown", cancelRequestedAt: null, lifecycleStatus: "active", inputStatus: "current", retry } as VideoJob;
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [{ ...job, id: "physical-old" }, job] });
  const post = vi.fn().mockResolvedValue(undefined);
  const render = async () => act(async () => root.render(createElement(BatchExecutionRetries, { projectId: "project", batch, disabled: false, onRetry: post, onObserve: vi.fn() })));
  await render(); expect(host.querySelectorAll('[aria-label="手动重试此失败任务"]')).toHaveLength(1); await click();
  expect(post).toHaveBeenCalledWith({ commandId: expect.any(String), expectedRevision: batch.revision, failedJobId: "physical-failed" });
  vi.mocked(plotloomApi.getVideoJobs).mockResolvedValue({ jobs: [{ ...job, cancelRequestedAt: "now" }] }); batch.revision++;
  await render(); expect(button()).toBeUndefined();
});
it("batch native draft and fidelity retry require exact failed attempts", async () => {
  const batch = productionBatch({ shotId: "shot", seed: 1, profileId: "h3", aspectPolicy: "cover_center_crop" } as never);
  batch.state = "blocked"; batch.execution.draft = { retry }; batch.execution.fidelity = { retry: { ...retry, state: "stopped" } };
  const post = vi.fn().mockResolvedValue(undefined);
  await act(async () => root.render(createElement(BatchExecutionRetries, { projectId: "project", batch, disabled: false, onRetry: post, onObserve: vi.fn() })));
  expect(host.querySelectorAll('[aria-label="手动重试此失败任务"]')).toHaveLength(1); await click();
  expect(post).toHaveBeenCalledWith({ commandId: expect.any(String), expectedRevision: batch.revision, failedJobId: "physical-failed", failedAttemptId: "attempt-failed" });
});
it("uses the dedicated language and autopilot endpoints with a literal UUID and exact request bodies", async () => {
  const json = vi.spyOn(ApiTransport.prototype, "json").mockResolvedValue({ body: {} } as never);
  const commandId = crypto.randomUUID(), failed = { commandId, failedJobId: "physical", failedAttemptId: "attempt" };
  await contentLanguageApi.retry("project", "logical-anchor", failed);
  expect(json).toHaveBeenLastCalledWith("/projects/project/content-language-checks/logical-anchor/retry", { method: "POST", body: JSON.stringify(failed) });
  const body = { ...failed, expectedRunId: "run", expectedRevision: 3 }; await autopilotApi.retryExecution("project", body);
  expect(json).toHaveBeenLastCalledWith("/projects/project/autopilot/retry-execution", { method: "POST", body: JSON.stringify(body) });
});
it("a late earlier physical observation cannot replace the current language successor or receive its old pass", async () => {
  let resolve!: (value: ReturnType<typeof languagePass>) => void;
  vi.spyOn(contentLanguageApi, "reconcile").mockReturnValue(new Promise(done => { resolve = done; }));
  const initial = { ...languagePass(), state: "outcome_unknown" as const, verdict: null, retry };
  const verified = vi.fn();
  const render = async (value: typeof initial | { retry: typeof retry } & Omit<typeof initial, "state"> & { state: "running" }) => act(async () => root.render(createElement(LanguageTaskObserver, { projectId: "project", initial: value, disabled: false, onVerified: verified })));
  await render(initial); await click("核对原语言检查");
  await render({ ...initial, state: "running", retry: { ...retry, retryCount: 3, currentJobId: "latest-child", currentAttemptId: "latest-attempt", state: "running" } });
  await act(async () => resolve({ ...languagePass(), retry }));
  expect(host.querySelector("details")?.textContent).toContain("latest-child"); expect(verified).not.toHaveBeenCalled();
});

it("a failed logical checker can only be observed through its ordinary check control, never reposted", async () => {
  const original = { prose: "A keeper leaves." };
  const status = { ...languagePass(), state: "failed" as const, verdict: null, retry };
  vi.spyOn(contentLanguageApi, "status").mockResolvedValue(status);
  const check = vi.spyOn(contentLanguageApi, "check"), read = vi.spyOn(contentLanguageApi, "reconcile").mockResolvedValue(status);
  function Host() { const value = useContentLanguageCheck({ projectId: "project", stage: "art", jobId: "candidate", candidate: original, original }); return createElement(ContentLanguageReview, { check: value }); }
  await act(async () => root.render(createElement(Host))); await click("核对原语言检查");
  expect(check).not.toHaveBeenCalled(); expect(read).toHaveBeenCalledWith("project", "check-original");
});

it("current-owner reads stay reachable when mutations are locked after a lost acknowledgement", async () => {
  const post = vi.fn().mockRejectedValue(new Error("ACK lost")), read = vi.fn().mockResolvedValue(undefined);
  const props = { identity: "same-owner", status: retry, onRetry: post, onObserve: read };
  await act(async () => root.render(createElement(ManualExecutionRetry, { ...props, disabled: false }))); await click();
  await act(async () => root.render(createElement(ManualExecutionRetry, { ...props, disabled: true })));
  expect(button().disabled).toBe(true); expect(button("读取当前任务后再决定").disabled).toBe(false);
  await click("读取当前任务后再决定"); expect(read).toHaveBeenCalledTimes(1); expect(button().disabled).toBe(true);
});

it("autopilot never offers a historical predecessor or a paused execution as a manual retry target", async () => {
  const run = { ...fixtureRun, state: "waiting" as const, checkpoints: [
    { operationKey: "image:shot", state: "failed", retry, evidence: { owner: "image", result: {} } },
    { operationKey: "image:shot:retry:3", state: "sent", retry: { ...retry, state: "running" as const, currentJobId: "new-child", currentAttemptId: "new-attempt", predecessorJobIds: ["physical-failed"] }, evidence: { owner: "image", result: {} } },
  ] };
  const props = { projectId: "project", disabled: false, onRetry: vi.fn(), onObserve: vi.fn() };
  await act(async () => root.render(createElement(ExecutionRetries, { ...props, run }))); expect(button()).toBeUndefined();
  const paused = { ...run, state: "paused" as const, checkpoints: [run.checkpoints[0]] };
  await act(async () => root.render(createElement(ExecutionRetries, { ...props, run: paused }))); expect(button()).toBeUndefined();
  expect(host.textContent).toContain("请先继续原运行"); expect(props.onRetry).not.toHaveBeenCalled();
});
