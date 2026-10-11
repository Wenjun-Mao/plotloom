import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { demoProject } from "../src/demo";
import type { SectionMap, SourceOutlineReviewState, StageHead } from "../src/types";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { WorkspaceWorkflowGuide } from "../src/app/workspace/WorkspaceWorkflowGuide";
import { WorkspaceProductionContext } from "../src/features/graph/WorkspaceProductionContext";
import type { RecommendedWorkflowInput } from "../src/app/workspace/recommendedWorkflow";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import { workflowProductionFixture } from "./workflow-production-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: ReturnType<typeof createRoot>;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

const draft = graphDraftFixture();
const source: SourceOutlineReviewState = {
  source: { revision: 1 } as never, candidate: null, acceptedOutline: { revision: 1, sourceRevision: 1, contentHash: "outline" } as never,
  outlineStatus: "accepted", sectionMapStatus: "current", sectionMapStaleReasons: [],
  acceptedSectionMap: { revision: 1, sourceRevision: 1, outlineRevision: 1, outlineContentHash: "outline", contentHash: "map", mapping: structuredClone(draft.mapping) as SectionMap } as never,
  graphAdmission: { status: "current", sourceRevision: 1, outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "map", graphRevision: 1, graphContentHash: "graph" } as never,
};
const input: Omit<RecommendedWorkflowInput, "branchDraft" | "productionRead"> = {
  activePage: "creator", activeHash: "", project: { ...demoProject, id: "project", revision: 1 },
  stageHeads: { story_graph: { revision: 1, status: "ready", contentHash: "graph" } as StageHead },
  sourceReviewStatus: "ready", sourceReview: source, branchTaskStatus: "idle", branchTask: null,
  branchTaskBusy: false, branchTaskBlocked: false, workspaceAvailable: true, projectPending: false,
  sourceDraftDirty: false, readOnly: false, actionDisabled: false, playHref: "",
};

it.each(["matching", "changed mapping", "pending field buffer", "failed read"])("observes the graph owner before offering production: %s", async state => {
  const nextDraft = structuredClone(draft);
  if (state === "changed mapping") nextDraft.mapping.sections[0].title = "Unconfirmed opening";
  if (state === "pending field buffer") nextDraft.fieldBuffers["edge-effects"] = "invalid unsent value";
  const owner = graphControllerFixture({ draft: nextDraft, readStatus: state === "failed read" ? "failed" : "ready",
    state: { bindingHash: draft.bindingHash, baseCanonicalRevision: 1, draft: null, initialPayload: draft, readOnlyReason: null } });
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner },
    createElement(WorkspaceProductionContext.Provider, { value: { data: workflowProductionFixture(source), retry: vi.fn() } },
      createElement(WorkspaceWorkflowGuide, { input, onNavigate: vi.fn() })))));
  const status = host.querySelector('[role="status"]');
  if (state === "matching") {
    expect(status?.textContent).toBe("当前状态：当前图内容已应用到故事路线。");
    expect(host.textContent).toContain("选择「opening」，打开「制作」标签");
    expect(host.textContent).toContain("剧本与分镜已确认");
    expect(host.textContent).toContain("点击「分镜与投产整包评审」（第5/6步「制作与审阅」）");
  } else {
    expect(status).toBeNull();
    expect(host.textContent).not.toContain("打开「制作」标签");
    expect(host.textContent).toContain(state === "failed read" ? "无法读取当前图草稿" : state === "pending field buffer" ? "待提交的字段输入" : "点击「确认图内容」");
    if (state === "pending field buffer") {
      expect(host.textContent).toContain("点击输入框外提交字段");
      expect(host.textContent).not.toContain("先补全节点、选项与连接");
    }
  }
  expect(owner.saveDraft).not.toHaveBeenCalled();
  expect(owner.confirmMapping).not.toHaveBeenCalled();
  expect(owner.installMapping).not.toHaveBeenCalled();
  expect(owner.selectNode).not.toHaveBeenCalled();
});
