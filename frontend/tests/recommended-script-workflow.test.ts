import { expect, it } from "vitest";
import { scriptWorkflowNextText } from "../src/app/workspace/recommendedScriptWorkflow";
import type { ScriptWorkflowObservation } from "../src/app/workspace/ScriptWorkflowReadContext";
import type { ScriptCandidate, ScriptReviewState } from "../src/types";
import { workflowProductionFixture } from "./workflow-production-fixture";

const missing = (): ScriptReviewState => ({ status: "missing", candidate: null, acceptedScript: null, staleReasons: [],
  acceptedReviewState: { status: "missing", staleReasons: [] } });
const read = (state = missing()): ScriptWorkflowObservation => ({ status: "ready", state, busy: false, dirty: false });
const next = (value?: ScriptWorkflowObservation) => scriptWorkflowNextText(value).text;

it("names preparation, not review, before a script exists", () => {
  expect(next(read())).toContain("当前没有剧本候选。点击「准备剧本任务」");
  expect(next(read())).toContain("收到剧本后审阅并确认");
  expect(next(read())).toContain("不会自动生成剧本或影片");
  expect(next(read())).not.toContain("审阅当前剧本");
});
it.each([undefined, { ...read(), status: "loading" as const }])("does not guess missing while a read is pending", value => {
  expect(next(value)).toContain("正在读取当前剧本状态");
  expect(next(value)).not.toContain("准备剧本任务");
});
it("names retry before using retained state on failure", () => {
  expect(next({ ...read(), status: "failed" })).toContain("点击本页「重试加载剧本」");
  expect(next({ ...read(), status: "failed" })).not.toContain("准备剧本任务");
});
it.each([["prepared", "剧本任务已准备，尚未交付"], ["ready", "查看待审阅剧本"]] as const)("uses the actual %s candidate stage", (status, text) => {
  const state = missing(); state.candidate = { status } as ScriptCandidate;
  expect(next(read(state))).toContain(text);
  expect(next(read(state))).not.toContain("当前没有剧本候选");
  if (status === "ready") expect(next(read(state))).toContain("确认使用此剧本");
});
it("only points to Continue for current accepted Script evidence", () => {
  const current = workflowProductionFixture({ graphAdmission: {} } as never).script!;
  expect(next(read(current))).toContain("点击「继续：分镜评审」");
  current.acceptedReviewState.status = "retained";
  expect(next(read(current))).not.toContain("继续：分镜评审");
  expect(next(read(current))).toContain("保留内容不代表当前确认");
});
it.each(["prepared", "ready"] as const)("does not confuse retained old evidence with a fresh %s replacement", status => {
  const state = workflowProductionFixture({ graphAdmission: {} } as never).script!;
  state.status = status === "ready" ? "candidate_ready" : "prepared"; state.candidate = { status } as ScriptCandidate;
  state.acceptedReviewState.status = "retained";
  expect(next(read(state))).toContain(status === "prepared" ? "剧本任务已准备，尚未交付" : "确认使用此剧本");
  expect(next(read(state))).not.toContain("剧本依据已变化");
  expect(next(read(state))).not.toContain("继续：分镜评审");
  state.status = "stale";
  expect(next(read(state))).toContain("剧本依据已变化");
});
it.each([["busy", "正在处理剧本任务"], ["dirty", "章节有未保存修改"]] as const)("suppresses next commands for %s", (field, text) => {
  expect(next({ ...read(), [field]: true })).toContain(text);
  expect(next({ ...read(), [field]: true })).not.toContain("准备剧本任务");
});
it.each(["reopened", "stale"] as const)("names the %s review boundary", status => {
  const state = missing(); state.status = status;
  expect(next(read(state))).toContain(status === "reopened" ? "保存此章节，不覆盖其他章节" : "剧本依据已变化");
  expect(next(read(state))).not.toContain("当前没有剧本候选");
});
