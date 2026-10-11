import { describe, expect, it } from "vitest";
import { demoProject } from "../src/demo";
import type { AcceptedSectionMapRevision, BranchTaskState, ServerStageName, SourceOutlineReviewState, StageHead, WorkspaceProject } from "../src/types";
import { branchSuggestionBasis, buildRecommendedWorkflow, type RecommendedWorkflowInput } from "../src/app/workspace/recommendedWorkflow";

const project = { ...demoProject, id: "project", revision: 4 } as WorkspaceProject;
const base: RecommendedWorkflowInput = {
  activePage: "brief", activeHash: "", project, stageHeads: {}, sourceReviewStatus: "ready", sourceReview: null,
  branchTaskStatus: "idle", branchTask: null, workspaceAvailable: true, projectPending: false, sourceDraftDirty: false,
  branchTaskBusy: false,
  branchTaskBlocked: false,
  branchDraft: { status: "ready", dirty: false, complete: false, stale: false, busy: false, blocked: false },
  readOnly: false, actionDisabled: false, playHref: "?project=project&view=play",
};

function acceptedReview(overrides: Partial<SourceOutlineReviewState> = {}): SourceOutlineReviewState {
  return {
    source: { revision: 2 } as never,
    candidate: null,
    acceptedOutline: { revision: 3, sourceRevision: 2, contentHash: "outline-hash" } as never,
    outlineStatus: "accepted",
    acceptedSectionMap: null,
    sectionMapStatus: "missing",
    sectionMapStaleReasons: [],
    graphAdmission: null,
    ...overrides,
  };
}

function head(stage: ServerStageName, revision: number, contentHash: string): StageHead {
  return { stage, revision, status: "ready", entityRevisionId: null, contentHash, schemaVersion: 2, inputRevisions: {}, staleReasons: [], updatedAt: "2026-10-10T00:00:00Z" };
}

describe("recommended creative workflow", () => {
  const branchInput = (): RecommendedWorkflowInput => ({ ...base, activePage: "source", sourceReview: acceptedReview(), branchTaskStatus: "ready" });
  const branchTask = (status: string): BranchTaskState => ({
    candidate: { jobId: "branch-job", status, suggestion: status === "ready" ? { nodes: [], choices: [], joins: [], clarifications: [] } : null, reportAvailable: false },
    staleReasons: [], plannedTopology: null, infeasibleReason: null,
  });

  it("names the import button for a delivered suggestion on the actual branches route", () => {
    const model = buildRecommendedWorkflow({ ...branchInput(), branchTask: branchTask("ready") })!;
    expect(model.currentStep).toBe("branches");
    expect(model.nextText).toContain("点击「带入可编辑草稿」");
    expect(model.nextText).toContain("如果满意");
    expect(model.action).toBeUndefined();
  });

  it("advances an imported complete draft to its save control, not another import", () => {
    const input = { ...branchInput(), branchTask: branchTask("ready"), branchDraft: { ...base.branchDraft, dirty: true, complete: true } };
    const model = buildRecommendedWorkflow(input)!;
    expect(model.nextText).toContain("点击「确认并保存故事分支」");
    expect(model.nextText).not.toContain("带入可编辑草稿");
    expect(model.steps.find(step => step.id === "branches")?.status).toBe("草稿待确认保存");
    expect(model.action).toBeUndefined();
    const revision = buildRecommendedWorkflow({ ...input, sourceReview: acceptedReview({ acceptedSectionMap: { revision: 2 } as AcceptedSectionMapRevision }) })!;
    expect(revision.nextText).toContain("点击「保存修改」");
  });

  it("asks for missing fields before saving an incomplete hand-authored draft", () => {
    const model = buildRecommendedWorkflow({ ...branchInput(), branchDraft: { ...base.branchDraft, dirty: true } })!;
    expect(model.nextText).toContain("先补全");
    expect(model.nextText).toContain("尚不能确认保存");
  });

  it.each([
    ["loading", null, "正在读取剧情分支建议任务"],
    ["failed", null, "重试读取建议"],
    ["ready", null, "准备剧情分支建议"],
    ["ready", "prepared", "发送给文字创作助手"],
    ["ready", "cancelled", "准备剧情分支建议"],
  ] as const)("guides %s task reads with candidate %s", (status, candidate, wording) => {
    const model = buildRecommendedWorkflow({ ...branchInput(), branchTaskStatus: status, branchTask: candidate ? branchTask(candidate) : null })!;
    expect(model.nextText).toContain(wording);
    expect(model.nextText).not.toContain("点击「带入可编辑草稿」");
  });

  it.each([
    { status: "loading" as const, wording: "正在读取当前分支草稿" },
    { status: "failed" as const, wording: "无法读取当前分支草稿" },
    { busy: true, wording: "正在处理分支草稿" },
    { stale: true, wording: "在当前版本恢复为新草稿" },
    { blocked: true, wording: "当前分支暂不可编辑" },
  ])("does not recommend import when draft authority is unavailable: $wording", ({ wording, ...state }) => {
    const model = buildRecommendedWorkflow({ ...branchInput(), branchTask: branchTask("ready"), branchDraft: { ...base.branchDraft, ...state } })!;
    expect(model.nextText).toContain(wording);
    expect(model.nextText).not.toContain("点击「带入可编辑草稿」");
    expect(model.action).toBeUndefined();
  });

  it("keeps stale, unavailable and pending suggestions out of the import path", () => {
    const input = { ...branchInput(), branchTask: { ...branchTask("ready"), staleReasons: ["Brief changed"] } };
    expect(buildRecommendedWorkflow(input)!.nextText).toContain("不要带入旧建议");
    expect(buildRecommendedWorkflow({ ...branchInput(), branchTask: branchTask("ready"), branchTaskBusy: true })!.nextText).toContain("正在处理分支建议任务");
    expect(buildRecommendedWorkflow({ ...branchInput(), branchTask: branchTask("ready"), branchTaskBlocked: true })!.nextText).toContain("当前分支暂不可编辑");
    expect(buildRecommendedWorkflow({ ...branchInput(), branchTask: { ...branchTask("ready"), infeasibleReason: "Budget too small" } })!.nextText).toContain("调整项目简报");
    expect(buildRecommendedWorkflow({ ...branchInput(), branchTask: { ...branchTask("ready"), candidate: { ...branchTask("ready").candidate!, suggestion: null } } })!.nextText).toContain("内容未能读入");
  });
  it("maps primary routes and source subphases to their workflow steps", () => {
    expect(buildRecommendedWorkflow(base)?.currentStep).toBe("brief");
    expect(buildRecommendedWorkflow({ ...base, activePage: "source", sourceReview: acceptedReview() })?.currentStep).toBe("branches");
    expect(buildRecommendedWorkflow({ ...base, activePage: "source", activeHash: "art" })?.currentStep).toBe("production");
    expect(buildRecommendedWorkflow({ ...base, activePage: "source", activeHash: "script" })?.currentStep).toBe("production");
    expect(buildRecommendedWorkflow({ ...base, activePage: "graph" })?.currentStep).toBe("branches");
    expect(buildRecommendedWorkflow({ ...base, activePage: "creator" })?.currentStep).toBe("creator");
    expect(buildRecommendedWorkflow({ ...base, activePage: "characters" })?.currentStep).toBe("production");
    expect(buildRecommendedWorkflow({ ...base, activePage: "trace" })).toBeNull();
  });

  it("does not treat a retained outline as current for a newer source", () => {
    const review = acceptedReview({ source: { revision: 4 } as never });
    const model = buildRecommendedWorkflow({ ...base, activePage: "source", sourceReview: review })!;
    expect(model.currentStep).toBe("source");
    expect(model.steps.find(step => step.id === "source")?.status).toContain("旧大纲");
    expect(model.steps.find(step => step.id === "branches")?.status).toBe("等待当前大纲");
  });

  it("requires matching map and graph identities before reporting an applied branch", () => {
    const map = { revision: 5, sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", contentHash: "map-hash" } as AcceptedSectionMapRevision;
    const admission = { status: "current", sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", sectionMapRevision: 5, sectionMapContentHash: "map-hash", graphRevision: 8, graphContentHash: "graph-hash" } as never;
    const review = acceptedReview({ acceptedSectionMap: map, sectionMapStatus: "current", graphAdmission: admission });
    const valid = buildRecommendedWorkflow({ ...base, activePage: "source", sourceReview: review, stageHeads: { story_graph: head("story_graph", 8, "graph-hash") } })!;
    expect(valid.steps.find(step => step.id === "branches")?.status).toBe("已应用到路线 r8");
    expect(valid.action).toEqual({ kind: "navigate", label: "进入创作工作台", route: { stage: "creator" } });

    const changedGraph = buildRecommendedWorkflow({ ...base, activePage: "source", sourceReview: review, stageHeads: { story_graph: head("story_graph", 8, "different-hash") } })!;
    expect(changedGraph.steps.find(step => step.id === "branches")?.status).toBe("分支方案 r5 已确认");
    expect(changedGraph.nextText).toContain("应用到故事路线");
  });

  it("keeps branch-task observations bound to the brief and accepted revisions", () => {
    const review = acceptedReview();
    const basis = branchSuggestionBasis(review.acceptedOutline, review.acceptedSectionMap, true, JSON.stringify(project.brief));
    expect(basis).toBe("map:3:outline-hash:0:true:" + JSON.stringify(project.brief));
    expect(branchSuggestionBasis(review.acceptedOutline, review.acceptedSectionMap, true, "changed-brief")).not.toBe(basis);
  });

  it("reports unsaved projects without inventing in-progress reads", () => {
    const model = buildRecommendedWorkflow({
      ...base,
      activePage: "source",
      project: { ...project, id: "", revision: 0 },
      sourceReviewStatus: "idle",
      sourceReview: null,
      workspaceAvailable: false,
    })!;
    expect(model.steps.find(step => step.id === "brief")?.status).toBe("尚未保存");
    expect(model.steps.find(step => step.id === "source")?.status).toBe("项目未保存");
    expect(model.steps.find(step => step.id === "branches")?.status).toBe("项目未保存");
    expect(model.nextText).toContain("项目尚未保存");
    expect(model.nextText).not.toContain("正在读取");
  });

  it("hides route actions while the source editor holds an unsaved local draft", () => {
    const map = { revision: 5, sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", contentHash: "map-hash" } as AcceptedSectionMapRevision;
    const admission = { status: "current", sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", sectionMapRevision: 5, sectionMapContentHash: "map-hash", graphRevision: 8, graphContentHash: "graph-hash" } as never;
    const model = buildRecommendedWorkflow({
      ...base,
      activePage: "source",
      sourceReview: acceptedReview({ acceptedSectionMap: map, sectionMapStatus: "current", graphAdmission: admission }),
      stageHeads: { story_graph: head("story_graph", 8, "graph-hash") },
      sourceDraftDirty: true,
    })!;
    expect(model.steps.find(step => step.id === "branches")?.status).toBe("已应用到路线 r8");
    expect(model.nextText).toContain("未保存修改");
    expect(model.action).toBeUndefined();
  });

  it("keeps a pending project load separate from an unsaved blank workspace", () => {
    const model = buildRecommendedWorkflow({ ...base, project: { ...project, id: "", revision: 0 }, projectPending: true, workspaceAvailable: false })!;
    expect(model.steps.find(step => step.id === "brief")?.status).toBe("无法核实");
    expect(model.nextText).toContain("正在读取当前项目版本");
  });

  it("distinguishes interactive playback checks from a static report", () => {
    const model = buildRecommendedWorkflow({ ...base, activePage: "storyboard" })!;
    expect(model.currentStep).toBe("production");
    expect(model.steps.find(step => step.id === "play")?.status).toBe("可检查播放器条件");
    expect(model.nextText).toContain("静态报告只供阅读");
    expect(model.action).toEqual({ kind: "play", label: "检查交互式播放", href: base.playHref });
  });

  it("avoids readiness and actions while source reads fail or the project is read-only", () => {
    const failed = buildRecommendedWorkflow({ ...base, activePage: "source", sourceReviewStatus: "failed" })!;
    expect(failed.steps.find(step => step.id === "source")?.status).toBe("无法核实");
    expect(failed.nextText).toContain("无法核实");
    const archived = buildRecommendedWorkflow({ ...base, activePage: "source", project: { ...project, lifecycleStatus: "archived" }, readOnly: true })!;
    expect(archived.steps.every(step => step.status === "只读快照")).toBe(true);
    expect(archived.action).toBeUndefined();
  });
});
