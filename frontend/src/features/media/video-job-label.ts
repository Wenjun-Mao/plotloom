import type { VideoJob } from "../../types";
import { isCurrentVideoSelection } from "./video-next-action";

const stateLabels: Record<VideoJob["state"], string> = {
  prepared: "已准备 · 尚未提交",
  dispatching: "正在提交 · 请勿重复操作",
  submitted: "已提交 · 等待结果",
  outcome_unknown: "提交结果待核实 · 请勿重复提交",
  retrieve_needed: "结果待获取",
  ingested: "待审原片",
  discard_pending: "删除待完成",
  discarded: "已删除",
  cancelled: "已取消",
  failed: "生成未完成",
};

/** Request progress is distinct from selection and retained-media evidence. */
export function videoJobLabel(job: VideoJob): string {
  if (isCurrentVideoSelection(job)) return "已选择片段";
  if (job.state === "ingested") {
    if (!job.current) return "保留原片";
    return job.selected ? "已选原片 · 片段待确认" : "待审原片";
  }
  return stateLabels[job.state];
}
