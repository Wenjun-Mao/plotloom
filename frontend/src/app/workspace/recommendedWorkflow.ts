import type { AcceptedOutlineRevision, AcceptedSectionMapRevision, BranchTaskState, ServerStageName, SourceOutlineReviewState, StageHead, WorkspaceProject } from "../../types";
import type { PageId } from "./contracts";
import { sourceWorkflowTarget } from "./sourceWorkflowNavigation";
import type { WorkspaceSourceReviewStatus } from "./useWorkspaceSourceReview";

export type RecommendedWorkflowStepId = "brief" | "source" | "branches" | "creator" | "production" | "play";
export type RecommendedWorkflowRoute = { stage: PageId; hash?: string };
export type BranchTaskReadObservation = { basis: string; status: "loading" | "ready" | "failed"; value: BranchTaskState | null; busy: boolean; blocked: boolean };
export type RecommendedWorkflowAction =
  | { kind: "navigate"; label: string; route: RecommendedWorkflowRoute }
  | { kind: "play"; label: string; href: string };

export interface RecommendedWorkflowInput {
  activePage: PageId;
  activeHash: string;
  project: WorkspaceProject;
  stageHeads: Partial<Record<ServerStageName, StageHead>>;
  sourceReviewStatus: WorkspaceSourceReviewStatus;
  sourceReview: SourceOutlineReviewState | null;
  branchTaskStatus: "idle" | "loading" | "ready" | "failed";
  branchTask: BranchTaskState | null;
  branchTaskBusy: boolean;
  branchTaskBlocked: boolean;
  branchDraft: { status: "loading" | "ready" | "failed"; dirty: boolean; complete: boolean; stale: boolean; busy: boolean; blocked: boolean };
  workspaceAvailable: boolean;
  projectPending: boolean;
  sourceDraftDirty: boolean;
  readOnly: boolean;
  actionDisabled: boolean;
  playHref: string;
}

export interface RecommendedWorkflowStep {
  id: RecommendedWorkflowStepId;
  label: string;
  status: string;
}

export interface RecommendedWorkflowModel {
  currentStep: RecommendedWorkflowStepId;
  currentStepLabel: string;
  steps: RecommendedWorkflowStep[];
  nextText: string;
  action?: RecommendedWorkflowAction;
}

const steps: Array<{ id: RecommendedWorkflowStepId; label: string }> = [
  { id: "brief", label: "项目简报" },
  { id: "source", label: "来源与大纲" },
  { id: "branches", label: "剧情分支" },
  { id: "creator", label: "创作工作台" },
  { id: "production", label: "制作与审阅" },
  { id: "play", label: "播放" },
];

const primaryPages = new Set<PageId>(["brief", "source", "graph", "creator", "characters", "bible", "beats", "storyboard"]);
const productionStages: ServerStageName[] = ["story_bible", "scene_beats", "storyboard"];
const playbackStages: ServerStageName[] = ["story_graph", "scene_beats", "storyboard"];

export function branchSuggestionBasis(outline: AcceptedOutlineRevision | null, accepted: AcceptedSectionMapRevision | null, outlineCurrent: boolean, briefKey: string): string {
  return outline ? `map:${outline.revision}:${outline.contentHash}:${accepted?.revision ?? 0}:${outlineCurrent}:${briefKey}` : "";
}

function acceptedOutlineIsCurrent(review: SourceOutlineReviewState | null): boolean {
  return Boolean(review?.source && review.outlineStatus === "accepted" && review.acceptedOutline
    && review.acceptedOutline.sourceRevision === review.source.revision);
}

function currentSectionMap(review: SourceOutlineReviewState | null): boolean {
  const source = review?.source, outline = review?.acceptedOutline, map = review?.acceptedSectionMap;
  return Boolean(review?.sectionMapStatus === "current" && source && outline && map
    && acceptedOutlineIsCurrent(review)
    && map.sourceRevision === source.revision
    && map.outlineRevision === outline.revision
    && map.outlineContentHash === outline.contentHash);
}

function currentGraphAdmission(input: RecommendedWorkflowInput): boolean {
  const review = input.sourceReview, map = review?.acceptedSectionMap, admission = review?.graphAdmission;
  const graph = stageState(input, "story_graph");
  return Boolean(currentSectionMap(review) && map && admission?.status === "current"
    && admission.sourceRevision === review!.source!.revision
    && admission.outlineRevision === review!.acceptedOutline!.revision
    && admission.outlineContentHash === review!.acceptedOutline!.contentHash
    && admission.sectionMapRevision === map.revision
    && admission.sectionMapContentHash === map.contentHash
    && graph.status === "ready"
    && graph.head?.revision === admission.graphRevision
    && graph.head.contentHash === admission.graphContentHash);
}

function stageState(input: RecommendedWorkflowInput, stage: ServerStageName): { status: "ready" | "stale" | "missing" | "unknown"; head?: StageHead } {
  if (!input.workspaceAvailable) return { status: "unknown" };
  const head = input.stageHeads[stage];
  if (input.project.staleStages.includes(stage) || head?.status === "stale") return { status: "stale", head };
  if (head?.status === "ready" || (!head && input.project.stageRevisions[stage] > 0)) return { status: "ready", head };
  return { status: "missing", head };
}

function sourcePhase(input: RecommendedWorkflowInput): "source" | "production" | "unknown" {
  const target = sourceWorkflowTarget(input.activeHash) || "source";
  return target === "source" ? "source" : "production";
}

function currentStepFor(input: RecommendedWorkflowInput): RecommendedWorkflowStepId | null {
  if (input.activePage === "brief") return "brief";
  if (input.activePage === "source") {
    if (sourcePhase(input) === "production") return "production";
    if (input.sourceReviewStatus !== "ready") return "source";
    const candidateNeedsOutlineReview = ["prepared", "ready"].includes(input.sourceReview?.candidate?.status ?? "");
    return acceptedOutlineIsCurrent(input.sourceReview) && !candidateNeedsOutlineReview ? "branches" : "source";
  }
  if (input.activePage === "graph") return "branches";
  if (input.activePage === "creator") return "creator";
  if (["characters", "bible", "beats", "storyboard"].includes(input.activePage)) return "production";
  return null;
}

function outlineStatus(input: RecommendedWorkflowInput): string {
  if (!input.workspaceAvailable || input.sourceReviewStatus === "failed") return "无法核实";
  if (input.sourceReviewStatus !== "ready" || !input.sourceReview) return "正在读取";
  const review = input.sourceReview, accepted = review.acceptedOutline;
  const outlineCurrent = acceptedOutlineIsCurrent(review);
  if (review.candidate?.status === "ready") return "候选待审阅";
  if (review.candidate?.status === "prepared") return "任务待交付";
  if (review.outlineStatus === "reopened" || (accepted && !outlineCurrent)) return accepted ? `旧大纲 r${accepted.revision} · 需更新` : "修订已打开";
  if (outlineCurrent && accepted) return `已确认 r${accepted.revision}`;
  if (review.source) return "来源已确认 · 待审阅大纲";
  return "尚未确认来源";
}

function branchStatus(input: RecommendedWorkflowInput): string {
  if (!input.workspaceAvailable || input.sourceReviewStatus === "failed") return "无法核实";
  if (input.sourceReviewStatus !== "ready" || !input.sourceReview) return "正在读取";
  const review = input.sourceReview;
  if (!acceptedOutlineIsCurrent(review)) return "等待当前大纲";
  if (input.activePage === "source" && input.branchDraft.status === "ready" && input.branchDraft.dirty) return "草稿待确认保存";
  if (review.sectionMapStatus === "stale" || review.graphAdmission?.status === "stale") return "需重新检查";
  if (currentGraphAdmission(input)) return `已应用到路线 r${review.graphAdmission!.graphRevision}`;
  if (currentSectionMap(review)) return `分支方案 r${review.acceptedSectionMap!.revision} 已确认`;
  if (input.branchTaskStatus === "loading") return "正在读取建议任务";
  if (input.branchTaskStatus === "failed") return "无法读取建议任务";
  if (input.branchTaskStatus === "ready") {
    if (input.branchTask?.staleReasons.length) return "建议依据需更新";
    if (input.branchTask?.candidate?.status === "ready") return "建议待审阅";
    if (input.branchTask?.candidate?.status === "prepared") return "建议任务待交付";
    if (input.branchTask?.candidate?.status === "cancelled") return "建议已取消";
  }
  return "尚未确认分支";
}

function productionStatus(input: RecommendedWorkflowInput): string {
  const states = productionStages.map(stage => stageState(input, stage).status);
  if (states.includes("unknown")) return "无法核实";
  const stale = states.filter(status => status === "stale").length;
  const ready = states.filter(status => status === "ready").length;
  if (stale) return `${stale} 项需更新`;
  if (ready === 0) return "正式内容待建立";
  if (ready === productionStages.length) return "已有可用版本";
  return `${ready}/${productionStages.length} 项已有版本`;
}

function playbackStatus(input: RecommendedWorkflowInput): string {
  if (!input.workspaceAvailable) return "无法核实";
  if (input.project.lifecycleStatus === "archived" || input.project.archivedAt) return "归档只读";
  const states = playbackStages.map(stage => stageState(input, stage).status);
  if (states.every(status => status === "ready")) return "可检查播放器条件";
  if (states.includes("unknown")) return "无法核实";
  if (states.includes("stale")) return "有内容需更新";
  return "等待路线、场景与分镜";
}

function statusFor(input: RecommendedWorkflowInput, id: RecommendedWorkflowStepId, currentStep: RecommendedWorkflowStepId): string {
  if (input.readOnly) return "只读快照";
  if (!input.project.id && !input.projectPending) return id === "brief" ? "尚未保存" : "项目未保存";
  if (!input.workspaceAvailable) return "无法核实";
  if (id === "brief") return input.project.id && input.project.revision > 0 ? "已有保存版本" : "尚未保存";
  if (id === "source") return outlineStatus(input);
  if (id === "branches") return branchStatus(input);
  if (id === "creator") return id === currentStep ? "正在查看" : "待检查路线";
  if (id === "production") return productionStatus(input);
  return playbackStatus(input);
}

function productionNextText(input: RecommendedWorkflowInput): { text: string; action?: RecommendedWorkflowAction } {
  const target = input.activePage === "source" ? sourceWorkflowTarget(input.activeHash) : undefined;
  if (target === "art") return { text: "审阅当前美术参考；这项确认只属于美术内容，后续剧本和分镜仍需各自检查。" };
  if (target === "script") return { text: "审阅当前剧本中的完整分支与结局；剧本确认不代表分镜或实际播放已通过。" };
  if (target === "storyboard-review") return { text: "继续分镜评审；明确确认投产后，实际媒体仍需单独检查。" };
  if (input.activePage === "characters") return { text: "审阅角色设定；后续美术参考、剧本和分镜仍由各自工作区分别确认。" };
  if (input.activePage === "bible") return { text: "检查故事设定是否与当前故事路线一致，再按需继续场景制作。" };
  if (input.activePage === "beats") return { text: "检查场景节拍与事件顺序；保存后再进入分镜工作台审阅镜头。" };
  const playerStagesReady = playbackStages.every(stage => stageState(input, stage).status === "ready");
  if (input.activePage === "storyboard" && playerStagesReady && input.playHref) {
    return {
      text: "下一步可打开交互式播放器核对当前路线；播放器会再次检查制作状态。静态报告只供阅读，不会等待你的路线选择。",
      action: { kind: "play", label: "检查交互式播放", href: input.playHref },
    };
  }
  return { text: "按当前页面继续制作与审阅；播放器会核对正式故事路线、场景和分镜，内容齐备后再体验交互式路线。" };
}

function nextRecommendation(input: RecommendedWorkflowInput, currentStep: RecommendedWorkflowStepId): { text: string; action?: RecommendedWorkflowAction } {
  const archived = input.project.lifecycleStatus === "archived" || Boolean(input.project.archivedAt);
  if (archived || input.readOnly) return { text: "项目为只读快照，可查看保留内容；恢复项目后再核实当前状态并继续创作。" };
  if (input.projectPending) return { text: "正在读取当前项目版本；读取完成后再核实已有确认和后续步骤。" };
  if (!input.project.id) return currentStep === "brief"
    ? { text: "填写故事梗概并保存项目，再进入来源与大纲。保存不会自动生成或确认内容。" }
    : { text: "当前项目尚未保存。先完成项目简报并保存，再继续来源、大纲与后续创作。" };
  if (!input.workspaceAvailable) return { text: "当前项目版本未能读取。先刷新服务器版本；读取成功后再判断此前确认是否仍适用。" };
  if (input.actionDisabled) return { text: "项目正在读取或处理，请等待状态稳定后再继续；现有草稿和导航保护仍按当前工作台处理。" };
  if (input.activePage === "source" && input.sourceDraftDirty) return { text: "故事内容有未保存修改。先在本页确认或放弃修改，再继续导航。" };
  if (currentStep === "brief") {
    return { text: "检查并保存当前项目简报，再按需返回来源与大纲；简报修改不会自动重建后续内容。", action: { kind: "navigate", label: "打开来源与大纲", route: { stage: "source", hash: "source" } } };
  }
  const sourceNeeded = currentStep === "source" || currentStep === "branches" || currentStep === "creator";
  if (sourceNeeded && input.sourceReviewStatus === "loading") return { text: "正在读取来源、大纲和当前分支版本；读取完成前不沿用旧确认。" };
  if (sourceNeeded && input.sourceReviewStatus === "failed") return { text: "无法核实当前来源与大纲状态。先在本页刷新读取；保留版本不代表当前确认。" };
  if (currentStep === "source") {
    const review = input.sourceReview;
    if (!review?.source) return { text: "先确认故事来源，再准备大纲任务；确认来源不会自动生成大纲。" };
    if (review.candidate?.status === "ready") return { text: "先审阅当前大纲候选并明确确认；阅读候选不会替换已确认内容。" };
    if (review.candidate?.status === "prepared") return { text: "按本页任务区发送或等待大纲交付，再检查候选并决定是否确认。" };
    if (review.outlineStatus === "reopened" || (review.acceptedOutline && !acceptedOutlineIsCurrent(review))) {
      return { text: "来源已变化或大纲修订已打开。先为当前来源完成新一轮大纲审阅；旧大纲仅供查看。" };
    }
    if (!acceptedOutlineIsCurrent(review)) return { text: "故事来源已确认。下一步准备大纲任务，检查候选后再明确确认。" };
    return { text: "请先完成当前大纲审阅，再继续剧情分支。" };
  }
  if (currentStep === "branches") {
    if (input.activePage === "graph") return {
      text: "专业工作台可直接编辑剧情分支。保存图草稿、确认图内容和应用路线是独立操作；检查后可返回创作工作台查看完整路线。",
      action: { kind: "navigate", label: "返回创作工作台", route: { stage: "creator" } },
    };
    const draft = input.branchDraft;
    if (draft.status === "loading") return { text: "正在读取当前分支草稿；读取完成后再继续。" };
    if (draft.status === "failed") return { text: "无法读取当前分支草稿。请点击「刷新」重新读取，暂不要带入或确认建议。" };
    if (draft.busy) return { text: "正在处理分支草稿，请等待完成；不要重复带入、保存或应用。" };
    if (draft.stale) return { text: "当前分支草稿的依据已变化。请先按分支区提示核对内容，再点击「在当前版本恢复为新草稿」。" };
    if (draft.blocked || input.branchTaskBlocked) return { text: "当前分支暂不可编辑。请先处理分支区显示的限制；读取失败时点击「刷新」，读取中请等待完成。" };
    if (draft.dirty || input.sourceReview?.sectionMapStatus === "stale") {
      const saveLabel = input.sourceReview?.acceptedSectionMap ? "保存修改" : "确认并保存故事分支";
      return { text: draft.complete
        ? `请审阅可编辑草稿；确认无误后点击「${saveLabel}」。保存不会自动应用到故事路线。`
        : `请先补全分支区的必填内容，再点击「${saveLabel}」。当前草稿尚不能确认保存。` };
    }
    if (currentGraphAdmission(input)) return {
      text: "当前分支已应用到故事路线。下一步点击「进入创作工作台」，检查每条完整播放路线、选择与结局。",
      action: { kind: "navigate", label: "进入创作工作台", route: { stage: "creator" } },
    };
    if (currentSectionMap(input.sourceReview)) return { text: "分支方案已确认。下一步点击本页「应用到故事路线」；应用后再进入创作工作台。" };
    if (input.branchTaskStatus === "loading" || input.branchTaskStatus === "idle") return { text: "正在读取剧情分支建议任务；读取完成后再继续。" };
    if (input.branchTaskStatus === "failed") return { text: "无法读取剧情分支建议。请点击分支区的「重试读取建议」。" };
    if (input.branchTask?.infeasibleReason) return { text: "当前结构无法生成分支建议。请先根据分支区说明调整项目简报与结构设置。" };
    if (input.branchTask?.staleReasons.length) return { text: "当前分支建议的依据已变化。请先核对当前来源与大纲，再按分支区提示处理；不要带入旧建议。" };
    if (input.branchTaskBusy) return { text: "正在处理分支建议任务，请等待完成；不要重复发送或带入。" };
    const candidate = input.branchTask?.candidate;
    if (candidate?.status === "ready" && candidate.suggestion) return { text: "分支建议已生成。请先审阅；如果满意，点击「带入可编辑草稿」。带入不会确认保存或应用路线。" };
    if (candidate?.status === "ready") return { text: "分支建议的内容未能读入。请点击「刷新」重新读取，暂不要带入草稿。" };
    if (candidate?.status === "prepared") return { text: "分支建议任务已准备。请按任务区发送状态继续：未发送时点击「发送给文字创作助手」；已发送时等待交付，或点击「立即检查」。" };
    return { text: "下一步点击分支区的「准备剧情分支建议」；也可自行填写当前结构草稿。" };
  }
  if (currentStep === "creator") {
    const applied = currentGraphAdmission(input);
    return { text: applied
      ? "检查每条完整播放路线、选择与结局；需要调整时可继续手工编辑。保存图草稿、确认图内容和应用路线彼此独立。"
      : "当前正式路线尚未与已确认分支匹配；仍可在创作工作台手工编辑草稿，按本页检查后再确认和应用。" };
  }
  return productionNextText(input);
}

/** A recommended sequence over existing workspaces; it does not impose admission or acceptance. */
export function buildRecommendedWorkflow(input: RecommendedWorkflowInput): RecommendedWorkflowModel | null {
  if (!primaryPages.has(input.activePage)) return null;
  const currentStep = currentStepFor(input);
  if (!currentStep) return null;
  const recommendation = nextRecommendation(input, currentStep);
  return {
    currentStep,
    currentStepLabel: steps.find(step => step.id === currentStep)!.label,
    steps: steps.map(step => ({ ...step, status: statusFor(input, step.id, currentStep) })),
    nextText: recommendation.text,
    action: recommendation.action,
  };
}
