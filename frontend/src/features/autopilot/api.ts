import { ApiTransport } from "../../api-transport";
import { browserProjectReads } from "../../project-read-admission";
import type { AutopilotRun, Handoff, Launch, ReviewMaterial } from "./contracts";
const transport = new ApiTransport(globalThis.fetch, "/api/v2", browserProjectReads);
const path = (id: string) => `/projects/${encodeURIComponent(id)}/autopilot`;
const read = async <T,>(url: string, init?: RequestInit) => (await transport.json<T>(url, init)).body;
export const autopilotApi = {
  current: (id: string, signal?: AbortSignal) => read<AutopilotRun | null>(path(id), { signal }),
  launchContext: (id: string, signal?: AbortSignal) => read<{ eligible: boolean; briefRevision: number }>(`${path(id)}/launch-context`, { signal }),
  start: (id: string, body: Launch) => read<AutopilotRun>(`${path(id)}/start`, { method: "POST", body: JSON.stringify(body) }),
  control: (id: string, revision: number, action: string) => read<AutopilotRun>(`${path(id)}/control`, { method: "POST", body: JSON.stringify({ expectedRevision: revision, action }) }),
  review: (id: string, signal?: AbortSignal) => read<ReviewMaterial>(`${path(id)}/review`, { signal }),
  handoff: (id: string, body: Handoff) => read<AutopilotRun>(`${path(id)}/handoff`, { method: "POST", body: JSON.stringify(body) }),
};
