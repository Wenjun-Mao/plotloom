import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ApiError, plotloomApi } from "../../api";
import { discardDraft, discardDraftRecord, findProjectDrafts, getDraft, putDraft, type DraftRecord, type DraftScope } from "../../draft-registry";
import { useAuthoringDraftAutosave } from "../../features/authoring/useAuthoringDraftAutosave";
import { markDownstreamStale, mergeProjectResponse, stageLabels } from "../../model";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "../../project-creation";
import type { ProjectResource, ServerStageName, WorkspaceProject } from "../../types";
import { authoringDraftKey, canonicalDraftConsumption, messageFrom, newClientDraftOwner, validationIssuesFrom, type DurableDraftStatus, type WorkspaceOperation } from "./contracts";
import type { WorkspaceSession } from "./useWorkspaceSession";

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
  const [durableDraftStatus, setDurableDraftStatus] = useState<DurableDraftStatus>("idle");
  const [draftConflict, setDraftConflict] = useState<DraftConflictState | undefined>();
  const [restoredDraft, setRestoredDraft] = useState<{ scope: DraftScope; payload: unknown; source: "server" | "session" | "reconcile" } | undefined>();

  const { flushAuthoringDraft, scheduleAuthoringDraftAutosave } = useAuthoringDraftAutosave({
    project: input.session.project,
    durableDraftsEnabledRef: input.durableDraftsEnabled,
    serverAuthoringDrafts: input.session.serverDrafts,
    captureWorkspaceOperation: input.session.capture,
    isWorkspaceOperationCurrent: input.session.isCurrent,
    setDurableDraftStatus,
    setError: input.feedback.setError,
    onConflict: (scope, record, workspace) => setDraftConflict({ scope, record, workspace, serverReloaded: false }),
  });

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
    const { session, feedback } = current.current;
    if (session.project.archivedAt) {
      feedback.setError("归档项目为只读；请先在项目目录中恢复它。");
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

  const createProjectFrom = useCallback(async (nextLocal: WorkspaceProject, operation: WorkspaceOperation, initialStage?: ServerStageName) => {
    const source = current.current;
    const request = projectCreationRequest(nextLocal.brief, initialStage ? initialStagesThrough(nextLocal, initialStage) : []);
    const body = projectCreationBody(request);
    let idempotencyKey = createKeys.current.get(body);
    if (!idempotencyKey) {
      idempotencyKey = `project-create-${crypto.randomUUID()}`;
      createKeys.current.set(body, idempotencyKey);
    }
    const created = await plotloomApi.createProject(request, idempotencyKey);
    if (!source.session.isCurrent(operation)) return false;
    const storyboardReady = created.stages.some((stage) => stage.head.stage === "storyboard" && stage.head.status === "ready");
    const review = storyboardReady ? await plotloomApi.getStoryboardReview(created.id).catch(() => null) : null;
    if (!source.session.isCurrent(operation)) return false;
    source.session.acceptCreatedProject(nextLocal, created, review);
    createKeys.current.delete(body);
    cancelSave();
    return true;
  }, [cancelSave]);

  const commitProject = useCallback(async (patch: Partial<WorkspaceProject>) => {
    const generation = beginSave();
    if (!generation) return;
    const source = current.current;
    const operation = source.session.capture();
    const nextLocal = mergeProjectResponse(source.session.project, patch);
    try {
      if (!source.session.project.id) {
        if (!await createProjectFrom(nextLocal, operation, nextLocal.initialStageOnFirstSave)) return;
      } else {
        if (source.durableDraftsEnabled.current && getDraft(source.session.project, "brief") && !await flushAuthoringDraft("brief")) return;
        const serverDraft = source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, "brief"));
        const consumed = canonicalDraftConsumption(serverDraft, "brief", source.session.project.revision, nextLocal.brief);
        const saved: { project: ProjectResource; consumedDraftRevision?: number } = consumed
          ? await plotloomApi.patchProjectWithDraft(source.session.project.id, source.session.project.revision, nextLocal.brief, consumed)
          : { project: await plotloomApi.patchProject(source.session.project.id, source.session.project.revision, nextLocal.brief) };
        if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
          source.session.serverDrafts.current.delete(authoringDraftKey(source.session.project.id, "brief"));
          setDurableDraftStatus("idle");
        } else if (!source.durableDraftsEnabled.current) {
          discardDraft(source.session.project, "brief");
        }
        if (!source.session.isCurrent(operation)) {
          refreshStaleAcceptedProject(source.session.project.id);
          return;
        }
        source.session.acceptCanonicalProject(mergeProjectResponse(nextLocal, saved.project));
        currentDraft.current = undefined;
        setRestoredDraft(undefined);
        return;
      }
      discardDraft(source.session.project, "brief");
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
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
  }, [beginSave, createProjectFrom, finishSave, flushAuthoringDraft, refreshStaleAcceptedProject]);

  const commitStage = useCallback(async <T,>(stage: ServerStageName, content: T) => {
    const generation = beginSave();
    if (!generation) return;
    const source = current.current;
    const operation = source.session.capture();
    const key = stage === "story_bible" ? "storyBible" : stage === "story_graph" ? "storyGraph" : stage === "scene_beats" ? "sceneBeats" : "storyboard";
    const nextLocal = markDownstreamStale(workspaceWithStageDraft(source.session.project, stage, content), stage);
    try {
      if (!source.session.project.id) {
        if (!await createProjectFrom(nextLocal, operation, stage)) return;
        source.session.clearValidationIssues();
        discardDraft(source.session.project, stage);
        currentDraft.current = undefined;
        setRestoredDraft(undefined);
        return;
      }
      if (source.durableDraftsEnabled.current && getDraft(source.session.project, stage) && !await flushAuthoringDraft(stage)) return;
      const serverDraft = source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, stage));
      const consumed = canonicalDraftConsumption(serverDraft, stage, source.session.project.stageRevisions[stage], content);
      const saved = consumed
        ? await plotloomApi.patchStageWithDraft(source.session.project.id, stage, source.session.project.stageRevisions[stage], content, consumed)
        : { stage: await plotloomApi.patchStage(source.session.project.id, stage, source.session.project.stageRevisions[stage], content) };
      if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
        source.session.serverDrafts.current.delete(authoringDraftKey(source.session.project.id, stage));
        setDurableDraftStatus("idle");
      } else if (!source.durableDraftsEnabled.current) {
        discardDraft(source.session.project, stage);
      }
      if (!source.session.isCurrent(operation)) {
        refreshStaleAcceptedProject(source.session.project.id);
        return;
      }
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
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
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
  }, [beginSave, createProjectFrom, finishSave, flushAuthoringDraft, refreshStaleAcceptedProject]);

  const rememberDraft = useCallback((scope: DraftScope, payload: unknown) => {
    const source = current.current;
    if (source.session.project.archivedAt) return;
    currentDraft.current = { scope, payload };
    const local = getDraft(source.session.project, scope);
    const recovered = source.session.project.id && restoredDraft?.scope === scope && restoredDraft.source === "server"
      ? source.session.serverDrafts.current.get(authoringDraftKey(source.session.project.id, scope))
      : undefined;
    putDraft(source.session.project, scope, payload, local?.serverDraftRevision ?? recovered?.draftRevision ?? 0);
    scheduleAuthoringDraftAutosave(scope);
    if (restoredDraft?.scope === scope) setRestoredDraft({ ...restoredDraft, payload });
  }, [restoredDraft, scheduleAuthoringDraftAutosave]);

  const reloadDraftConflict = useCallback(async () => {
    const conflict = draftConflict;
    const source = current.current;
    if (!conflict || !source.session.project.id) return false;
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict((existing) => existing ? { ...existing, serverReloaded: true } : existing);
    const epoch = source.session.refreshCurrentRoute();
    await source.session.reloadCanonicalProject(source.session.project.id, epoch);
    return true;
  }, [draftConflict]);

  const copyDraftConflict = useCallback(async () => {
    const conflict = draftConflict;
    if (!conflict) return false;
    const generation = beginSave();
    if (!generation) return false;
    const source = current.current;
    const operation = source.session.capture();
    const staged = conflict.scope === "brief"
      ? { ...conflict.workspace, brief: conflict.record.payload as WorkspaceProject["brief"] }
      : workspaceWithStageDraft(conflict.workspace, conflict.scope, conflict.record.payload);
    const copy: WorkspaceProject = {
      ...staged,
      id: undefined,
      clientDraftOwner: newClientDraftOwner(),
      revision: 0,
      lifecycleRevision: 0,
      lifecycleStatus: "active",
      archivedAt: null,
      brief: { ...staged.brief, title: `${staged.brief.title || "未命名项目"}（冲突副本）` },
    };
    try {
      const created = await createProjectFrom(copy, operation, conflict.scope === "brief" ? undefined : conflict.scope);
      if (!created) return false;
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
  }, [beginSave, createProjectFrom, draftConflict, finishSave]);

  const discardDraftConflict = useCallback(() => {
    if (!draftConflict) return false;
    discardDraftRecord(draftConflict.record);
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict(undefined);
    return true;
  }, [draftConflict]);
  const clearDraftWorkflow = useCallback(() => {
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict(undefined);
  }, []);

  return {
    currentDraft,
    projectSaving,
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
    createProjectFrom,
    reloadDraftConflict,
    copyDraftConflict,
    discardDraftConflict,
    clearDraftWorkflow,
  };
}
