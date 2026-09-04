import type { ServerStageName, WorkspaceProject } from "./types";

export type DraftScope = "brief" | ServerStageName;

export interface DraftRecord {
  key: string;
  /** The persisted project id, or the private owner for an unsaved workspace. */
  projectId: string;
  scope: DraftScope;
  baseRevision: number;
  payload: unknown;
  updatedAt: string;
}

const storageKey = "plotloom:workbench-drafts:v1";

function draftOwner(project: WorkspaceProject): string {
  // Never use a shared `new` namespace: a blank workspace and the sample are
  // independent editing sessions and must not recover one another's content.
  return project.id || `local:${project.clientDraftOwner || "legacy"}`;
}

export function draftKey(project: WorkspaceProject, scope: DraftScope): string {
  const projectId = draftOwner(project);
  const baseRevision = scope === "brief" ? project.revision : project.stageRevisions[scope];
  return `${projectId}:${scope}:${baseRevision}`;
}

function readAll(): Record<string, DraftRecord> {
  try {
    const raw = window.sessionStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed as Record<string, DraftRecord> : {};
  } catch {
    return {};
  }
}

function writeAll(records: Record<string, DraftRecord>): void {
  window.sessionStorage.setItem(storageKey, JSON.stringify(records));
}

export function getDraft(project: WorkspaceProject, scope: DraftScope): DraftRecord | undefined {
  return readAll()[draftKey(project, scope)];
}

export function putDraft(project: WorkspaceProject, scope: DraftScope, payload: unknown): DraftRecord {
  const key = draftKey(project, scope);
  const projectId = draftOwner(project);
  const baseRevision = scope === "brief" ? project.revision : project.stageRevisions[scope];
  const record: DraftRecord = { key, projectId, scope, baseRevision, payload, updatedAt: new Date().toISOString() };
  writeAll({ ...readAll(), [key]: record });
  return record;
}

export function discardDraft(project: WorkspaceProject, scope: DraftScope): void {
  const all = readAll();
  delete all[draftKey(project, scope)];
  writeAll(all);
}

/**
 * A draft from another revision is intentionally not recoverable. Returning
 * it lets the UI make the conflict visible and offer only a safe discard.
 */
export function findRevisionConflict(project: WorkspaceProject, scope: DraftScope): DraftRecord | undefined {
  const owner = draftOwner(project);
  const currentKey = draftKey(project, scope);
  return Object.values(readAll())
    .filter((record) => record.projectId === owner && record.scope === scope && record.key !== currentKey)
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0];
}

export function discardDraftRecord(record: DraftRecord): void {
  const all = readAll();
  delete all[record.key];
  writeAll(all);
}

/** Used when the server object is archived, unavailable, or deleted. */
export function findProjectDrafts(projectId: string): DraftRecord[] {
  return Object.values(readAll())
    .filter((record) => record.projectId === projectId)
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

export function hasDraft(project: WorkspaceProject, scope: DraftScope): boolean {
  return Boolean(getDraft(project, scope));
}
