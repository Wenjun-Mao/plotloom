export type SpecialistStage = "outline" | "characters" | "art" | "script" | "storyboard";
export type SpecialistBinding = { name: string; taskId: string | null };
export type SpecialistSettings = { text: SpecialistBinding; image: SpecialistBinding; busy: boolean; activeTasks?: Array<{ jobId: string; projectId?: string; stage?: SpecialistStage }> };
export type SpecialistTask = { state: "prepared" | "queued" | "outcome_unknown" | "completed"; configured?: boolean; candidateStatus?: string };

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`/api/v2${path}`, { method, headers: { "Content-Type": "application/json", Accept: "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || data.message || "请求失败，请检查聊天 ID 和助手设置。");
  }
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
};
