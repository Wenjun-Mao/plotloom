import { ApiTransport } from "../../api-transport";
import { browserProjectReads } from "../../project-read-admission";
import type { Batch, Review } from "./contracts";
const transport = new ApiTransport(globalThis.fetch, "/api/v2", browserProjectReads);
const path = (id: string) => `/projects/${encodeURIComponent(id)}/video-batch`;
async function read<T>(id: string, suffix = "", body?: unknown, signal?: AbortSignal) {
  return (await transport.json<T>(path(id) + suffix, { signal, ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }) })).body;
}
export const batchApi = {
  current: (id: string, signal?: AbortSignal) => read<Batch | null>(id, "", undefined, signal),
  command: (id: string, name: string, body: unknown) => read<Batch>(id, `/${name}`, body),
  review: (id: string, signal?: AbortSignal) => read<Review>(id, "/review", undefined, signal),
  confirmPack: (id: string, body: unknown) => read<{ id: string }>(id, "/confirm", body),
};
