import type { GenerationWorkUnitTrace, PipelineRun, RunStatus, TraceEvent } from "./types";

export const runStatusLabels: Record<RunStatus, string> = {
  queued: "排队中", running: "正在运行", succeeded: "已完成", quarantined: "结果已隔离",
  cancel_requested: "已请求取消，等待运行结束", cancelled: "已取消", failed: "运行失败",
};
export const workUnitStatusLabels: Record<GenerationWorkUnitTrace["status"], string> = {
  queued: "等待执行", running: "正在执行", succeeded: "已完成", failed: "执行失败",
  quarantined: "输出未通过校验（已隔离）", cancelled: "已取消", outcome_unknown: "请求结果不确定",
};
export const runKindLabels: Record<PipelineRun["kind"], string> = {
  pipeline: "阶段生成", rebuild: "阶段重建", repair: "单独修复",
};
export const traceStatusLabels: Record<TraceEvent["status"], string> = {
  pending: "进行中", ok: "已记录", warning: "需要注意", error: "失败",
};
export const traceKindLabels: Record<TraceEvent["kind"], string> = {
  request: "执行请求", prompt: "提示词", response: "模型回复", validation: "校验结果",
  candidate: "生成候选", install: "保存结果", error: "失败记录",
};

/** Pending cancellation can be re-signalled by the public server contract. */
export function canRequestRunCancellation(run?: PipelineRun): boolean {
  return Boolean(run && ["queued", "running", "cancel_requested"].includes(run.status));
}
export function runCancellationLabel(run?: PipelineRun): string {
  return run?.status === "cancel_requested" ? "再次请求取消" : "取消运行";
}

export function repairRefusalExplanation(reason?: string | null): string {
  if (reason === "repair.snapshot_stale") return "这次运行所依据的内容已变更，不能按原要求单独重做。请先核对当前内容，再决定是否重建。";
  if (reason === "repair.target_outcome_unknown") return "模型请求的结果不确定。为避免重复生成，不能自动重试或单独重做；请先核实原请求的结果。";
  return "这个子任务暂不满足单独重做的条件。请在运行轨迹中核对原请求与结果。";
}
