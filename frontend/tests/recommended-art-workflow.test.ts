import { expect, it } from "vitest";
import { artWorkflowNextText } from "../src/app/workspace/recommendedArtWorkflow";
import type { ArtWorkflowObservation } from "../src/app/workspace/ReviewWorkflowReadContext";
import type { ArtBinding, ArtCandidate, ArtReviewState } from "../src/types";

const missing: ArtReviewState = { status: "missing", candidate: null, acceptedArt: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } };
const binding: ArtBinding = { sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "sections", graphRevision: 1, graphContentHash: "graph", sectionIds: ["opening"], castRevision: 1, castContentHash: "cast" };
const candidate = (status: ArtCandidate["status"]): ArtCandidate => ({ jobId: "art-job", expectedArtRevision: 0, binding, status, deliveryId: null, manifestHash: null, art: null, reportAvailable: false, createdAt: "2026-10-11T00:00:00Z", deliveredAt: null });
const read = (state = missing): ArtWorkflowObservation => ({ stage: "art", status: "ready", state, busy: false, dirty: false, retainedDraft: false, renderStyle: "" });
const hint = (value?: ArtWorkflowObservation) => artWorkflowNextText(value).text;

it("names style selection before the disabled preparation control", () => {
  expect(hint(read())).toContain("先选择「美术风格」");
  expect(hint({ ...read(), renderStyle: "live-action" })).toContain("美术风格已选择。点击「准备美术设定任务」");
  expect(hint(read())).toContain("不会自动生成图片");
});
it.each(["loading", "failed"] as const)("keeps %s reads ahead of previous state and failure", status => {
  const error = { code: "accepted_cast_not_current", owner: "characters", field: null, technicalMessage: "Missing cast" } as const;
  expect(hint({ ...read(), status, error })).toContain(status === "loading" ? "正在读取" : "重试加载美术参考");
  expect(hint({ ...read(), status, error })).not.toContain("点击左侧「角色」");
});
it("reports the actual prerequisite, not another failed preparation", () => {
  const error = { code: "accepted_cast_not_current", owner: "characters", field: null, technicalMessage: "Missing cast" } as const;
  expect(hint({ ...read(), error })).toContain("点击左侧「角色」");
  expect(hint({ ...read(), error })).not.toContain("准备美术设定任务");
  expect(hint({ ...read(), busy: true, error })).toContain("正在处理美术任务");
});
it.each(["prepared", "ready"] as const)("projects a fresh %s candidate independently of retained old evidence", status => {
  const state: ArtReviewState = { ...missing, status: status === "ready" ? "candidate_ready" : "prepared", candidate: candidate(status), acceptedReviewState: { status: "retained", staleReasons: [] } };
  expect(hint(read(state))).toContain(status === "ready" ? "确认使用此美术提案" : "立即检查");
  expect(hint(read(state))).not.toContain("美术依据已变化");
  expect(hint({ ...read(state), retainedDraft: true, dirty: true })).toContain("舍弃美术草稿");
  state.status = "stale";
  expect(hint(read(state))).toContain("美术依据已变化");
});
it("keeps reopened edits and accepted continuation distinct", () => {
  expect(hint(read({ ...missing, status: "reopened" }))).toContain("保存重新打开的美术");
  const state: ArtReviewState = { ...missing, status: "accepted", acceptedArt: { revision: 1, candidateJobId: "art-job", contentHash: "art", binding, art: { scenes: [], props: [] }, acceptedAt: "2026-10-11T00:00:00Z" }, acceptedReviewState: { status: "current", staleReasons: [] } };
  expect(hint(read(state))).toContain("继续：剧本");
  state.acceptedReviewState.status = "retained";
  expect(hint(read(state))).not.toContain("继续：剧本");
});
