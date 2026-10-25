import { createConflictCopy } from "../../features/authoring/createConflictCopy";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ApiError, plotloomApi } from "../../api";
import { discardDraft, discardDraftRecord, findProjectDrafts, getDraft, putDraft, draftsLocallyPreserved, type DraftRecord, type DraftScope } from "../../draft-registry";
import { useAuthoringDraftAutosave } from "../../features/authoring/useAuthoringDraftAutosave";
import type { ProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";
import { markDownstreamStale, mergeProjectResponse, serverStages, stageLabels } from "../../model";
import { workspaceWithStageDraft } from "../../project-creation";
import type { ProjectResource, ServerStageName, WorkspaceProject } from "../../types";
import { authoringDraftKey, canonicalDraftConsumption, messageFrom, sameDraftPayload, validationIssuesFrom, type DurableDraftStatus, type WorkspaceOperation } from "./contracts";
import type { WorkspaceSession } from "./useWorkspaceSession";
import { readGraphDraft } from "../../features/graph/contracts";
import { useDraftConflictReload } from "./useDraftConflictReload";

type AuthoringSession = Pick<WorkspaceSession,
  "project" | "connection" | "route" | "serverDrafts" | "capture" | "isCurrent"
  | "registerNavigationCleanup" | "markCanonicalRefreshRequired" | "refreshCurrentRoute" | "reloadCanonicalProject"
  | "acceptCreatedProject" | "acceptCanonicalProject" | "acceptCanonicalStage" | "acceptStoryboardReview"
  | "showValidationIssues" | "clearValidationIssues" | "applyDemoSave"
>;

export interface DraftConflictState {
  scope: DraftScope;
  record: DraftRecord;
  workspace: WorkspaceProject;
  serverReloaded: boolean;
}

interface ProjectAuthoringPersistenceInput {
  session: AuthoringSession;
  durableDraftsEnabled: React.MutableRefObject<boolean>;
  feedback: {
    setBusy: (busy: boolean) => void;
    setError: Dispatch<SetStateAction<string>>;
  };
  draftQuiescence: ProjectDraftQuiescence;
  scopeWritesAllowed?: (scope: DraftScope, projectId: string) => boolean;
}

/** Owns canonical authoring writes, their save flight, and draft-CAS consumption. */
export function useProjectAuthoringPersistence(input: ProjectAuthoringPersistenceInput) {
  const current = useRef(input);
  current.current = input;
  const currentDraft = useRef<{ scope: DraftScope; payload: unknown } | undefined>(undefined);
  const createKeys = useRef(new Map<string, string>());
  const saveInFlight = useRef(false);
  const saveGeneration = useRef(0);
  const activeGeneration = useRef<number | undefined>(undefined);
  const [projectSaving, setProjectSaving] = useState(false);
  const [admissionObservation, setAdmissionObservation] = useState({ projectId: "", version: 0 });
  const [draftStatus, setDraftStatus] = useState<{ projectId?: string; value: DurableDraftStatus }>({ value: "idle" });
  const statusProjectId = input.session.project.id;
  const setDurableDraftStatus = useCallback<Dispatch<SetStateAction<DurableDraftStatus>>>(update => {
    setDraftStatus(previous => ({ projectId: statusProjectId, value: typeof update === "function" ? update(previous.projectId === statusProjectId ? previous.value : "idle") : update }));
  }, [statusProjectId]);
  const durableDraftStatus = draftStatus.projectId === statusProjectId ? draftStatus.value : "idle";
  const [draftConflict, setDraftConflict] = useState<DraftConflictState | undefined>();
  const [restoredDraft, setRestoredDraft] = useState<{ scope: DraftScope; payload: unknown; source: "server" | "session" | "reconcile" } | undefined>();

  const observeAuthoringMutation = useCallback((operation: WorkspaceOperation) => {
    const session = current.current.session;
    if (!operation.projectId || session.project.id !== operation.projectId || !session.isCurrent(operation)) return;
    const projectId = operation.projectId;
    setAdmissionObservation(previous => ({ projectId,
      version: previous.projectId === projectId ? previous.version + 1 : 1 }));
  }, []);

  const { flushAuthoringDraft, scheduleAuthoringDraftAutosave, discardUnsentProjectDrafts, suspendProjectDraftWrites } = useAuthoringDraftAutosave({
    project: input.session.project,
    writesAllowed: input.session.connection === "connected" && input.session.project.operationalState !== "closed" && !input.session.project.teachingPreview && !draftConflict,
    scopeWritesAllowed: input.scopeWritesAllowed,
    projectWritesAllowed: input.draftQuiescence.canWrite,
    durableDraftsEnabledRef: input.durableDraftsEnabled,
    serverAuthoringDrafts: input.session.serverDrafts,
    captureWorkspaceOperation: input.session.capture,
    isWorkspaceOperationCurrent: input.session.isCurrent,
    setDurableDraftStatus,
    setError: input.feedback.setError,
    onConflict: (scope, record, workspace) => setDraftConflict({ scope, record, workspace, serverReloaded: false }),
    onMutationAcknowledged: observeAuthoringMutation,
  });
  const flushProjectAuthoringDrafts = useCallback(async () => {
    for (const scope of ["brief", "story_bible", "story_graph", "scene_beats", "storyboard"] as DraftScope[]) {
      if (!await flushAuthoringDraft(scope)) return false;
    }
    return true;
  }, [flushAuthoringDraft]);
  useEffect(() => {
    const ownerProject = input.session.project;
    const projectId = ownerProject.id;
    if (!projectId) return;
    return input.draftQuiescence.register(projectId, "authoring", flushProjectAuthoringDrafts, {
      retainOnUnmount: true,
      locallyPreserved: () => draftsLocallyPreserved(projectId),
      pending: () => ["brief", "story_bible", "story_graph", "scene_beats", "storyboard"].some(scope => Boolean(getDraft(ownerProject, scope as DraftScope))),
      suspendWrites: suspendProjectDraftWrites,
      discardUnsent: async () => { await discardUnsentProjectDrafts(); currentDraft.current = undefined; },
    });
  }, [flushProjectAuthoringDrafts, discardUnsentProjectDrafts, suspendProjectDraftWrites, input.draftQuiescence, input.session.project.id]);

  const cancelSave = useCallback(() => {
    saveInFlight.current = false;
    activeGeneration.current = undefined;
    setProjectSaving(false);
    current.current.feedback.setBusy(false);
  }, []);
  useEffect(
    () => input.session.registerNavigationCleanup(cancelSave),
    [cancelSave, input.session.registerNavigationCleanup],
  );

  const beginSave = useCallback((): number | undefined => {
    const { session, feedback, draftQuiescence } = current.current;
    if (session.project.archivedAt) {
      feedback.setError("归档项目为只读；请先在项目目录中恢复它。");
      return undefined;
    }
    if (session.project.id && draftQuiescence.isClosing(session.project.id)) {
      feedback.setError("项目正在执行独占操作；请等待操作完成或失败后再编辑。");
      return undefined;
    }
    if (saveInFlight.current) return undefined;
    saveInFlight.current = true;
    const generation = ++saveGeneration.current;
    activeGeneration.current = generation;
    feedback.setBusy(true);
    setProjectSaving(true);
    feedback.setError("");
    return generation;
  }, []);

  const finishSave = useCallback((operation: WorkspaceOperation, generation: number) => {
    if (activeGeneration.current !== generation) return;
    activeGeneration.current = undefined;
    saveInFlight.current = false;
    if (!current.current.session.isCurrent(operation)) return;
    setProjectSaving(false);
    current.current.feedback.setBusy(false);
  }, []);

  const refreshStaleAcceptedProject = useCallback((projectId: string) => {
    const { session, feedback } = current.current;
    session.markCanonicalRefreshRequired(projectId);
    if (session.route.project !== projectId) return;
    if (currentDraft.current || findProjectDrafts(projectId).length) {
      feedback.setError("服务器已接受较早保存；当前草稿不会被覆盖。请先保存或丢弃当前草稿后切换阶段以刷新规范版本。");
      return;
    }
    const epoch = session.refreshCurrentRoute();
    void session.reloadCanonicalProject(projectId, epoch);
  }, []);

  const retireAppliedInput = (workspace: WorkspaceProject, scope: DraftScope, payload: unknown, selected?: DraftRecord) => {
    const local = getDraft(workspace, scope);
    const sameSelection = Boolean(selected && local && local.key === selected.key && local.localRevision === selected.localRevision
      && local.baseRevision === selected.baseRevision && local.serverDraftRevision === selected.serverDraftRevision
      && local.updatedAt === selected.updatedAt && sameDraftPayload(local.payload, selected.payload));
    if (selected && sameSelection) discardDraftRecord(selected);
    if (current.current.session.project.id !== workspace.id || currentDraft.current?.scope !== scope) return;
    if (sameDraftPayload(currentDraft.current.payload, payload) && (!local || sameSelection)) {
      currentDraft.current = undefined;
      setRestoredDraft(previous => previous?.scope === scope && sameDraftPayload(previous.payload, payload) ? undefined : previous);
    }
  };
  const commitProject = useCallback(async (patch: Partial<WorkspaceProject>): Promise<string | undefined> => {
    const generation = beginSave();
    if (!generation) return undefined;
    const source = current.current;
    const operation = source.session.capture();
    const nextLocal = mergeProjectResponse(source.session.project, patch);
    const selectedInput = getDraft(source.session.project, "brief");
    const workingPayload = selectedInput?.payload ?? (currentDraft.current?.scope === "brief" ? currentDraft.current.payload : nextLocal.brief);
    try {
      if (!source.session.project.id) {
        throw new Error("请先新建项目或创建示例的编辑副本。");
      } else {
        if (source.durableDraftsEnabled.current && getDraft(source.session.project, "brief") && !await flushAuthoringDraft("brief")) return;
        const serverDraft = source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, "brief"));
        const consumed = canonicalDraftConsumption(serverDraft, "brief", source.session.project.revision, nextLocal.brief, workingPayload);
        if (serverDraft && !consumed) throw new Error("简报工作草稿与本次应用输入不一致；请先核对保留内容。");
        // A canonical Brief write invalidates every generated stage. Do not
        // manufacture that invalidation merely to acknowledge an unchanged
        // editor buffer: discard its exact draft receipt instead.
        if (sameDraftPayload(nextLocal.brief, source.session.project.brief)) {
          if (serverDraft) {
            const receipt = await plotloomApi.discardAuthoringDraft(source.session.project.id, {
              editorScope: "brief", entityId: "root", expectedDraftRevision: serverDraft.draftRevision,
            });
            if (!source.session.isCurrent(operation)) return undefined;
            if (receipt !== serverDraft.draftRevision) throw new Error("当前草稿在丢弃前已变化");
            source.session.serverDrafts.current.delete(authoringDraftKey(source.session.project.id, "brief"));
            setDurableDraftStatus("idle");
            observeAuthoringMutation(operation);
          } else if (!source.durableDraftsEnabled.current) {
            retireAppliedInput(source.session.project, "brief", workingPayload, selectedInput);
          }
          if (!source.session.isCurrent(operation)) return undefined;
          retireAppliedInput(source.session.project, "brief", workingPayload, selectedInput);
          return source.session.project.id;
        }
        const saved: { project: ProjectResource; consumedDraftRevision?: number } = consumed
          ? await plotloomApi.patchProjectWithDraft(source.session.project.id, source.session.project.revision, nextLocal.brief, consumed)
          : { project: await plotloomApi.patchProject(source.session.project.id, source.session.project.revision, nextLocal.brief) };
        if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
          source.session.serverDrafts.current.delete(authoringDraftKey(source.session.project.id, "brief"));
          setDurableDraftStatus("idle");
        } else if (!source.durableDraftsEnabled.current) {
          retireAppliedInput(source.session.project, "brief", workingPayload, selectedInput);
        }
        retireAppliedInput(source.session.project, "brief", workingPayload, selectedInput);
        if (!source.session.isCurrent(operation)) {
          refreshStaleAcceptedProject(source.session.project.id);
          return;
        }
        if (consumed && saved.consumedDraftRevision === consumed.draftRevision) observeAuthoringMutation(operation);
        // The project contract invalidates every canonical stage when its Brief
        // changes. ProjectResource intentionally carries no stage envelopes,
        // so retain the existing heads but immediately project that server
        // invalidation until the next canonical aggregate reload.
        source.session.acceptCanonicalProject({
          ...mergeProjectResponse(nextLocal, saved.project),
          staleStages: [...serverStages],
        });
        retireAppliedInput(source.session.project, "brief", workingPayload, selectedInput);
        return saved.project.id;
      }
    } catch (error) {
      if (!source.session.isCurrent(operation)) return;
      source.feedback.setError(messageFrom(error));
      if (error instanceof ApiError && error.status === 409) {
        const record = getDraft(source.session.project, "brief") ?? putDraft(source.session.project, "brief", nextLocal.brief);
        setDraftConflict({ scope: "brief", record, workspace: nextLocal, serverReloaded: false });
      }
      if (source.session.connection === "demo") source.session.applyDemoSave(mergeProjectResponse(source.session.project, patch));
    } finally {
      finishSave(operation, generation);
    }
  }, [beginSave, finishSave, flushAuthoringDraft, observeAuthoringMutation, refreshStaleAcceptedProject]);

  const commitStage = useCallback(async <T,>(stage: ServerStageName, content: T) => {
    if (stage === "story_graph") {
      if (!await flushAuthoringDraft(stage)) return;
      currentDraft.current = undefined; setRestoredDraft(undefined);
      return;
    }
    const generation = beginSave();
    if (!generation) return;
    const source = current.current;
    const operation = source.session.capture();
    const key = stage === "story_bible" ? "storyBible" : stage === "scene_beats" ? "sceneBeats" : "storyboard";
    const nextLocal = markDownstreamStale(workspaceWithStageDraft(source.session.project, stage, content), stage);
    const selectedInput = getDraft(source.session.project, stage);
    try {
      if (!source.session.project.id) throw new Error("请先新建项目或创建示例的编辑副本。");
      if (source.durableDraftsEnabled.current && getDraft(source.session.project, stage) && !await flushAuthoringDraft(stage)) return;
      const serverDraft = source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, stage));
      const consumed = canonicalDraftConsumption(serverDraft, stage, source.session.project.stageRevisions[stage], content);
      if (serverDraft && !consumed) throw new Error("阶段工作草稿与本次应用输入不一致；请先核对保留内容。");
      const saved = consumed
        ? await plotloomApi.patchStageWithDraft(source.session.project.id, stage, source.session.project.stageRevisions[stage], content, consumed)
        : { stage: await plotloomApi.patchStage(source.session.project.id, stage, source.session.project.stageRevisions[stage], content) };
      if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
        source.session.serverDrafts.current.delete(authoringDraftKey(source.session.project.id, stage));
        setDurableDraftStatus("idle");
      } else if (!source.durableDraftsEnabled.current) {
        retireAppliedInput(source.session.project, stage, content, selectedInput);
      }
      retireAppliedInput(source.session.project, stage, content, selectedInput);
      if (!source.session.isCurrent(operation)) {
        refreshStaleAcceptedProject(source.session.project.id);
        return;
      }
      if (consumed && saved.consumedDraftRevision === consumed.draftRevision) observeAuthoringMutation(operation);
      const accepted = markDownstreamStale({
        ...source.session.project,
        [key]: content,
        stageRevisions: { ...source.session.project.stageRevisions, [stage]: saved.stage.revision },
      }, stage);
      source.session.acceptCanonicalStage(accepted, stage, saved.stage);
      if (stage === "storyboard") {
        const review = await plotloomApi.getStoryboardReview(source.session.project.id).catch(() => null);
        if (source.session.isCurrent(operation)) source.session.acceptStoryboardReview(review);
      }
      retireAppliedInput(source.session.project, stage, content, selectedInput);
    } catch (error) {
      if (!source.session.isCurrent(operation)) return;
      const issues = validationIssuesFrom(error);
      if (issues.length) {
        source.session.showValidationIssues(stage, issues);
        source.feedback.setError(`${stageLabels[stage]}未通过领域校验。已保留草稿并标出 ${issues.length} 个问题。`);
      } else {
        source.feedback.setError(messageFrom(error));
      }
      if (error instanceof ApiError && error.status === 409) {
        const record = getDraft(source.session.project, stage) ?? putDraft(source.session.project, stage, content);
        setDraftConflict({ scope: stage, record, workspace: nextLocal, serverReloaded: false });
      }
      if (source.session.connection === "demo") source.session.applyDemoSave(markDownstreamStale(workspaceWithStageDraft(source.session.project, stage, content), stage));
    } finally {
      finishSave(operation, generation);
    }
  }, [beginSave, finishSave, flushAuthoringDraft, observeAuthoringMutation, refreshStaleAcceptedProject]);

  const rememberDraft = useCallback((scope: DraftScope, payload: unknown) => {
    const source = current.current;
    if (source.session.project.archivedAt || source.session.project.operationalState === "closed" || source.session.project.teachingPreview || (source.session.project.id && source.draftQuiescence.isClosing(source.session.project.id))) return;
    currentDraft.current = { scope, payload };
    const local = getDraft(source.session.project, scope);
    // An acknowledged draft remains server-owned until a canonical save
    // consumes it. A later local edit must continue its CAS chain even after
    // the acknowledged session buffer was removed; otherwise it incorrectly
    // restarts at revision zero and creates a self-conflict.
    const serverDraft = source.session.project.id
      ? source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, scope))
      : undefined;
    putDraft(source.session.project, scope, payload, local?.serverDraftRevision ?? serverDraft?.draftRevision ?? 0);
    setDurableDraftStatus("saving");
    source.draftQuiescence.changed();
    scheduleAuthoringDraftAutosave(scope);
    if (restoredDraft?.scope === scope) setRestoredDraft({ ...restoredDraft, payload });
  }, [restoredDraft, scheduleAuthoringDraftAutosave]);

  const conflictReload = useDraftConflictReload({ conflict: draftConflict, session: input.session, onLoaded: (conflict) => {
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict((existing) => existing === conflict ? { ...existing, serverReloaded: true } : existing);
  } });

  const copyDraftConflict = useCallback(async () => {
    const conflict = draftConflict;
    if (!conflict || conflictReload.isPending()) return false;
    if (conflict.scope === "story_graph") {
      const source = current.current, projectId = source.session.project.id;
      if (!projectId) return false;
      const generation = beginSave();
      if (!generation) return false;
      const operation = source.session.capture();
      try {
        const state = await plotloomApi.getGraphWorkbench(projectId);
        if (!source.session.isCurrent(operation)) return false;
        const saved = await plotloomApi.recoverGraphDraft(projectId, { expectedDraftRevision: state.draft?.draftRevision ?? 0,
          expectedBindingHash: state.bindingHash, payload: readGraphDraft(conflict.record.payload) });
        if (!source.session.isCurrent(operation)) return false;
        source.session.serverDrafts.current.set(authoringDraftKey(projectId, "story_graph"), saved);
        observeAuthoringMutation(operation);
        discardDraftRecord(conflict.record);
        currentDraft.current = { scope: "story_graph", payload: saved.payload };
        setRestoredDraft({ scope: "story_graph", payload: saved.payload, source: "server" });
        setDraftConflict(undefined);
        return true;
      } catch (error) { if (source.session.isCurrent(operation)) source.feedback.setError(`图草稿未恢复：${messageFrom(error)}`); return false; }
      finally { finishSave(operation, generation); }
    }
    const generation = beginSave();
    if (!generation) return false;
    const source = current.current;
    const operation = source.session.capture();
    const identity = `${conflict.record.key}:${conflict.record.localRevision}`;
    let key = createKeys.current.get(identity);
    if (!key) { key = `project-conflict-copy-${crypto.randomUUID()}`; createKeys.current.set(identity, key); }
    try {
      const { project: created, draft: savedDraft } = await createConflictCopy(conflict.record, conflict.workspace, key);
      if (!source.session.isCurrent(operation)) return false;
      source.session.acceptCreatedProject(conflict.workspace, created, null);
      source.session.serverDrafts.current.set(authoringDraftKey(created.id, conflict.scope), savedDraft);
      createKeys.current.delete(identity);
      discardDraftRecord(conflict.record);
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
      setDraftConflict(undefined);
      source.session.clearValidationIssues();
      return true;
    } catch (error) {
      if (!source.session.isCurrent(operation)) return false;
      const issues = validationIssuesFrom(error);
      if (issues.length && conflict.scope !== "brief") source.session.showValidationIssues(conflict.scope, issues);
      source.feedback.setError(`无法创建冲突副本：${messageFrom(error)}`);
      return false;
    } finally {
      finishSave(operation, generation);
    }
  }, [beginSave, conflictReload, draftConflict, finishSave, observeAuthoringMutation]);

  const discardDraftConflict = useCallback(() => {
    if (!draftConflict || conflictReload.isPending()) return false;
    discardDraftRecord(draftConflict.record);
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict(undefined);
    return true;
  }, [conflictReload, draftConflict]);
  const clearDraftWorkflow = useCallback(() => {
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict(undefined);
  }, []);
  const discardCurrentAuthoringDraft = useCallback(async (scope: DraftScope): Promise<boolean> => {
    const source = current.current;
    const project = source.session.project;
    const operation = source.session.capture();
    const draft = currentDraft.current;
    if (!draft || draft.scope !== scope) return false;
    if (!project.id || !source.durableDraftsEnabled.current) {
      discardDraft(project, scope);
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
      return true;
    }
    // Close has already frozen admission. Persisting first gives the server an
    // exact CAS revision to discard; only its receipt permits local removal.
    if (!await flushAuthoringDraft(scope)) return false;
    const key = authoringDraftKey(project.id, scope);
    const serverDraft = source.session.serverDrafts.current.get(key);
    if (!serverDraft) {
      source.feedback.setError("当前草稿没有可验证的服务器回执；项目仍保持打开状态。");
      return false;
    }
    try {
      const receipt = await plotloomApi.discardAuthoringDraft(project.id, {
        editorScope: scope,
        entityId: "root",
        expectedDraftRevision: serverDraft.draftRevision,
      });
      if (receipt !== serverDraft.draftRevision) {
        throw new Error("当前草稿在丢弃前已变化");
      }
      source.session.serverDrafts.current.delete(key);
      if (!source.session.isCurrent(operation)) return false;
      observeAuthoringMutation(operation);
      discardDraft(project, scope);
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
      setDurableDraftStatus("idle");
      return true;
    } catch (error) {
      if (source.session.isCurrent(operation)) source.feedback.setError(`草稿未丢弃：${messageFrom(error)}`);
      return false;
    }
  }, [flushAuthoringDraft, observeAuthoringMutation]);

  return {
    currentDraft,
    projectSaving,
    admissionVersion: admissionObservation.projectId === input.session.project.id ? admissionObservation.version : 0,
    observeAuthoringMutation,
    durableDraftStatus,
    draftConflict,
    setDraftConflict,
    restoredDraft,
    setRestoredDraft,
    flushAuthoringDraft,
    scheduleAuthoringDraftAutosave,
    rememberDraft,
    commitProject,
    commitStage,
    cancelSave,
    beginSave,
    finishSave,
    reloadDraftConflict: conflictReload.reload,
    conflictReloading: conflictReload.reloading,
    copyDraftConflict,
    discardDraftConflict,
    clearDraftWorkflow,
    discardCurrentAuthoringDraft,
  };
}
