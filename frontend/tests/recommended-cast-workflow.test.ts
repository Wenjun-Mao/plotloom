import { expect, it } from "vitest";
import { castWorkflowNextText } from "../src/app/workspace/recommendedCastWorkflow";
import type { CastWorkflowObservation } from "../src/app/workspace/ReviewWorkflowReadContext";
import type { CastBinding, CastCandidate, CastReviewState } from "../src/types";

const missing: CastReviewState = { status: "missing", candidate: null, acceptedCast: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } };
const binding: CastBinding = { sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "sections", graphRevision: 1, graphContentHash: "graph", sectionIds: ["opening"] };
const candidate = (status: CastCandidate["status"]): CastCandidate => ({ jobId: "cast-job", expectedCastRevision: 0, binding, status, deliveryId: null, manifestHash: null, cast: null, reportAvailable: false, createdAt: "2026-10-11T00:00:00Z", deliveredAt: null });
const read = (state = missing): CastWorkflowObservation => ({ stage: "characters", status: "ready", state, busy: false, dirty: false, retainedDraft: false, renderStyle: "", designValid: true });
const hint = (value?: CastWorkflowObservation) => castWorkflowNextText(value).text;

it("names the required style before preparation, without implying image generation", () => {
  expect(hint(read())).toContain("先选择「角色图像风格」");
  expect(hint({ ...read(), renderStyle: "live-action" })).toContain("点击「准备角色设定任务」");
  expect(hint(read())).toContain("不会自动生成图片");
});
it.each(["loading", "failed"] as const)("keeps %s reads ahead of prior state or errors", status => {
  expect(hint({ ...read(), status, error: "failed operation" })).toContain(status === "loading" ? "正在读取" : "重试加载角色设定");
});
it("keeps operations, verified errors and retained drafts ahead of commands", () => {
  expect(hint({ ...read(), busy: true, error: "failed" })).toContain("正在处理角色任务");
  expect(hint({ ...read(), error: { code: "source_context_not_ready", owner: "source", field: null, technicalMessage: "not current" } })).toContain("点击左侧「来源与大纲」");
  expect(hint({ ...read(), retainedDraft: true })).toContain("丢弃保留草稿");
});
it.each(["prepared", "ready"] as const)("keeps fresh %s replacement separate from retained accepted evidence", status => {
  const state: CastReviewState = { ...missing, status: status === "ready" ? "candidate_ready" : "prepared", candidate: candidate(status), acceptedReviewState: { status: "retained", staleReasons: [] } };
  expect(hint(read(state))).toContain(status === "prepared" ? "立即检查" : "确认使用此角色设定");
  state.status = "stale";
  expect(hint(read(state))).toContain("创作依据需要更新");
});
it("does not name a disabled design confirmation, but keeps valid edits confirmable", () => {
  const state: CastReviewState = { ...missing, status: "candidate_ready", candidate: candidate("ready") };
  expect(hint({ ...read(state), designValid: false })).toContain("性格特点");
  expect(hint({ ...read(state), designValid: false })).not.toContain("点击「确认使用此角色设定」");
  expect(hint({ ...read(state), dirty: true })).toContain("确认使用此角色设定");
  state.status = "reopened";
  expect(hint(read(state))).toContain("保存角色修改");
});
it("continues only with current accepted Role evidence", () => {
  const state: CastReviewState = { ...missing, status: "accepted", acceptedCast: { revision: 1, candidateJobId: "cast-job", binding, contentHash: "cast", cast: {}, consumerMappings: [], reportAvailable: false, differsFromDelivery: null, acceptedAt: "2026-10-11T00:00:00Z" }, acceptedReviewState: { status: "current", staleReasons: [] } };
  expect(hint(read(state))).toContain("继续：美术参考");
  state.acceptedReviewState.status = "retained";
  expect(hint(read(state))).not.toContain("继续：美术参考");
});
