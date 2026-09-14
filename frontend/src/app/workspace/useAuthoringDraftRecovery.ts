import { useEffect, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { discardDraft, findProjectDrafts, findRevisionConflict, getDraft, type DraftRecord, type DraftScope } from "../../draft-registry";
import { plotloomApi } from "../../api";
import { authoringDraftKey, messageFrom, stageForPage, type DraftRecoverySource, type PageId } from "./contracts";
import type { AuthoringDraft, WorkspaceProject } from "../../types";
import type { DraftConflictState } from "./useProjectAuthoringPersistence";

export type DraftRecovery = { scope: DraftScope; payload: unknown; source: DraftRecoverySource };

/** Owns draft restoration prompts and the session/server discard handshake. */
export function useAuthoringDraftRecovery({ activePage, project, durableEnabled, serverDrafts, currentDraft, restoredDraft, setRestoredDraft, draftConflict, setDraftConflict, unsafeDraft, setUnsafeDraft, scheduleAutosave, setError }: {
  activePage: PageId;
  project: WorkspaceProject;
  durableEnabled: boolean;
  serverDrafts: MutableRefObject<Map<string, AuthoringDraft>>;
  currentDraft: MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
  restoredDraft: DraftRecovery | undefined;
  setRestoredDraft: Dispatch<SetStateAction<DraftRecovery | undefined>>;
  draftConflict: DraftConflictState | undefined;
  setDraftConflict: Dispatch<SetStateAction<DraftConflictState | undefined>>;
  unsafeDraft: { record: DraftRecord; reason: "archived" | "unavailable" } | undefined;
  setUnsafeDraft: Dispatch<SetStateAction<{ record: DraftRecord; reason: "archived" | "unavailable" } | undefined>>;
  scheduleAutosave: (scope: DraftScope) => void;
  setError: Dispatch<SetStateAction<string>>;
}) {
  const [recovery, setRecovery] = useState<DraftRecovery | undefined>();
  const [editorNonce, setEditorNonce] = useState(0);
  useEffect(() => {
    const scope = stageForPage(activePage);
    if (project.id && (project.archivedAt || project.lifecycleStatus === "archived")) {
      const record = findProjectDrafts(project.id)[0];
      if (record && !unsafeDraft) setUnsafeDraft({ record, reason: "archived" });
      return;
    }
    if (!scope || currentDraft.current || recovery || draftConflict || unsafeDraft || restoredDraft) return;
    const saved = getDraft(project, scope);
    const serverDraft = project.id && durableEnabled ? serverDrafts.current.get(authoringDraftKey(project.id, scope)) : undefined;
    if (serverDraft) setRecovery({ scope, payload: saved?.payload ?? serverDraft.payload, source: saved ? "reconcile" : "server" });
    else if (saved) setRecovery({ scope, payload: saved.payload, source: "session" });
    else {
      const conflict = findRevisionConflict(project, scope);
      if (conflict) setDraftConflict({ scope, record: conflict, workspace: project, serverReloaded: false });
    }
  }, [activePage, draftConflict, durableEnabled, project, recovery, restoredDraft, serverDrafts, unsafeDraft, currentDraft, setDraftConflict, setUnsafeDraft]);

  const restore = () => {
    if (!recovery) return;
    currentDraft.current = { scope: recovery.scope, payload: recovery.payload };
    setRestoredDraft(recovery);
    if (recovery.source !== "server") scheduleAutosave(recovery.scope);
    setEditorNonce((value) => value + 1);
    setRecovery(undefined);
  };
  const discard = () => {
    if (!recovery) return;
    discardDraft(project, recovery.scope);
    const serverDraft = project.id && serverDrafts.current.get(authoringDraftKey(project.id, recovery.scope));
    if (serverDraft && project.id) {
      void plotloomApi.discardAuthoringDraft(project.id, { editorScope: recovery.scope, entityId: "root", expectedDraftRevision: serverDraft.draftRevision })
        .then((receipt) => { if (receipt === serverDraft.draftRevision) serverDrafts.current.delete(authoringDraftKey(project.id!, recovery.scope)); })
        .catch((error) => setError(`草稿未丢弃：${messageFrom(error)}`));
    }
    currentDraft.current = undefined;
    setRecovery(undefined);
    setRestoredDraft(undefined);
    setEditorNonce((value) => value + 1);
  };
  return { recovery, setRecovery, editorNonce, restore, discard, bumpEditorNonce: () => setEditorNonce((value) => value + 1) };
}
