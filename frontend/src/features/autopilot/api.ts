import { ApiTransport } from "../../api-transport";
import { browserProjectReads } from "../../project-read-admission";
import type { AutopilotRun, BulkHandoff, Handoff, Launch, ReviewMaterial, TextFailure, TextRetry } from "./contracts";
const transport = new ApiTransport(globalThis.fetch, "/api/v2", browserProjectReads);
const path = (id: string) => `/projects/${encodeURIComponent(id)}/autopilot`;
const read = async <T,>(url: string, init?: RequestInit) => (await transport.json<T>(url, init)).body;
export const autopilotApi = {
  textFailure: (id: string, signal?: AbortSignal, stage?: string) => read<TextFailure | null>(`${path(id)}/text-failure${stage ? `?stage=${encodeURIComponent(stage)}` : ""}`, { signal }),
  retryText: (id: string, body: TextRetry) => read<AutopilotRun>(`${path(id)}/text-retry`, { method: "POST", body: JSON.stringify(body) }),
  deliveryEvidence: (id: string, signal?: AbortSignal) => read<import("./deliveryEvidence").EvidenceReads>(`${path(id)}/delivery-evidence`, { signal }),
  current: (id: string, signal?: AbortSignal) => read<AutopilotRun | null>(path(id), { signal }),
  launchContext: (id: string, signal?: AbortSignal) => read<{ eligible: boolean; briefRevision: number }>(`${path(id)}/launch-context`, { signal }),
  start: (id: string, body: Launch) => read<AutopilotRun>(`${path(id)}/start`, { method: "POST", body: JSON.stringify(body) }),
  control: (id: string, revision: number, action: string) => read<AutopilotRun>(`${path(id)}/control`, { method: "POST", body: JSON.stringify({ expectedRevision: revision, action }) }),
  continuationContext: (id: string) => read<{ runId: string; runRevision: number; materialClosure: string; eligible: boolean; blockers: string[]; inheritedOperations: number; lifetimeJobs: number; lifetimeImages: number }>(`${path(id)}/continuation-context`),
  continueMaterial: (id: string, body: Launch & { expectedRunId: string; expectedRunRevision: number; expectedMaterialClosure: string }) => read<AutopilotRun>(`${path(id)}/continue`, { method: "POST", body: JSON.stringify(body) }),
  review: (id: string, signal?: AbortSignal) => read<ReviewMaterial>(`${path(id)}/review`, { signal }),
  handoff: (id: string, body: Handoff | BulkHandoff) => read<AutopilotRun>(`${path(id)}/handoff`, { method: "POST", body: JSON.stringify(body) }),
};
