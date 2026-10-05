export type SpecialistStage = "outline" | "branches" | "characters" | "art" | "script" | "storyboard";
export type SpecialistBinding = { name: string; taskId: string | null };
export type SpecialistSettings = { text: SpecialistBinding; image: SpecialistBinding; busy: boolean; activeTasks?: Array<{ jobId: string; projectId?: string; stage?: SpecialistStage }> };
export type SpecialistTask = { state: "prepared" | "queued" | "outcome_unknown" | "completed"; configured?: boolean; candidateStatus?: string };
export type ImageTerminalTarget = "image_job" | "character_reference_proposal" | "art_reference_proposal";
export type ImageTerminalPreview = { markerHash: string; marker: { jobId: string; taskId: string; requestHash: string; reason: string } };
export type ImageTerminalReview = { markerHash: string; taskId: string; terminalTurnId: string; terminalRevision: number; reviewer: string; observedIdle: true; reviewedBlockedVerdict: true };

export class SpecialistApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); }
}

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`/api/v2${path}`, { method, headers: { "Content-Type": "application/json", Accept: "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json().catch(() => undefined);
  if (!response.ok) {
    const detail = data?.detail;
    throw new SpecialistApiError(typeof detail === "string" ? detail : detail?.message || data?.message || "请求暂时不可用，请检查连接或助手设置。", response.status, detail?.code || data?.code);
  }
  if (!data || typeof data !== "object") throw new SpecialistApiError("助手响应格式无效，请刷新并核对交付。", response.status, "invalid_response");
  return data as T;
}
const path = (project: string, stage: SpecialistStage, job: string) => `/projects/${encodeURIComponent(project)}/specialist-tasks/${stage}/${encodeURIComponent(job)}`;
export const specialistsApi = {
  settings: () => request<SpecialistSettings>("/specialists"),
  save: (settings: SpecialistSettings) => request<SpecialistSettings>("/specialists", "PUT", { text: settings.text, image: settings.image }),
  status: (project: string, stage: SpecialistStage, job: string) => request<SpecialistTask>(path(project, stage, job)),
  send: (project: string, stage: SpecialistStage, job: string) => request<SpecialistTask>(`${path(project, stage, job)}/send`, "POST"),
  check: (project: string, stage: SpecialistStage, job: string) => request<SpecialistTask>(`${path(project, stage, job)}/check`, "POST"),
  sendArtImage: (project: string, job: string) => request(`/projects/${encodeURIComponent(project)}/art-reference-proposals/${encodeURIComponent(job)}/send`, "POST"),
  sendImage: (project: string, job: string) => request(`/projects/${encodeURIComponent(project)}/image-jobs/${encodeURIComponent(job)}/send`, "POST"),
  imageTerminalPreview: (project: string, target: ImageTerminalTarget, job: string) => request<ImageTerminalPreview>(`/projects/${encodeURIComponent(project)}/image-terminal/${target}/${encodeURIComponent(job)}`),
  settleImageTerminal: (project: string, target: ImageTerminalTarget, job: string, review: ImageTerminalReview) => request(`/projects/${encodeURIComponent(project)}/image-terminal/${target}/${encodeURIComponent(job)}/settle`, "POST", review),
};
