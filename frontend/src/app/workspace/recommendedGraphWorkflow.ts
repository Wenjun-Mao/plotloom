import type { SectionMap, StorySection } from "../../types";
import { creativeWorkflowStepReference } from "../../creative-workflow-steps";
import type { RecommendedWorkflowInput, WorkflowRecommendation } from "./recommendedWorkflow";

/** Follow the accepted route, not section-array order or the currently selected node. */
function firstFilmedSection(mapping: SectionMap | undefined): StorySection | undefined {
  if (!mapping) return undefined;
  const pending = [mapping.topology.startNodeId], visited = new Set<string>();
  for (let index = 0; index < pending.length; index++) {
    const id = pending[index];
    if (visited.has(id)) continue;
    visited.add(id);
    const section = mapping.sections.find(section => section.sectionId === id);
    if (section?.footageMode === "footage" && section.title.trim()) return section;
    pending.push(...mapping.topology.edges.filter(edge => edge.sourceNodeId === id).map(edge => edge.targetNodeId));
  }
  return undefined;
}

/** Advisory projection only; the graph owner still owns edits, confirmation and application. */
export function graphWorkflowRecommendation(input: RecommendedWorkflowInput, confirmed: boolean, applied: boolean): WorkflowRecommendation {
  const draft = input.branchDraft;
  if (draft.status === "loading") return { text: "正在读取当前图草稿；读取完成后再核实确认与应用状态。" };
  if (draft.status === "failed") return { text: "无法读取当前图草稿。请先按本页提示重新读取；暂不能核实当前图是否已应用。" };
  if (draft.busy) return { text: "正在处理图草稿，请等待完成；不要重复确认或应用。" };
  if (draft.stale) return { text: "当前图草稿的依据已变化。请先核对保留内容，再点击「在当前版本恢复为新草稿」。" };
  if (draft.blocked) return { text: "当前图暂不可编辑。请先处理本页显示的限制，再核实确认与应用状态。" };
  if (draft.pendingFields) return { text: "图草稿有待提交的字段输入。完成或修正输入后，点击输入框外提交字段，再确认图内容并应用到故事路线；可用「保存图草稿」暂存未完成输入。" };
  if (draft.dirty || !draft.complete) return { text: draft.complete
    ? "图草稿有修改。审阅无误后点击「确认图内容」，再点击「应用到故事路线」；如需暂存，可使用「保存图草稿」。"
    : "图草稿尚未完成。先补全节点、选项与连接，再确认图内容并应用到故事路线；如需暂存，可使用「保存图草稿」。" };

  const returnToCreator = input.activePage === "graph"
    ? { kind: "navigate" as const, label: "返回创作工作台", route: { stage: "creator" as const } }
    : undefined;
  if (!applied) return {
    text: confirmed
      ? "图内容已确认，尚未应用到当前故事路线。下一步点击「应用到故事路线」，再继续制作与审阅。"
      : "两种视图共用同一剧情图。当前正式路线尚未与已确认分支匹配；可在任一视图编辑草稿，按本页检查后再确认和应用。",
    action: returnToCreator,
  };

  const mapping = input.sourceReview?.acceptedSectionMap?.mapping;
  const section = firstFilmedSection(mapping);
  const target = section && mapping!.sections.filter(item => item.title.trim() === section.title.trim()).length === 1
    ? `「${section.title.trim()}」` : "当前路线中需要拍摄的节点";
  const entry = input.activePage === "graph" ? "点击「返回创作工作台」，再" : "";
  return {
    statusText: "当前图内容已应用到故事路线。",
    text: section
      ? `${entry}选择${target}，打开「制作」标签。尚无当前可用剧本时，点击左侧「剧本」；剧本与分镜确认后，返回「创作工作台」并打开「制作」，点击「分镜与投产整包评审」（${creativeWorkflowStepReference("production")}）。`
      : `${entry}检查当前路线中需要拍摄的节点；仅控制路线的节点无需拍摄，不能据此视为制作已完成。`,
    action: returnToCreator,
  };
}
