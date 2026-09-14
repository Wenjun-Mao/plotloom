import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { discardDraft, findProjectDrafts, findRevisionConflict, getDraft, type DraftScope } from "../../draft-registry";
import { plotloomApi } from "../../api";
import { authoringDraftKey, messageFrom, stageForPage, type DraftRecoverySource } from "./contracts";
import type { DraftConflictState } from "./useProjectAuthoringPersistence";
import type { WorkspaceSession } from "./useWorkspaceSession";

export type DraftRecovery = { scope: DraftScope; payload: unknown; source: DraftRecoverySource };
type DraftRecoverySession = Pick<WorkspaceSession, "activePage" | "project" | "serverDrafts" | "unsafeDraft" | "setUnsafeDraft">;

/** Owns draft restoration prompts and the session/server discard handshake. */
export function useAuthoringDraftRecovery({
  session,
  durableEnabled,
  currentDraft,
  restoredDraft,
  setRestoredDraft,
  draftConflict,
  setDraftConflict,
  scheduleAutosave,
  setError,
  reloadDraftConflict,
  copyDraftConflict,
  discardDraftConflict,
}: {
  session: DraftRecoverySession;
  durableEnabled: boolean;
  currentDraft: React.MutableRefObject<{ scope: DraftScope; payload: unknown } | undefined>;
  restoredDraft: DraftRecovery | undefined;
  setRestoredDraft: Dispatch<SetStateAction<DraftRecovery | undefined>>;
  draftConflict: DraftConflictState | undefined;
  setDraftConflict: Dispatch<SetStateAction<DraftConflictState | undefined>>;
  scheduleAutosave: (scope: DraftScope) => void;
  setError: Dispatch<SetStateAction<string>>;
  reloadDraftConflict: () => Promise<boolean>;
  copyDraftConflict: () => Promise<boolean>;
  discardDraftConflict: () => boolean;
}) {
  const [recovery, setRecovery] = useState<DraftRecovery | undefined>();
  const [editorNonce, setEditorNonce] = useState(0);
  const { activePage, project, serverDrafts, unsafeDraft } = session;

  useEffect(() => {
    const scope = stageForPage(activePage);
    if (project.id && (project.archivedAt || project.lifecycleStatus === "archived")) {
      const record = findProjectDrafts(project.id)[0];
      if (record && !unsafeDraft) session.setUnsafeDraft({ record, reason: "archived" });
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
  }, [activePage, draftConflict, durableEnabled, project, recovery, restoredDraft, serverDrafts, session, unsafeDraft, currentDraft, setDraftConflict]);

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
        .then((receipt) => {
          if (receipt === serverDraft.draftRevision) serverDrafts.current.delete(authoringDraftKey(project.id!, recovery.scope));
        })
        .catch((error) => setError(`草稿未丢弃：${messageFrom(error)}`));
    }
    currentDraft.current = undefined;
    setRecovery(undefined);
    setRestoredDraft(undefined);
    setEditorNonce((value) => value + 1);
  };
  const reloadConflict = async () => {
    if (await reloadDraftConflict()) setEditorNonce((value) => value + 1);
  };
  const copyConflict = async () => {
    if (await copyDraftConflict()) setEditorNonce((value) => value + 1);
  };
  const discardConflict = () => {
    if (discardDraftConflict()) setEditorNonce((value) => value + 1);
  };

  return {
    recovery,
    setRecovery,
    editorNonce,
    restore,
    discard,
    reloadConflict,
    copyConflict,
    discardConflict,
    bumpEditorNonce: () => setEditorNonce((value) => value + 1),
  };
}
