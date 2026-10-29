import { ApiTransport } from "../../api-transport";
import { browserProjectReads } from "../../project-read-admission";
import type { ContentLanguageStage, ContentLanguageStatus } from "./contracts";
const transport = new ApiTransport(globalThis.fetch, "/api/v2", browserProjectReads);
const original = (project: string, stage: ContentLanguageStage, job: string) => `/projects/${encodeURIComponent(project)}/content-language/${stage}/${encodeURIComponent(job)}`;
const exact = (project: string, check: string) => `/projects/${encodeURIComponent(project)}/content-language-checks/${encodeURIComponent(check)}`;
const read = async (path: string, signal?: AbortSignal) => (await transport.json<ContentLanguageStatus>(path, { signal })).body;
const command = async (path: string, body: unknown = {}) => (await transport.json<ContentLanguageStatus>(path, { method: "POST", body: JSON.stringify(body) })).body;
export const contentLanguageApi = {
  retry: (project: string, anchor: string, body: { commandId: string; failedJobId: string; failedAttemptId: string }) => command(exact(project, anchor) + "/retry", body),
  status: (project: string, stage: ContentLanguageStage, job: string, signal?: AbortSignal) => read(original(project, stage, job), signal),
  check: (project: string, stage: ContentLanguageStage, job: string, candidate?: Record<string, unknown>, automaticRetryLimit?: number) => command(original(project, stage, job) + "/check", { ...(candidate ? { candidate } : {}), ...(automaticRetryLimit === undefined ? {} : { automaticRetryLimit }) }),
  exact: (project: string, check: string, signal?: AbortSignal) => read(exact(project, check), signal),
  reconcile: (project: string, check: string) => command(exact(project, check) + "/reconcile"),
  cancel: (project: string, check: string) => command(exact(project, check) + "/cancel"),
};
