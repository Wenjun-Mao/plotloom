import { describe, expect, it } from "vitest";
import { demoProject } from "../src/demo";
import { appliedProductionRecommendation } from "../src/app/workspace/recommendedProductionWorkflow";
import type { RecommendedWorkflowInput } from "../src/app/workspace/recommendedWorkflow";
import type { ScriptCandidate, SourceOutlineReviewState, StoryboardReviewCandidate } from "../src/types";
import { installedProduction } from "./production-bridge-fixture";
import { workflowProductionFixture } from "./workflow-production-fixture";

const source = { graphAdmission: { sourceRevision: 1, outlineRevision: 1, outlineContentHash: "outline",
  sectionMapRevision: 1, sectionMapContentHash: "map", graphRevision: 2, graphContentHash: "graph" } } as SourceOutlineReviewState;
function input(activePage: "creator" | "graph" = "creator") {
  return { activePage, project: structuredClone(demoProject), sourceReview: source,
    productionRead: workflowProductionFixture(source) } as RecommendedWorkflowInput;
}
const next = (value: RecommendedWorkflowInput) => appliedProductionRecommendation(value, "opening", "「开场」");

describe.each(["creator", "graph"] as const)("state-driven production hints in %s", activePage => {
  it.each([
    ["missing", "剧本未确认"], ["prepared", "剧本任务已准备，尚未交付"],
    ["candidate_ready", "剧本候选已交付，尚未确认"], ["reopened", "剧本修订尚未完成"],
    ["stale", "剧本任务的来源已变化"], ["retained", "保留的已确认剧本不能用于当前制作"],
  ] as const)("names Script's verified %s state and sidebar entry", (state, wording) => {
    const value = input(activePage), script = value.productionRead!.script!;
    script.acceptedScript = null;
    script.acceptedReviewState.status = state === "retained" || state === "reopened" ? state : "missing";
    script.status = state === "retained" ? "candidate_ready" : state;
    if (state === "prepared" || state === "candidate_ready") script.candidate = { status: state === "prepared" ? "prepared" : "ready" } as ScriptCandidate;
    const result = next(value);
    expect(result.text).toContain(wording);
    expect(result.text).toContain("点击左侧「剧本」");
    expect(result.text).not.toContain("剧本时");
    expect(result.text).not.toContain("打开「制作」");
    expect(result.text).not.toContain("分镜与投产整包评审");
    expect(result.action).toBeUndefined();
  });

  it.each([
    ["missing", "分镜方案未确认"], ["prepared", "分镜任务已准备，尚未交付"],
    ["candidate_ready", "分镜候选已交付，尚未确认"], ["stale", "分镜任务的来源已变化"],
    ["retained", "保留的已确认分镜不能用于当前制作"],
  ] as const)("names source-storyboard's verified %s state", (state, wording) => {
    const value = input(activePage), board = value.productionRead!.storyboardSource!;
    board.acceptedReview = null;
    board.acceptedReviewState.status = state === "retained" ? "retained" : "missing";
    board.status = state === "retained" ? "candidate_ready" : state;
    if (state === "prepared" || state === "candidate_ready") board.candidate = { status: state === "prepared" ? "prepared" : "ready" } as StoryboardReviewCandidate;
    const result = next(value);
    expect(result.text).toContain(wording);
    expect(result.text).toContain("点击左侧「分镜评审」");
    expect(result.text).not.toContain("分镜与投产整包评审");
  });

  it("keeps pending and failed reads unknown and names the actual retry control", () => {
    const value = input(activePage);
    expect(next({ ...value, productionRead: undefined }).text).toContain("正在核对剧本、分镜与投产状态");
    value.productionRead!.errors.push("剧本暂不可读取");
    const result = next(value);
    expect(result.text).toContain("状态暂不能核实");
    expect(result.text).toContain("点击「重新核对制作来源」");
    expect(result.text).not.toContain("剧本未确认");
    expect(Boolean(result.action)).toBe(activePage === "graph");
  });

  it.each(["map", "script"])("rejects mismatched %s reads without guessing acceptance", mismatch => {
    const value = input(activePage);
    if (mismatch === "map") value.productionRead!.script!.acceptedScript!.binding.sectionMapRevision++;
    else value.productionRead!.storyboardSource!.acceptedReview!.binding.scriptContentHash = "other script";
    expect(next(value).text).toContain("制作来源版本不一致");
    expect(next(value).text).toContain("重新核对制作来源");
  });

  it("uses accepted review authority across a canonical graph/Bible rebind", () => {
    const value = input(activePage);
    value.productionRead!.script!.acceptedScript!.binding.graphRevision = 1;
    value.productionRead!.storyboardSource!.acceptedReview!.binding.graphRevision = 1;
    expect(next(value).text).toContain("剧本与分镜已确认");
    expect(next(value).text).toContain("点击「分镜与投产整包评审」");
  });

  it("only names shot/media controls when installed identities match", () => {
    const value = input(activePage), read = value.productionRead!;
    const cut = { sectionId: "opening", episode: 1, sceneIndex: 1, shotId: "cut", cutIndex: 1, seconds: 5,
      source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: 1 } };
    read.bridge!.installation = installedProduction({ inputs: { scriptRevision: 1, scriptContentHash: "script" },
      scenes: [{ sectionId: "opening", episode: 1, sceneIndex: 1, sceneId: "scene", title: "S01", cutCount: 1 }], cuts: [cut] });
    value.project.stageRevisions.storyboard = 1;
    value.project.storyboard.shots = [{ ...value.project.storyboard.shots[0], id: "cut", sceneId: "scene", durationUnits: 5000 }];
    expect(next(value).text).toContain("点击该节点镜头下的「镜头审核与媒体」");
    expect(next(value).text).toContain("不代表影片已完成");
    value.project.storyboard.shots[0].durationUnits = 6000;
    expect(next(value).text).not.toContain("镜头审核与媒体");
    expect(next(value).text).toContain("需核对");
    read.bridge!.installation.status = "outdated";
    expect(next(value).text).toContain("旧镜头与媒体保留");
  });
});
