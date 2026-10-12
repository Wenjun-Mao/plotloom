import { expect, it } from "vitest";
import { storyboardWorkflowNextText } from "../src/app/workspace/recommendedStoryboardWorkflow";
import type { StoryboardWorkflowObservation, BridgeWorkflowObservation } from "../src/app/workspace/ReviewWorkflowReadContext";
import type { StoryboardReviewState, ProductionBridgeProposal } from "../src/types";
import { workflowProductionFixture } from "./workflow-production-fixture";
import { bridgeState, installedProduction } from "./production-bridge-fixture";

const missing = (): StoryboardReviewState => ({ status: "missing", candidate: null, acceptedReview: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } });
const read = (state = missing()): StoryboardWorkflowObservation => ({ stage: "storyboard-review", status: "ready", state, busy: false, dirty: false });
const accepted = () => read(workflowProductionFixture({ graphAdmission: {} } as never).storyboardSource!);
const bridge = (): BridgeWorkflowObservation => ({ stage: "production-bridge", status: "ready", state: bridgeState(), busy: false, dirty: false, blocked: false, canonicalReady: true, canOpenShot: true });
const next = (value?: StoryboardWorkflowObservation, production?: BridgeWorkflowObservation) => storyboardWorkflowNextText(value, production).text;

it("names preparation only after the current missing read", () => {
  expect(next(read())).toContain("点击「准备分镜任务」");
  expect(next()).toContain("正在读取当前分镜评审状态");
  expect(next({ ...read(), status: "loading" })).not.toContain("点击「准备");
  expect(next({ ...read(), status: "failed" })).toContain("重试加载分镜评审");
});
it.each(["prepared", "ready"] as const)("names the actual %s candidate, not retained old evidence", status => {
  const state = accepted().state!;
  state.candidate = { status } as never;
  state.acceptedReviewState.status = "retained";
  expect(next(read(state))).toContain(status === "ready" ? "阅读原始分镜报告（只读）" : "尚未交付");
  if (status === "ready") {
    expect(next(read(state))).toContain("放大阅读报告");
    expect(next(read(state))).toContain("查看待审阅分镜");
    expect(next(read(state))).toContain("确认此分镜评审方案");
  }
  state.status = "stale";
  expect(next(read(state))).toContain("依据已变化");
  expect(next(read(state))).not.toContain("确认此分镜评审方案");
});
it("suppresses actions for failed, busy or rejected preparation", () => {
  expect(next({ ...read(), busy: true })).toContain("不要重复");
  expect(next({ ...read(), error: { code: "accepted_script_not_current", owner: "script", field: null, technicalMessage: "missing" } })).toContain("剧本");
  const value = accepted(); value.state!.acceptedReviewState.status = "retained";
  expect(next(value, bridge())).not.toContain("点击下方「准备投产提案」");
});
it("does not infer production readiness from Storyboard acceptance", () => {
  expect(next(accepted())).toContain("正在读取对应投产提案");
  expect(next(accepted(), { ...bridge(), status: "failed" })).toContain("「重试加载」");
  const value = bridge(); value.state!.preparation = { status: "unavailable", reason: "unresolved publication" };
  expect(next(accepted(), value)).toContain("展开下方「提案准备诊断」");
  expect(next(accepted(), value)).not.toContain("点击下方「准备投产提案」");
  expect(next(accepted(), bridge())).toContain("点击下方「准备投产提案」");
});
it("keeps unresolved native jobs at the same-task check owner", () => {
  const value = bridge(); value.state!.intentJob = { transport: "codex_native", status: "outcome_unknown" } as never;
  expect(next(accepted(), value)).toContain("检查原任务交付");
  expect(next(accepted(), value)).not.toContain("准备 Codex");
  value.state!.intentJob = { transport: "codex_native", status: "queued" } as never;
  value.state!.nativeIntentTask = { state: "prepared" } as never;
  value.state!.nativeIntentGeneration = { status: "available" };
  expect(next(accepted(), value)).toContain("发送给 Codex 文字助手");
  value.state!.intentJob = { transport: "text_api", status: "queued" } as never;
  expect(next(accepted(), value)).toContain("继续排队任务");
});
it("never names a disabled queued-job control", () => {
  const value = bridge(); value.state!.intentJob = { transport: "text_api", status: "queued" } as never;
  value.state!.intentGeneration = { status: "unavailable", reason: "not_configured" };
  expect(next(accepted(), value)).toContain("生成助手设置");
  expect(next(accepted(), value)).not.toContain("点击「继续排队任务」");
  value.state!.intentJob = { transport: "codex_native", status: "queued" } as never;
  value.state!.nativeIntentTask = { state: "prepared" } as never;
  expect(next(accepted(), value)).toContain("生成助手设置");
  expect(next(accepted(), value)).not.toContain("点击「发送给 Codex 文字助手」");
  value.state!.nativeIntentGeneration = { status: "available" }; value.state!.status = "stale";
  expect(next(accepted(), value)).toContain("取消 Codex 意图任务");
  expect(next(accepted(), value)).not.toContain("点击「发送给 Codex 文字助手」");
});
it("names intent, presentation and installation as independent controls", () => {
  const value = bridge(); value.state!.status = "ready"; value.state!.nativeIntentGeneration = { status: "available" };
  const proposal = { intentPackage: { reviewState: "pending" }, presentation: { reviewed: false }, installable: false } as ProductionBridgeProposal;
  value.state!.proposal = proposal;
  expect(next(accepted(), value)).toContain("准备 Codex 戏剧意图任务");
  proposal.intentPackage.reviewState = "model_suggested";
  expect(next(accepted(), value)).toContain("保存戏剧意图整包");
  proposal.intentPackage.reviewState = "author_saved";
  expect(next(accepted(), value)).toContain("保存呈现方式审阅");
  proposal.presentation.reviewed = true;
  expect(next(accepted(), value)).toContain("具体冲突提示");
  proposal.installable = true;
  expect(next(accepted(), value)).toContain("点击「确认投产提案」");
  expect(next(accepted(), { ...value, dirty: true })).not.toContain("点击「确认投产提案」");
});
it("only names installed-shot navigation after acknowledged current installation", () => {
  const value = bridge(); value.state!.status = "accepted"; value.state!.installation = installedProduction({ cuts: [{ shotId: "s1", sectionId: "opening", episode: 1, sceneIndex: 1, seconds: 2.5, source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } }] });
  expect(next(accepted(), value)).toContain("继续：打开第一个镜头");
  expect(next(accepted(), { ...value, status: "loading" })).not.toContain("打开第一个镜头");
  expect(next(accepted(), { ...value, canonicalReady: false })).toContain("等待刷新");
  value.state!.installation.status = "outdated";
  expect(next(accepted(), value)).toContain("准备重建提案");
  expect(next(accepted(), value)).not.toContain("打开第一个镜头");
});
it("does not invent an installed-shot control for incomplete receipt coordinates", () => {
  const value = bridge(); value.state!.status = "accepted"; value.state!.installation = installedProduction({ cuts: [{ shotId: "s1" }] });
  expect(next(accepted(), value)).not.toContain("继续：打开第一个镜头");
  expect(next(accepted(), value)).toContain("创作工作台");
});
