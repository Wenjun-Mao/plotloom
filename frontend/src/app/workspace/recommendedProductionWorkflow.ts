import { creativeWorkflowStepReference } from "../../creative-workflow-steps";
import { currentBridgeCut } from "../../production-bridge-handoff";
import { installedCutMatches, nodeProductionScenes } from "../../features/graph/productionProjection";
import type { ScriptBinding } from "../../types";
import type { RecommendedWorkflowInput, WorkflowRecommendation } from "./recommendedWorkflow";

function matchesAcceptedMap(binding: ScriptBinding, input: RecommendedWorkflowInput): boolean {
  const admission = input.sourceReview?.graphAdmission;
  // Production may rebind canonical graph/Bible identities without changing the
  // authored route. Accepted review currentness owns that distinction.
  return Boolean(admission && binding.sourceRevision === admission.sourceRevision
    && binding.outlineRevision === admission.outlineRevision && binding.outlineContentHash === admission.outlineContentHash
    && binding.sectionMapRevision === admission.sectionMapRevision && binding.sectionMapContentHash === admission.sectionMapContentHash);
}

/** Accepted review authority and exact source identities, never canonical-head guesses. */
export function appliedProductionRecommendation(input: RecommendedWorkflowInput, sectionId: string, target: string): WorkflowRecommendation {
  const data = input.productionRead;
  const step = creativeWorkflowStepReference("production");
  const inspection = (text: string): WorkflowRecommendation => ({
    text: `${input.activePage === "graph" ? "点击「返回创作工作台」，再" : ""}选择${target}，打开「制作」标签，${text}（${step}）。`,
    action: input.activePage === "graph" ? { kind: "navigate", label: "返回创作工作台", route: { stage: "creator" } } : undefined,
  });
  const sidebar = (state: string, label: "剧本" | "分镜评审", instruction: string): WorkflowRecommendation => ({
    text: `${state}。点击左侧「${label}」，${instruction}（${step}）。`,
  });
  if (!data) return { text: "正在核对剧本、分镜与投产状态；读取完成后显示具体下一步。" };
  if (data.errors.length || !data.script || !data.storyboardSource || !data.bridge) {
    return inspection("制作来源读取失败，状态暂不能核实；点击「重新核对制作来源」");
  }
  const script = data.script, accepted = script.acceptedScript, scriptState = script.acceptedReviewState;
  if (scriptState.status !== "current" || !accepted) {
    if (scriptState.status === "reopened") return sidebar("剧本修订尚未完成", "剧本", "保存或明确舍弃章节修改");
    if (scriptState.status === "retained") return sidebar("保留的已确认剧本不能用于当前制作", "剧本", "按来源与审阅提示处理，旧剧本仍保留");
    if (script.status === "stale") return sidebar("剧本任务的来源已变化", "剧本", "按来源提示更新任务并重新审阅");
    if (script.candidate?.status === "ready") return sidebar("剧本候选已交付，尚未确认", "剧本", "审阅候选后点击「确认使用此剧本」");
    if (script.candidate?.status === "prepared") return sidebar("剧本任务已准备，尚未交付", "剧本", "查看任务区的发送与结果检查控件");
    return sidebar("剧本未确认", "剧本", "进入剧本准备与审阅");
  }
  if (scriptState.staleReasons.length || !matchesAcceptedMap(accepted.binding, input)) {
    return inspection("制作来源版本不一致，暂不能继续；点击「重新核对制作来源」");
  }
  const storyboard = data.storyboardSource, board = storyboard.acceptedReview, boardState = storyboard.acceptedReviewState;
  if (boardState.status !== "current" || !board) {
    if (boardState.status === "retained") return sidebar("保留的已确认分镜不能用于当前制作", "分镜评审", "按来源与审阅提示处理，旧分镜仍保留");
    if (storyboard.status === "stale") return sidebar("分镜任务的来源已变化", "分镜评审", "按来源提示更新任务并重新审阅");
    if (storyboard.candidate?.status === "ready") return sidebar("分镜候选已交付，尚未确认", "分镜评审", "审阅候选后点击「确认此分镜评审方案」");
    if (storyboard.candidate?.status === "prepared") return sidebar("分镜任务已准备，尚未交付", "分镜评审", "查看任务区的发送与结果检查控件");
    return sidebar("剧本已确认，分镜方案未确认", "分镜评审", "进入分镜准备与审阅");
  }
  if (boardState.staleReasons.length || board.binding.scriptRevision !== accepted.revision
    || board.binding.scriptContentHash !== accepted.contentHash || !matchesAcceptedMap(board.binding, input)) {
    return inspection("制作来源版本不一致，暂不能继续；点击「重新核对制作来源」");
  }
  const bridge = data.bridge, installation = bridge.installation;
  if (installation?.status === "current" && installation.staleReasons.length === 0) {
    try {
      const scenes = nodeProductionScenes(installation, accepted, sectionId);
      const bound = scenes.some(scene => scene.cuts.some(cut => currentBridgeCut(bridge, input.project.stageRevisions.storyboard, cut.shotId)
        && installedCutMatches(cut, scene.sceneId, input.project.storyboard.shots.find(shot => shot.id === cut.shotId))));
      if (bound) return inspection("点击该节点镜头下的「镜头审核与媒体」，继续镜头与媒体审阅；不代表影片已完成");
    } catch { /* Retained mismatched evidence remains with the package-review owner. */ }
    return inspection("当前节点的投产镜头与制作版本需核对；点击「分镜与投产整包评审」");
  }
  const state = installation ? "已有制作内容需要重新核对，旧镜头与媒体保留"
    : bridge.status === "ready" ? "投产提案待审阅与确认" : "剧本与分镜已确认，尚未建立当前制作内容";
  return inspection(`${state}；点击「分镜与投产整包评审」`);
}
