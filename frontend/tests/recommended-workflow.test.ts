import { describe, expect, it } from "vitest";
import { demoProject } from "../src/demo";
import type { AcceptedSectionMapRevision, BranchTaskState, SectionMap, ServerStageName, SourceOutlineReviewState, StageHead, WorkspaceProject } from "../src/types";
import { branchSuggestionBasis, buildRecommendedWorkflow, type RecommendedWorkflowInput } from "../src/app/workspace/recommendedWorkflow";
import { creativeWorkflowStepReference, creativeWorkflowSteps } from "../src/creative-workflow-steps";
import { graphDraftFixture } from "./graph-workbench-fixture";
import { workflowProductionFixture } from "./workflow-production-fixture";

const project = { ...demoProject, id: "project", revision: 4 } as WorkspaceProject;
const base: RecommendedWorkflowInput = {
  activePage: "brief", activeHash: "", project, stageHeads: {}, sourceReviewStatus: "ready", sourceReview: null,
  branchTaskStatus: "idle", branchTask: null, workspaceAvailable: true, projectPending: false, sourceDraftDirty: false,
  branchTaskBusy: false,
  branchTaskBlocked: false,
  productionRead: undefined,
  scriptRead: undefined,
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

function appliedGraphInput(activePage: "creator" | "graph" = "creator"): RecommendedWorkflowInput {
  const mapping = graphDraftFixture().mapping as SectionMap;
  mapping.sections[0].title = "离开前，最后点亮";
  mapping.sections.reverse(); // The guide must follow the start node, not section storage order.
  const input = { ...base, activePage, branchDraft: { ...base.branchDraft, complete: true },
    sourceReview: acceptedReview({ sectionMapStatus: "current",
      acceptedSectionMap: { revision: 5, sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", contentHash: "map-hash", mapping } as AcceptedSectionMapRevision,
      graphAdmission: { status: "current", sourceRevision: 2, outlineRevision: 3, outlineContentHash: "outline-hash", sectionMapRevision: 5, sectionMapContentHash: "map-hash", graphRevision: 8, graphContentHash: "graph-hash" } as never }),
    stageHeads: { story_graph: head("story_graph", 8, "graph-hash") } };
  return { ...input, productionRead: workflowProductionFixture(input.sourceReview) };
}

describe("recommended creative workflow", () => {
  it("shares the six step labels and one-based references with node impact guidance", () => {
    const model = buildRecommendedWorkflow(base)!;
    expect(model.steps.map(({ id, label }) => ({ id, label }))).toEqual(creativeWorkflowSteps);
    expect(model.steps.map(step => creativeWorkflowStepReference(step.id))).toEqual([
      "第1/6步「项目简报」", "第2/6步「来源与大纲」", "第3/6步「剧情分支」",
      "第4/6步「剧情图编辑」", "第5/6步「制作与审阅」", "第6/6步「播放」",
    ]);
  });
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
    expect(buildRecommendedWorkflow({ ...base, activePage: "graph" })?.currentStep).toBe("creator");
    expect(buildRecommendedWorkflow({ ...base, activePage: "creator" })?.currentStep).toBe("creator");
    expect(buildRecommendedWorkflow({ ...base, activePage: "characters" })?.currentStep).toBe("production");
    expect(buildRecommendedWorkflow({ ...base, activePage: "trace" })).toBeNull();
  });

  it.each([["creator", "创作视图"], ["graph", "专业视图"]] as const)("keeps %s in the shared graph step without claiming completion", (activePage, viewLabel) => {
    const input = { ...base, activePage, sourceReview: acceptedReview(), branchTaskBlocked: true, branchDraft: { ...base.branchDraft, complete: true } };
    const model = buildRecommendedWorkflow(input)!;
    expect(model.currentStep).toBe("creator");
    expect(model.currentStepLabel).toBe("剧情图编辑");
    expect(model.steps.findIndex(step => step.id === model.currentStep)).toBe(3);
    expect(model.currentViewLabel).toBe(viewLabel);
    expect(model.steps[3].status).toBe("正在查看");
    expect(model.nextText).toContain("共用同一剧情图");
    expect(model.nextText).toContain("尚未与已确认分支匹配");
    expect(model.steps[2].status).not.toContain("已应用");

    const failed = buildRecommendedWorkflow({ ...input, sourceReviewStatus: "failed" })!;
    expect(failed.currentStep).toBe(model.currentStep);
    expect(failed.currentViewLabel).toBe(viewLabel);
    expect(failed.nextText).toContain("无法核实");
    expect(failed.action).toBeUndefined();
    const readOnly = buildRecommendedWorkflow({ ...input, readOnly: true })!;
    expect(readOnly.currentStep).toBe(model.currentStep);
    expect(readOnly.steps.every(step => step.status === "只读快照")).toBe(true);
    expect(readOnly.action).toBeUndefined();
    expect(buildRecommendedWorkflow({ ...base, activePage: "source", sourceReview: acceptedReview() })?.currentViewLabel).toBeUndefined();
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
    for (const activePage of ["creator", "graph"] as const) {
      const input = { ...base, activePage, sourceReview: review, branchDraft: { ...base.branchDraft, complete: true }, stageHeads: { story_graph: head("story_graph", 8, "graph-hash") } };
      const graphView = buildRecommendedWorkflow(input)!;
      expect(graphView.currentStepLabel).toBe("剧情图编辑");
      expect(graphView.steps[2].status).toBe("已应用到路线 r8");
      expect(graphView.nextText).not.toContain("尚未与已确认分支匹配");
      const mismatched = buildRecommendedWorkflow({ ...input, stageHeads: { story_graph: head("story_graph", 8, "different-hash") } })!;
      expect(mismatched.currentStep).toBe(graphView.currentStep);
      expect(mismatched.nextText).toContain("尚未应用到当前故事路线");
      expect(mismatched.statusText).toBeUndefined();
      expect(mismatched.steps[2].status).not.toContain("已应用");
    }
  });

  it.each(["creator", "graph"] as const)("shows applied status and the real production entry on %s", activePage => {
    const model = buildRecommendedWorkflow(appliedGraphInput(activePage))!;
    expect(model.currentStep).toBe("creator");
    expect(model.statusText).toBe("当前图内容已应用到故事路线。");
    expect(model.nextText).toContain("选择「离开前，最后点亮」，打开「制作」标签");
    expect(model.nextText).toContain("剧本与分镜已确认，尚未建立当前制作内容");
    expect(model.nextText).toContain("点击「分镜与投产整包评审」");
    expect(model.nextText).toContain("第5/6步「制作与审阅」");
    expect(model.nextText).not.toContain("继续第5/6步");
    expect(model.nextText.includes("点击「返回创作工作台」")).toBe(activePage === "graph");
    expect(model.action).toEqual(activePage === "graph" ? { kind: "navigate", label: "返回创作工作台", route: { stage: "creator" } } : undefined);
  });

  it.each(["creator", "graph"] as const)("leaves script confirmation to its owner, not canonical stage heads on %s", activePage => {
    const input = appliedGraphInput(activePage);
    const model = buildRecommendedWorkflow(input)!;
    const withStages = buildRecommendedWorkflow({ ...input, stageHeads: { ...input.stageHeads,
      scene_beats: head("scene_beats", 2, "scenes"), storyboard: head("storyboard", 3, "shots") } })!;
    expect(withStages.nextText).toBe(model.nextText);
    expect(model.nextText).toContain("剧本与分镜已确认");
    const unknown = buildRecommendedWorkflow({ ...input, productionRead: undefined })!;
    expect(unknown.nextText).toContain("正在核对剧本、分镜与投产状态");
    expect(unknown.nextText).not.toContain("剧本未确认");
  });

  it.each([
    { status: "loading" as const, wording: "正在读取当前图草稿" },
    { status: "failed" as const, wording: "无法读取当前图草稿" },
    { busy: true, wording: "正在处理图草稿" },
    { stale: true, wording: "在当前版本恢复为新草稿" },
    { blocked: true, wording: "当前图暂不可编辑" },
    { pendingFields: true, wording: "待提交的字段输入" },
    { dirty: true, wording: "点击「确认图内容」" },
    { complete: false, wording: "先补全节点、选项与连接" },
    { dirty: true, complete: false, wording: "先补全节点、选项与连接" },
  ])("does not invite production for an unready graph draft: $wording", ({ wording, ...state }) => {
    for (const activePage of ["creator", "graph"] as const) {
      const input = appliedGraphInput(activePage);
      const model = buildRecommendedWorkflow({ ...input, branchDraft: { ...input.branchDraft, ...state } })!;
      expect(model.nextText).toContain(wording);
      expect(model.statusText).toBeUndefined();
      expect(model.nextText).not.toContain("打开「制作」标签");
      expect(model.action).toBeUndefined();
    }
  });

  it("follows reachable routes past control-only nodes, not an unconnected filmed section", () => {
    const input = appliedGraphInput(), mapping = input.sourceReview!.acceptedSectionMap!.mapping;
    mapping.sections.find(section => section.sectionId === "opening")!.footageMode = "route_only";
    mapping.sections.unshift({ sectionId: "detached", title: "不在路线中的影片", summary: "保留草稿", ending: false, footageMode: "footage" });
    mapping.topology.nodes.push({ id: "detached", kind: "scene" });
    const model = buildRecommendedWorkflow(input)!;
    expect(model.nextText).toContain("选择「ending」");
    expect(model.nextText).not.toContain("不在路线中的影片");
  });

  it.each(["creator", "graph"] as const)("avoids an ambiguous filming target when node titles repeat on %s", activePage => {
    const input = appliedGraphInput(activePage), mapping = input.sourceReview!.acceptedSectionMap!.mapping;
    const opening = mapping.sections.find(section => section.sectionId === mapping.topology.startNodeId)!;
    mapping.sections.find(section => section.ending)!.title = ` ${opening.title} `;
    const model = buildRecommendedWorkflow(input)!;
    expect(model.statusText).toBe("当前图内容已应用到故事路线。");
    expect(model.nextText).toContain("选择当前路线中需要拍摄的节点，打开「制作」标签");
    expect(model.nextText).not.toContain(`选择「${opening.title}」`);
    expect(model.nextText).toContain("第5/6步「制作与审阅」");
  });

  it("does not claim production is complete when there is no reachable filmed node", () => {
    const input = appliedGraphInput(), mapping = input.sourceReview!.acceptedSectionMap!.mapping;
    mapping.sections.forEach(section => { section.footageMode = "route_only"; });
    mapping.topology.edges.push({ ...mapping.topology.edges[0], id: "cycle", sourceNodeId: "ending", targetNodeId: "opening" });
    const model = buildRecommendedWorkflow(input)!;
    expect(model.statusText).toBe("当前图内容已应用到故事路线。");
    expect(model.nextText).toContain("不能据此视为制作已完成");
    expect(model.nextText).not.toContain("打开「制作」标签");
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

  describe.each(["source", "art", "script", "storyboard-review"])("retained Source draft on #%s", activeHash => {
    it.each(["loading", "failed"] as const)("prioritizes %s reads over dirty draft guidance", sourceReviewStatus => {
      const model = buildRecommendedWorkflow({ ...base, activePage: "source", activeHash, sourceReviewStatus, sourceDraftDirty: true })!;
      expect(model.nextText).toContain(sourceReviewStatus === "loading" ? "正在读取来源" : "先在本页刷新读取");
      expect(model.nextText).not.toContain("确认或放弃修改");
      expect(model.action).toBeUndefined();
    });
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
