import { useCallback, useEffect, useRef } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import type { AuthoringDraft, WorkspaceProject } from "../../types";
import { ApiError, plotloomApi } from "../../api";
import {
  acknowledgeDraft,
  getDraft,
  type DraftRecord,
  type DraftScope,
} from "../../draft-registry";
import type { DurableDraftStatus, WorkspaceOperation } from "../../app/workspace/contracts";


function authoringDraftKey(projectId: string, scope: DraftScope): string {
  return `${projectId}:${scope}:root`;
}

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : "未知错误";
}

export function useAuthoringDraftAutosave({
  project,
  durableDraftsEnabledRef,
  serverAuthoringDrafts,
  captureWorkspaceOperation,
  isWorkspaceOperationCurrent,
  setDurableDraftStatus,
  setError,
  onConflict,
}: {
  project: WorkspaceProject;
  durableDraftsEnabledRef: MutableRefObject<boolean>;
  serverAuthoringDrafts: MutableRefObject<Map<string, AuthoringDraft>>;
  captureWorkspaceOperation: () => WorkspaceOperation;
  isWorkspaceOperationCurrent: (operation: WorkspaceOperation) => boolean;
  setDurableDraftStatus: Dispatch<SetStateAction<DurableDraftStatus>>;
  setError: Dispatch<SetStateAction<string>>;
  onConflict: (scope: DraftScope, record: DraftRecord, workspace: WorkspaceProject) => void;
}) {
  const draftAutosaveTimers = useRef(new Map<string, number>());
  const draftAutosaveFlights = useRef(new Map<string, Promise<boolean>>());
  const flushAuthoringDraft = useCallback(async (scope: DraftScope): Promise<boolean> => {
    if (!durableDraftsEnabledRef.current || !project.id || project.archivedAt) return true;
    const key = authoringDraftKey(project.id, scope);
    const timer = draftAutosaveTimers.current.get(key);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      draftAutosaveTimers.current.delete(key);
    }
    // Drain to a stable local revision.  Joining one flight is insufficient:
    // typing can create a newer session record while that request is in flight.
    while (true) {
      const local = getDraft(project, scope);
      if (!local) return true;
      const existingFlight = draftAutosaveFlights.current.get(key);
      if (existingFlight) {
        if (!await existingFlight) return false;
        continue;
      }
      const operation = captureWorkspaceOperation();
      const request = (async (): Promise<boolean> => {
        if (isWorkspaceOperationCurrent(operation)) setDurableDraftStatus("saving");
        try {
          const saved = await plotloomApi.saveAuthoringDraft(project.id!, {
            editorScope: scope, entityId: "root",
            baseCanonicalRevision: local.baseRevision,
            expectedDraftRevision: local.serverDraftRevision,
            payload: local.payload as Record<string, unknown>,
          });
          serverAuthoringDrafts.current.set(key, saved);
          acknowledgeDraft(project, scope, local.localRevision, saved.draftRevision);
          if (isWorkspaceOperationCurrent(operation)) setDurableDraftStatus("saved");
          return true;
        } catch (draftError) {
          if (isWorkspaceOperationCurrent(operation)) {
            if (draftError instanceof ApiError && draftError.status === 409) {
              setDurableDraftStatus("conflict");
              onConflict(scope, local, project);
            } else {
              setDurableDraftStatus("failed");
              setError(`草稿未保存：${messageFrom(draftError)}`);
            }
          }
          return false;
        } finally {
          draftAutosaveFlights.current.delete(key);
        }
      })();
      draftAutosaveFlights.current.set(key, request);
      if (!await request) return false;
      const newer = getDraft(project, scope);
      if (!newer || newer.localRevision === local.localRevision) return true;
    }
  }, [project]);

  const scheduleAuthoringDraftAutosave = useCallback((scope: DraftScope) => {
    if (!durableDraftsEnabledRef.current || !project.id) return;
    const key = authoringDraftKey(project.id, scope);
    const existingTimer = draftAutosaveTimers.current.get(key);
    if (existingTimer !== undefined) window.clearTimeout(existingTimer);
    draftAutosaveTimers.current.set(key, window.setTimeout(() => {
      draftAutosaveTimers.current.delete(key);
      void flushAuthoringDraft(scope);
    }, 750));
  }, [flushAuthoringDraft, project.id]);

  useEffect(() => () => {
    draftAutosaveTimers.current.forEach((timer) => window.clearTimeout(timer));
    draftAutosaveTimers.current.clear();
  }, []);

  return { flushAuthoringDraft, scheduleAuthoringDraftAutosave };
}
