import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { demoRun } from "../src/demo";
import { TracePage } from "../src/pages/TracePage";
import { QuarantinePage } from "../src/pages/QuarantinePage";
import { canRequestRunCancellation, repairRefusalExplanation, runCancellationLabel, runStatusLabels, workUnitStatusLabels } from "../src/run-presentation";
import { useRunCommands } from "../src/app/workspace/useRunCommands";
import { plotloomApi } from "../src/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("explains stale and uncertain repair boundaries without claiming a known failure or automatic retry", () => {
  expect(repairRefusalExplanation("repair.snapshot_stale")).toContain("所依据的内容已变更");
  expect(repairRefusalExplanation("repair.target_outcome_unknown")).toContain("不能自动重试");
  expect(repairRefusalExplanation("repair.target_outcome_unknown")).not.toContain("请求失败");
  expect(repairRefusalExplanation("repair.not_eligible")).toContain("运行轨迹");
});

it.each(Object.keys(runStatusLabels) as Array<keyof typeof runStatusLabels>)("names the public run state %s without changing cancellation eligibility", status => {
  const run = { ...demoRun, status };
  expect(runStatusLabels[status]).toMatch(/[\u4e00-\u9fff]/);
  expect(canRequestRunCancellation(run)).toBe(["queued", "running", "cancel_requested"].includes(status));
  expect(runCancellationLabel(run)).toBe(status === "cancel_requested" ? "再次请求取消" : "取消运行");
});
it.each(Object.keys(runStatusLabels) as Array<keyof typeof runStatusLabels>)("cancellation command retains the public %s eligibility without saving a profile", async status => {
  const run = { ...demoRun, status };
  const cancel = vi.spyOn(plotloomApi, "cancelRun").mockResolvedValue({ ...run, status: "cancel_requested" });
  const saveProfile = vi.fn(); const acceptRun = vi.fn(); const pollRun = vi.fn(async () => {});
  const host = document.createElement("div"); const root = createRoot(host);
  let commands!: ReturnType<typeof useRunCommands>;
  function Harness() {
    commands = useRunCommands({ apiTextPipeline: true,
      session: { project: { id: run.projectId }, run, route: { run: run.id }, capture: vi.fn(), isCurrent: () => true, acceptRun },
      profiles: { draft: { enabled: true }, save: saveProfile }, pollRun, openTrace: vi.fn(), setBusy: vi.fn(), setError: vi.fn(), hasDraft: () => false,
    } as never);
    return null;
  }
  try {
    await act(async () => root.render(createElement(Harness)));
    await act(async () => commands.cancelRun());
    if (["queued", "running", "cancel_requested"].includes(status)) {
      expect(cancel).toHaveBeenCalledExactlyOnceWith(run.id); expect(acceptRun).toHaveBeenCalledOnce();
    } else { expect(cancel).not.toHaveBeenCalled(); expect(acceptRun).not.toHaveBeenCalled(); }
    expect(saveProfile).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); cancel.mockRestore(); }
});
it.each(Object.keys(workUnitStatusLabels) as Array<keyof typeof workUnitStatusLabels>)("names the public subtask state %s distinctly", status => {
  expect(workUnitStatusLabels[status]).toMatch(/[\u4e00-\u9fff]/);
  expect(new Set(Object.values(workUnitStatusLabels)).size).toBe(Object.keys(workUnitStatusLabels).length);
});
it("explains and deliberately re-signals a pending cancellation rather than implying a new one", async () => {
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host); const onCancel = vi.fn(async () => {});
  try {
    await act(async () => root.render(createElement(TracePage, { apiTextPipeline: true,
      run: { ...demoRun, status: "cancel_requested" }, trace: [], running: true,
      onRun: vi.fn(async () => {}), onResume: vi.fn(async () => {}), onCancel,
    })));
    expect(host.textContent).toContain("已请求取消，等待运行结束");
    expect(host.textContent).toContain("正在等待运行结束");
    expect(host.textContent).not.toContain("cancel_requested");
    const cancel = [...host.querySelectorAll("button")].find(button => button.textContent === "再次请求取消")!;
    expect(cancel.disabled).toBe(false);
    await act(async () => cancel.click()); expect(onCancel).toHaveBeenCalledOnce();
  } finally { await act(async () => root.unmount()); host.remove(); }
});

it("does not invite selecting nonexistent events and presents pending events without success colour", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const props = { run: { ...demoRun, status: "running" as const }, running: true,
    onRun: vi.fn(async () => {}), onResume: vi.fn(async () => {}), onCancel: vi.fn(async () => {}),
    progress: { runId: demoRun.id, status: "running" as const, failureCode: null, failedStage: null, stageProgress: [], workUnits: [],
      actions: { canResume: false, canCancel: true, canRebuildStage: false, repairEligible: false } },
  };
  try {
    await act(async () => root.render(createElement(TracePage, { apiTextPipeline: true, ...props, trace: [] })));
    expect(host.querySelector(".run-progress-panel")?.textContent).toContain("当前暂无可查看的事件详情");
    expect(host.textContent).not.toContain("选择事件");
    await act(async () => root.render(createElement(TracePage, { apiTextPipeline: true, ...props, trace: [{
      id: "pending", at: "12:00:00", stage: "story_graph", kind: "request", title: "正在执行", status: "pending",
    }] })));
    expect(host.querySelector(".run-progress-panel")?.textContent).toContain("选择事件");
    expect(host.querySelector(".inspector-meta .badge")?.classList.contains("accent")).toBe(true);
    expect(host.querySelector(".inspector-meta .badge")?.classList.contains("ok")).toBe(false);
  } finally { await act(async () => root.unmount()); }
});

it("warns that rebuilding an uncertain result can duplicate generation without dispatching automatically", async () => {
  const host = document.createElement("div"); const root = createRoot(host);
  const onRebuildStage = vi.fn(async () => {}); const onRepair = vi.fn(async () => {});
  try {
    await act(async () => root.render(createElement(QuarantinePage, { apiTextPipeline: true,
      items: [{ id: "unknown", stage: "story_graph", status: "outcome_unknown", code: "transport.outcome_unknown",
        message: "请求的结果不确定", repairEligible: false, repairReasonCode: "repair.target_outcome_unknown" }],
      repairing: false, onRebuildStage, onRepair,
    })));
    expect(host.querySelector(".repair-rebuild-separator")?.textContent).toContain("也可能重复生成");
    expect(onRebuildStage).not.toHaveBeenCalled(); expect(onRepair).not.toHaveBeenCalled();
    const rebuild = [...host.querySelectorAll("button")].find(button => button.textContent === "重建本阶段及后续阶段")!;
    expect(rebuild.disabled).toBe(false);
    await act(async () => rebuild.click()); expect(onRebuildStage).toHaveBeenCalledExactlyOnceWith("story_graph");
  } finally { await act(async () => root.unmount()); }
});

it.each([false, null, undefined])("keeps Quarantine recovery controls disabled for capability %s", async apiTextPipeline => {
  const host = document.createElement("div"), root = createRoot(host);
  const onRepair = vi.fn(async () => {}), onRebuildStage = vi.fn(async () => {});
  try {
    await act(async () => root.render(createElement(QuarantinePage, { apiTextPipeline,
      items: [{ id: "eligible", stage: "story_graph", code: "failed", message: "failed", repairEligible: true }],
      repairing: false, onRepair, onRebuildStage,
    })));
    const buttons = [...host.querySelectorAll("button")].filter(button =>
      ["重新执行此子任务", "重建本阶段及后续阶段"].includes(button.textContent || ""));
    expect(buttons).toHaveLength(2);
    for (const button of buttons) { expect(button.disabled).toBe(true); await act(async () => button.click()); }
    expect(onRepair).not.toHaveBeenCalled(); expect(onRebuildStage).not.toHaveBeenCalled();
    expect(host.textContent).toContain(apiTextPipeline === false ? "未启用 API" : "尚未读入");
  } finally { await act(async () => root.unmount()); }
});
