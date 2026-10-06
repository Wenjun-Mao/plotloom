import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { discardDraft, findProjectDrafts, findRevisionConflict, getDraft, retainDraftRecord, type DraftRecord, type DraftScope } from "../../draft-registry";
import { ApiError, plotloomApi } from "../../api";
import type { WorkspaceProject } from "../../types";
import { authoringDraftKey, messageFrom, stageForPage, type DraftRecoverySource } from "./contracts";
import type { DraftConflictState } from "./useProjectAuthoringPersistence";
import type { WorkspaceSession } from "./useWorkspaceSession";

export type DraftRecovery = { scope: DraftScope; payload: unknown; source: DraftRecoverySource };
type RecoveryPrompt = DraftRecovery & { projectId: string | undefined; baseRevision: number; record: DraftRecord; workspace: WorkspaceProject };
type DraftRecoverySession = Pick<WorkspaceSession, "activePage" | "project" | "serverDrafts" | "unsafeDraft" | "setUnsafeDraft" | "connection" | "capture" | "isCurrent" | "rejectProjectLoad">;

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
  const [recovery, setRecovery] = useState<RecoveryPrompt | undefined>();
  const [editorNonce, setEditorNonce] = useState(0);
  const [restoring, setRestoring] = useState(false);
  const { activePage, project, serverDrafts, unsafeDraft } = session;

  useEffect(() => {
    const scope = stageForPage(activePage);
    if (project.id && (project.archivedAt || project.lifecycleStatus === "archived")) {
      const record = findProjectDrafts(project.id)[0];
      if (record && !unsafeDraft) session.setUnsafeDraft({ record, reason: "archived" });
      return;
    }
    // The shared graph provider owns current typed graph recovery in both modes.
    if (scope === "story_graph") return;
    if (!scope || (project.id && session.connection !== "connected") || currentDraft.current || recovery || draftConflict || unsafeDraft || restoredDraft) return;
    const saved = getDraft(project, scope);
    const serverDraft = project.id && durableEnabled ? serverDrafts.current.get(authoringDraftKey(project.id, scope)) : undefined;
    if (serverDraft) {
      const record = saved ?? {
        key: `${project.id}:${scope}:${serverDraft.baseCanonicalRevision}`, projectId: project.id!, scope,
        baseRevision: serverDraft.baseCanonicalRevision, serverDraftRevision: serverDraft.draftRevision,
        localRevision: 0, payload: serverDraft.payload, updatedAt: serverDraft.updatedAt,
      };
      setRecovery({ scope, payload: record.payload, source: saved ? "reconcile" : "server", projectId: project.id, baseRevision: record.baseRevision, record, workspace: project });
    }
    else if (saved) setRecovery({ scope, payload: saved.payload, source: "session", projectId: project.id, baseRevision: saved.baseRevision, record: saved, workspace: project });
    else {
      const conflict = findRevisionConflict(project, scope);
      if (conflict) setDraftConflict({ scope, record: conflict, workspace: project, serverReloaded: false });
    }
  }, [activePage, draftConflict, durableEnabled, project, recovery, restoredDraft, serverDrafts, session, unsafeDraft, currentDraft, setDraftConflict]);

  const restore = async () => {
    if (!recovery || restoring || unsafeDraft || (project.id && session.connection !== "connected")) return;
    const operation = session.capture();
    let missingAuthority = false;
    setRestoring(true);
    try {
      if (project.id !== recovery.projectId) throw new Error("草稿不属于当前项目，内容仍保留。 ");
      if (project.id) {
        const [authority, stages] = await Promise.all([plotloomApi.getProject(project.id).catch(error => {
          missingAuthority = error instanceof ApiError && error.status === 404; throw error;
        }), plotloomApi.getStages(project.id)]);
        if (!session.isCurrent(operation)) return;
        const actual = recovery.scope === "brief" ? authority.revision : stages.stages.find(stage => stage.head.stage === recovery.scope)?.head.revision;
        const expected = recovery.scope === "brief" ? project.revision : project.stageRevisions[recovery.scope];
        if (authority.id !== recovery.projectId) throw new Error("项目响应不属于当前草稿，内容仍保留。");
        if (authority.archivedAt || authority.lifecycleStatus === "archived") {
          session.rejectProjectLoad({ record: retainDraftRecord(recovery.record), reason: "archived" });
          setRecovery(undefined); setError("草稿未恢复：项目已归档；保留内容可查看或导出。"); return;
        }
        if (actual !== recovery.baseRevision || expected !== recovery.baseRevision) {
          setDraftConflict({ scope: recovery.scope, record: retainDraftRecord(recovery.record), workspace: recovery.workspace, serverReloaded: false });
          setRecovery(undefined); setError("草稿未恢复：项目版本已变化，请查看服务器版本或单独处理冲突草稿。"); return;
        }
      }
      currentDraft.current = { scope: recovery.scope, payload: recovery.payload };
      setRestoredDraft(recovery);
      if (recovery.source !== "server") scheduleAutosave(recovery.scope);
      setEditorNonce((value) => value + 1);
      setRecovery(undefined);
    } catch (error) {
      if (session.isCurrent(operation)) {
        session.rejectProjectLoad({ record: retainDraftRecord(recovery.record), reason: missingAuthority ? "missing" : "temporary" });
        setRecovery(undefined); setError(`草稿未恢复：${messageFrom(error)}`);
      }
    } finally { setRestoring(false); }
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
    restoring,
    restore,
    discard,
    reloadConflict,
    copyConflict,
    discardConflict,
    bumpEditorNonce: () => setEditorNonce((value) => value + 1),
  };
}
