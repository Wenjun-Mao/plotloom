import { emptyStageContent } from "../../demo";
import { ApiError } from "../../api";
import type { AuthoringDraft, CanonicalDraftConsumption, ServerStageName, StageEnvelope, StageHead, ValidationIssue, WorkspaceProject } from "../../types";
import type { DraftScope } from "../../draft-registry";

export type PageId = "source" | "characters" | "brief" | "bible" | "graph" | "beats" | "storyboard" | "trace" | "quarantine";
export type NavigationTarget = { project: string; stage: PageId; entity: string; run: string; hash: string; history: "push" | "pop"; forceReload?: boolean };
export type WorkspaceOperation = { epoch: number; projectId: string; stage: PageId };
export type DraftRecoverySource = "server" | "session" | "reconcile";
export type DurableDraftStatus = "idle" | "saving" | "saved" | "failed" | "conflict";

export const navigation: { id: PageId; index: string; label: string; description: string }[] = [
  { id: "source", index: "01", label: "来源与大纲", description: "来源、候选与接受" },
  { id: "characters", index: "02", label: "角色", description: "文字与外观参考" },
  { id: "brief", index: "03", label: "项目简报", description: "梗概与提案" },
  { id: "bible", index: "04", label: "故事圣经", description: "人物与规则" },
  { id: "graph", index: "05", label: "剧情 DAG", description: "分支与汇合" },
  { id: "beats", index: "06", label: "场景节拍", description: "原子事件" },
  { id: "storyboard", index: "07", label: "分镜工作台", description: "路径与媒体" },
  { id: "trace", index: "08", label: "运行轨迹", description: "Prompt 与证据" },
  { id: "quarantine", index: "09", label: "隔离修复", description: "安全失败" },
];

export const editableStages: ServerStageName[] = ["story_bible", "story_graph", "scene_beats", "storyboard"];
export const authoringDraftKey = (projectId: string, scope: DraftScope) => `${projectId}:${scope}:root`;
export const sameDraftPayload = (left: unknown, right: unknown) => JSON.stringify(left) === JSON.stringify(right);
export function canonicalDraftConsumption(draft: AuthoringDraft | undefined, scope: DraftScope, canonicalRevision: number, payload: unknown): CanonicalDraftConsumption | undefined {
  if (!draft || draft.baseCanonicalRevision !== canonicalRevision || !sameDraftPayload(draft.payload, payload)) return undefined;
  return { editorScope: scope, entityId: "root", draftRevision: draft.draftRevision };
}
export const headsByStage = (stages: StageEnvelope[]) => Object.fromEntries(stages.map((envelope) => [envelope.head.stage, envelope.head])) as Partial<Record<ServerStageName, StageHead>>;
export function messageFrom(error: unknown): string { return error instanceof ApiError && error.status === 409 ? `项目版本冲突：${error.message}。请刷新后再合并修改。` : error instanceof Error ? error.message : "未知错误"; }
export function validationIssuesFrom(error: unknown): ValidationIssue[] {
  const details = error && typeof error === "object" && "details" in error ? (error as { details?: unknown }).details : undefined;
  const rawIssues = details && typeof details === "object" && "issues" in details ? (details as { issues?: unknown }).issues : undefined;
  if (!Array.isArray(rawIssues)) return [];
  return rawIssues.flatMap((raw): ValidationIssue[] => { if (!raw || typeof raw !== "object") return []; const value = raw as { code?: unknown; path?: unknown; message?: unknown }; if (typeof value.code !== "string" || typeof value.message !== "string") return []; return [{ code: value.code, path: Array.isArray(value.path) ? value.path.map(String).join(".") : typeof value.path === "string" ? value.path : "", message: value.message }]; });
}
export const projectIdFromLocation = () => new URLSearchParams(window.location.search).get("project") || "";
export const pageFromStage = (stage: string | null): PageId => navigation.some((item) => item.id === stage) ? stage as PageId : "brief";
export function stageForPage(page: PageId): DraftScope | undefined { return page === "brief" ? "brief" : page === "bible" ? "story_bible" : page === "graph" ? "story_graph" : page === "beats" ? "scene_beats" : page === "storyboard" ? "storyboard" : undefined; }
export function routeFromLocation() { const query = new URLSearchParams(window.location.search); return { project: query.get("project") || "", stage: pageFromStage(query.get("stage")), entity: query.get("entity") || "", run: query.get("run") || "", hash: decodeHash(location.hash) }; }
function decodeHash(value: string) { try { return decodeURIComponent(value.replace(/^#/, "")); } catch { return ""; } }
export const newClientDraftOwner = () => `workspace-${crypto.randomUUID()}`;
export function blankWorkspace(clientDraftOwner = newClientDraftOwner()): WorkspaceProject { return { clientDraftOwner, revision: 0, brief: { title: "", synopsis: "", genre: null, visualStyle: null, language: "zh-CN", aspectRatio: "16:9", targetPlaythroughSeconds: 180, decisionPointsPerPath: 2, endingCount: 2, nodeBudget: 8, maxOutDegree: 3, desiredJoinCount: 1, shotsPerSceneMin: 1, shotsPerSceneMax: 4, shotCountPolicy: "advisory" }, ...emptyStageContent, quarantines: [], staleStages: [], stageRevisions: { story_bible: 0, story_graph: 0, scene_beats: 0, storyboard: 0 } }; }
