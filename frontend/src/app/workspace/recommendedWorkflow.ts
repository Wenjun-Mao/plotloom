import type { AcceptedOutlineRevision, AcceptedSectionMapRevision, BranchTaskState, ServerStageName, SourceOutlineReviewState, StageHead, WorkspaceProject } from "../../types";
import type { PageId } from "./contracts";
import { sourceWorkflowTarget } from "./sourceWorkflowNavigation";
import type { WorkspaceSourceReviewStatus } from "./useWorkspaceSourceReview";
import { creativeWorkflowSteps, type CreativeWorkflowStepId } from "../../creative-workflow-steps";
import { graphWorkflowRecommendation } from "./recommendedGraphWorkflow";
import type { ProductionRead } from "../../features/graph/useCreatorProduction";
import type { ArtWorkflowObservation, CastWorkflowObservation, ScriptWorkflowObservation, StoryboardWorkflowObservation, BridgeWorkflowObservation, ShotWorkflowObservation } from "./ReviewWorkflowReadContext";
import { scriptWorkflowNextText } from "./recommendedScriptWorkflow";
import { artWorkflowNextText } from "./recommendedArtWorkflow";
import { castWorkflowNextText } from "./recommendedCastWorkflow";
import { storyboardWorkflowNextText } from "./recommendedStoryboardWorkflow";
import { acceptedOutlineIsCurrent } from "./sourceReviewCurrentness";

export type RecommendedWorkflowStepId = CreativeWorkflowStepId;
export type RecommendedWorkflowRoute = { stage: PageId; hash?: string };
export type BranchTaskReadObservation = { basis: string; status: "loading" | "ready" | "failed"; value: BranchTaskState | null; busy: boolean; blocked: boolean };
export type RecommendedWorkflowAction =
  | { kind: "navigate"; label: string; route: RecommendedWorkflowRoute }
  | { kind: "play"; label: string; href: string };

export type WorkflowRecommendation = { text: string; statusText?: string; action?: RecommendedWorkflowAction };

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
  branchDraft: { status: "loading" | "ready" | "failed"; dirty: boolean; complete: boolean; pendingFields?: boolean; stale: boolean; busy: boolean; blocked: boolean };
  productionRead: ProductionRead | undefined;
  scriptRead: ScriptWorkflowObservation | undefined;
  artRead: ArtWorkflowObservation | undefined;
  castRead: CastWorkflowObservation | undefined;
  storyboardRead?: StoryboardWorkflowObservation;
  bridgeRead?: BridgeWorkflowObservation;
  shotRead?: ShotWorkflowObservation;
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
  adoptionUnknown?: boolean;
  adoptedArtifact?: { operation: string; revision: number; contentHash: string };
}

export interface RecommendedWorkflowModel {
  currentStep: RecommendedWorkflowStepId;
  currentStepLabel: string;
  currentViewLabel?: string;
  steps: RecommendedWorkflowStep[];
  statusText?: string;
  nextText: string;
  action?: RecommendedWorkflowAction;
}

const steps = creativeWorkflowSteps;

const primaryPages = new Set<PageId>(["brief", "source", "graph", "creator", "characters", "bible", "beats", "storyboard"]);
const productionStages: ServerStageName[] = ["story_bible", "scene_beats", "storyboard"];
const playbackStages: ServerStageName[] = ["story_graph", "scene_beats", "storyboard"];

export function branchSuggestionBasis(outline: AcceptedOutlineRevision | null, accepted: AcceptedSectionMapRevision | null, outlineCurrent: boolean, briefKey: string): string {
  return outline ? `map:${outline.revision}:${outline.contentHash}:${accepted?.revision ?? 0}:${outlineCurrent}:${briefKey}` : "";
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
  // Editing presentations share one graph owner and one workflow activity.
  if (input.activePage === "graph" || input.activePage === "creator") return "creator";
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
  if (id === "brief") return input.project.hasConfirmedBrief === false ? "输入已保留 · 尚未确认" : input.project.id && input.project.revision > 0 ? "已有确认版本" : "尚未确认";
  if (id === "source") return outlineStatus(input);
  if (id === "branches") return branchStatus(input);
  if (id === "creator") return id === currentStep ? "正在查看" : "待检查路线";
  if (id === "production") return productionStatus(input);
  return playbackStatus(input);
}

function productionNextText(input: RecommendedWorkflowInput): WorkflowRecommendation {
  const target = input.activePage === "source" ? sourceWorkflowTarget(input.activeHash) : undefined;
  const read = input.activePage === "characters" ? input.castRead : target === "art" ? input.artRead
    : target === "script" ? input.scriptRead : target === "storyboard-review" ? input.storyboardRead : undefined;
  // Only replace an empty owner's preparation invitation. Its pending work,
  // errors, retained content and local edits still own their recovery guidance.
  const emptyPreparation = read?.status === "ready" && read.state?.status === "missing"
    && read.state.acceptedReviewState.status === "missing" && !["prepared", "ready"].includes(read.state.candidate?.status ?? "")
    && !read.busy && !read.dirty && !read.error && !("retainedDraft" in read && read.retainedDraft);
  if (emptyPreparation) {
    const action: RecommendedWorkflowAction = { kind: "navigate", label: "打开来源与大纲", route: { stage: "source", hash: "source" } };
    if (input.sourceReviewStatus === "loading" || input.sourceReviewStatus === "idle") return {
      text: "正在核实来源、大纲与已应用路线；读取完成后再准备本页任务。",
    };
    if (input.sourceReviewStatus === "failed" || !input.sourceReview) return {
      text: "无法核实本页任务的创作依据。点击左侧「来源与大纲」，再点击「刷新」重新读取；暂不建议准备任务。", action,
    };
    if (!input.sourceReview.source) return { text: "故事来源尚未确认。点击左侧「来源与大纲」，先点击「确认改编内容」；完成大纲与分支并应用路线后，再准备本页任务。", action };
    if (!acceptedOutlineIsCurrent(input.sourceReview)) return {
      text: "当前大纲尚未确认或依据已变化。点击左侧「来源与大纲」，完成当前大纲的交付与确认，再继续分支和本页任务。", action,
    };
    if (!currentSectionMap(input.sourceReview)) return {
      text: "当前剧情分支尚未确认。点击左侧「来源与大纲」，审阅并确认保存分支，再应用到故事路线；随后返回本页准备任务。", action,
    };
    if (!currentGraphAdmission(input)) return {
      text: "当前分支尚未应用到有效故事路线。点击左侧「来源与大纲」，核对分支区并点击「应用到故事路线」；随后返回本页准备任务。", action,
    };
  }
  if (target === "art") return artWorkflowNextText(input.artRead);
  if (target === "script") return scriptWorkflowNextText(input.scriptRead);
  if (target === "storyboard-review") return storyboardWorkflowNextText(input.storyboardRead, input.bridgeRead);
  if (input.activePage === "characters") return castWorkflowNextText(input.castRead);
  if (input.activePage === "bible") return { text: "检查故事设定是否与当前故事路线一致，再按需继续场景制作。" };
  if (input.activePage === "beats") return { text: "检查场景节拍与事件顺序；保存后再进入分镜工作台审阅镜头。" };
  const playerStagesReady = playbackStages.every(stage => stageState(input, stage).status === "ready");
  if (input.activePage === "storyboard") {
    const read = input.shotRead;
    if (!read) return { text: "正在读取当前镜头的制作与媒体状态；已安装分镜不代表影片或播放路线已完成。" };
    if (read.status === "ready" && read.allRoutesReady && !read.busy && !read.dirty && !playerStagesReady) return {
      text: "当前故事路线、场景或分镜尚未全部有效。先核对本页的来源与过期提示；保留的播放片段不代表当前路线可播放。",
    };
    return {
      text: read.nextText,
      ...(read.status === "ready" && read.allRoutesReady && !read.busy && !read.dirty && playerStagesReady && input.playHref
        ? { action: { kind: "play" as const, label: "检查交互式播放", href: input.playHref } } : {}),
    };
  }
  return { text: "按当前页面继续制作与审阅；播放器会核对正式故事路线、场景和分镜，内容齐备后再体验交互式路线。" };
}

function nextRecommendation(input: RecommendedWorkflowInput, currentStep: RecommendedWorkflowStepId): WorkflowRecommendation {
  const archived = input.project.lifecycleStatus === "archived" || Boolean(input.project.archivedAt);
  if (archived || input.readOnly) return { text: "项目为只读快照，可查看保留内容；恢复项目后再核实当前状态并继续创作。" };
  if (input.projectPending) return { text: "正在读取当前项目版本；读取完成后再核实已有确认和后续步骤。" };
  if (!input.project.id || input.project.hasConfirmedBrief === false) return currentStep === "brief"
    ? { text: "编辑输入自动保留。填写完整后明确确认项目简报，再开始准备来源、大纲与制作。" }
    : { text: "项目简报尚未确认。编辑输入已保留；先完成并确认简报，再开始制作。" };
  if (!input.workspaceAvailable) return { text: "当前项目版本未能读取。先刷新服务器版本；读取成功后再判断此前确认是否仍适用。" };
  if (input.actionDisabled) return { text: "项目正在读取或处理，请等待状态稳定后再继续；现有草稿和导航保护仍按当前工作台处理。" };
  if (currentStep === "brief") {
    return { text: "编辑输入自动保留；应用修改后才会更新制作依据。可以直接返回来源与大纲继续浏览。", action: { kind: "navigate", label: "打开来源与大纲", route: { stage: "source", hash: "source" } } };
  }
  const sourceNeeded = currentStep === "source" || currentStep === "branches" || currentStep === "creator"
    || (input.activePage === "source" && input.sourceDraftDirty);
  if (sourceNeeded && input.sourceReviewStatus === "loading") return { text: "正在读取来源、大纲和当前分支版本；读取完成前不沿用旧确认。" };
  if (sourceNeeded && input.sourceReviewStatus === "failed") return { text: "无法核实当前来源与大纲状态。先在本页刷新读取；保留版本不代表当前确认。" };
  if (input.activePage === "source" && input.sourceDraftDirty) return { text: "故事输入已保留、尚未应用。确认修改后下游才会使用它；也可继续浏览已确认版本。" };
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
    return graphWorkflowRecommendation(input, currentSectionMap(input.sourceReview), currentGraphAdmission(input));
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
    currentViewLabel: input.activePage === "creator" ? "创作视图" : input.activePage === "graph" ? "专业视图" : undefined,
    steps: steps.map(step => {
      const admission = step.id === "branches" && currentGraphAdmission(input) ? input.sourceReview?.graphAdmission : null;
      const adopted = step.id === "source" && acceptedOutlineIsCurrent(input.sourceReview) ? input.sourceReview?.acceptedOutline : null;
      return { ...step, status: statusFor(input, step.id, currentStep), ...(adopted ? { adoptedArtifact: {
        operation: "outline", revision: adopted.revision, contentHash: adopted.contentHash,
      } } : admission ? { adoptedArtifact: { operation: "branches", revision: admission.graphRevision, contentHash: admission.graphContentHash } }
        : step.id === "branches" && currentSectionMap(input.sourceReview) ? { adoptionUnknown: true } : {}) };
    }),
    statusText: recommendation.statusText,
    nextText: recommendation.text,
    action: recommendation.action,
  };
}
