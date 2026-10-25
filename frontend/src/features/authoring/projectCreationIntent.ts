import type { ProjectCreationRequest } from "../../types";
import { draftClientIdentity } from "./clientJournalStorage";
export type ProjectCreationIntent = { key: string; mode: "blank" | "teaching"; request: ProjectCreationRequest; owner: string; createdAt: string };
const prefix = "plotloom:create-intent:v1:";
export function retainedCreationIntent(): ProjectCreationIntent | undefined {
  const owner = draftClientIdentity().split(":")[0];
  const retained: ProjectCreationIntent[] = [];
  for (let index = 0; index < localStorage.length; index++) {
    const key = localStorage.key(index);
    if (!key?.startsWith(prefix)) continue;
    const value = JSON.parse(localStorage.getItem(key) || "null") as ProjectCreationIntent | null;
    if (value?.owner === owner && value.key && value.request) retained.push(value);
  }
  return retained.sort((a, b) => a.createdAt.localeCompare(b.createdAt))[0];
}
export function reserveCreationIntent(mode: ProjectCreationIntent["mode"], request: ProjectCreationRequest): ProjectCreationIntent {
  const intent = { key: `project-create-${crypto.randomUUID()}`, mode, request, owner: draftClientIdentity().split(":")[0], createdAt: new Date().toISOString() };
  const serialized = JSON.stringify(intent);
  localStorage.setItem(prefix + intent.key, serialized);
  if (localStorage.getItem(prefix + intent.key) !== serialized) throw new Error("新项目创建意图未能在本机保留，请重试。");
  return intent;
}
export function acknowledgeCreationIntent(intent: ProjectCreationIntent) { localStorage.removeItem(prefix + intent.key); }
