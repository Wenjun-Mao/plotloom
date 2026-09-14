import { useCallback, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { ApiError, plotloomApi } from "../../api";
import { discardDraft, findProjectDrafts, getDraft, putDraft, type DraftRecord, type DraftScope } from "../../draft-registry";
import { markDownstreamStale, mergeProjectResponse, stageLabels } from "../../model";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "../../project-creation";
import { hydrateWorkspaceProject } from "../../workspace-state";
import { useAuthoringDraftAutosave } from "../../features/authoring/useAuthoringDraftAutosave";
import { authoringDraftKey, canonicalDraftConsumption, headsByStage, messageFrom, validationIssuesFrom, type DurableDraftStatus, type WorkspaceOperation } from "./contracts";
import type { AuthoringDraft, MediaTask, PipelineRun, ProjectResource, RunProgress, ServerStageName, StageHead, StoryboardReview, TraceEvent, ValidationIssue, WorkspaceProject } from "../../types";

export interface DraftConflictState {
  scope: DraftScope;
  record: DraftRecord;
  workspace: WorkspaceProject;
  serverReloaded: boolean;
}

type WorkspaceRoute = { project: string; stage: "brief" | "bible" | "graph" | "beats" | "storyboard" | "trace" | "quarantine"; entity: string; run: string };

interface ProjectAuthoringPersistenceInput {
  project: WorkspaceProject;
  connection: "loading" | "connected" | "demo" | "blank" | "error";
  workspace: {
    setProject: Dispatch<SetStateAction<WorkspaceProject>>;
    setStageHeads: Dispatch<SetStateAction<Partial<Record<ServerStageName, StageHead>>>>;
    setRun: Dispatch<SetStateAction<PipelineRun | undefined>>;
    setProgress: Dispatch<SetStateAction<RunProgress | undefined>>;
    setReview: Dispatch<SetStateAction<StoryboardReview | null>>;
    setIssues: Dispatch<SetStateAction<Partial<Record<ServerStageName, ValidationIssue[]>>>>;
    setTrace: Dispatch<SetStateAction<TraceEvent[]>>;
    setMediaTasks: Dispatch<SetStateAction<Record<string, MediaTask>>>;
    setConnection: (value: "loading" | "connected" | "demo" | "blank" | "error") => void;
  };
  feedback: {
    setBusy: (busy: boolean) => void;
    setError: Dispatch<SetStateAction<string>>;
  };
  route: {
    current: MutableRefObject<WorkspaceRoute>;
    capture: () => WorkspaceOperation;
    isCurrent: (operation: WorkspaceOperation) => boolean;
    invalidate: (next: WorkspaceRoute) => number;
    reload: (projectId: string, epoch?: number) => Promise<void>;
    canonicalRefreshRequired: MutableRefObject<Set<string>>;
  };
  drafts: {
    durableEnabled: MutableRefObject<boolean>;
    server: MutableRefObject<Map<string, AuthoringDraft>>;
    onConflict: () => void;
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
    project: input.project,
    durableDraftsEnabledRef: input.drafts.durableEnabled,
    serverAuthoringDrafts: input.drafts.server,
    captureWorkspaceOperation: input.route.capture,
    isWorkspaceOperationCurrent: input.route.isCurrent,
    setDurableDraftStatus,
    setError: input.feedback.setError,
    onConflict: (scope, record, workspace) => {
      setDraftConflict({ scope, record, workspace, serverReloaded: false });
      input.drafts.onConflict();
    },
  });

  const cancelSave = useCallback(() => {
    saveInFlight.current = false;
    activeGeneration.current = undefined;
    setProjectSaving(false);
  }, []);

  const beginSave = useCallback((): number | undefined => {
    const { project, feedback } = current.current;
    if (project.archivedAt) {
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
    if (!current.current.route.isCurrent(operation)) return;
    setProjectSaving(false);
    current.current.feedback.setBusy(false);
  }, []);

  const refreshStaleAcceptedProject = useCallback((projectId: string) => {
    const { route, feedback } = current.current;
    route.canonicalRefreshRequired.current.add(projectId);
    if (route.current.current.project !== projectId) return;
    if (currentDraft.current || findProjectDrafts(projectId).length) {
      feedback.setError("服务器已接受较早保存；当前草稿不会被覆盖。请先保存或丢弃当前草稿后切换阶段以刷新规范版本。");
      return;
    }
    const epoch = route.invalidate({ ...route.current.current });
    void route.reload(projectId, epoch);
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
    if (!source.route.isCurrent(operation)) return false;
    source.workspace.setProject(hydrateWorkspaceProject(nextLocal, created, created.stages));
    source.workspace.setStageHeads(headsByStage(created.stages));
    source.workspace.setRun(undefined);
    source.workspace.setProgress(undefined);
    source.workspace.setTrace([]);
    source.workspace.setMediaTasks({});
    source.workspace.setConnection("connected");
    if (created.id && created.stages.some((stage) => stage.head.stage === "storyboard" && stage.head.status === "ready")) {
      const review = await plotloomApi.getStoryboardReview(created.id).catch(() => null);
      if (!source.route.isCurrent(operation)) return false;
      if (review) source.workspace.setReview(review);
    }
    if (created.id) {
      const query = new URLSearchParams(location.search);
      query.set("project", created.id);
      history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
      source.route.current.current = { ...source.route.current.current, project: created.id };
    }
    createKeys.current.delete(body);
    cancelSave();
    source.feedback.setBusy(false);
    return true;
  }, [cancelSave]);

  const commitProject = useCallback(async (patch: Partial<WorkspaceProject>) => {
    const generation = beginSave();
    if (!generation) return;
    const source = current.current;
    const operation = source.route.capture();
    const nextLocal = mergeProjectResponse(source.project, patch);
    try {
      if (!source.project.id) {
        if (!await createProjectFrom(nextLocal, operation, nextLocal.initialStageOnFirstSave)) return;
      } else {
        if (source.drafts.durableEnabled.current && getDraft(source.project, "brief") && !await flushAuthoringDraft("brief")) return;
        const serverDraft = source.drafts.server.current.get(authoringDraftKey(source.project.id, "brief"));
        const consumed = canonicalDraftConsumption(serverDraft, "brief", source.project.revision, nextLocal.brief);
        const saved: { project: ProjectResource; consumedDraftRevision?: number } = consumed
          ? await plotloomApi.patchProjectWithDraft(source.project.id, source.project.revision, nextLocal.brief, consumed)
          : { project: await plotloomApi.patchProject(source.project.id, source.project.revision, nextLocal.brief) };
        if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
          source.drafts.server.current.delete(authoringDraftKey(source.project.id, "brief"));
          setDurableDraftStatus("idle");
        } else if (!source.drafts.durableEnabled.current) {
          discardDraft(source.project, "brief");
        }
        if (!source.route.isCurrent(operation)) {
          refreshStaleAcceptedProject(source.project.id);
          return;
        }
        source.workspace.setProject(mergeProjectResponse(nextLocal, saved.project));
        currentDraft.current = undefined;
        setRestoredDraft(undefined);
        return;
      }
      discardDraft(source.project, "brief");
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
    } catch (error) {
      if (!source.route.isCurrent(operation)) return;
      source.feedback.setError(messageFrom(error));
      if (error instanceof ApiError && error.status === 409) {
        const record = getDraft(source.project, "brief") ?? putDraft(source.project, "brief", nextLocal.brief);
        setDraftConflict({ scope: "brief", record, workspace: nextLocal, serverReloaded: false });
        source.drafts.onConflict();
      }
      if (source.connection === "demo") source.workspace.setProject((existing) => mergeProjectResponse(existing, patch));
    } finally {
      finishSave(operation, generation);
    }
  }, [beginSave, createProjectFrom, finishSave, flushAuthoringDraft, refreshStaleAcceptedProject]);

  const commitStage = useCallback(async <T,>(stage: ServerStageName, content: T) => {
    const generation = beginSave();
    if (!generation) return;
    const source = current.current;
    const operation = source.route.capture();
    const key = stage === "story_bible" ? "storyBible" : stage === "story_graph" ? "storyGraph" : stage === "scene_beats" ? "sceneBeats" : "storyboard";
    const nextLocal = markDownstreamStale(workspaceWithStageDraft(source.project, stage, content), stage);
    try {
      if (!source.project.id) {
        if (!await createProjectFrom(nextLocal, operation, stage)) return;
        source.workspace.setIssues((existing) => ({ ...existing, [stage]: [] }));
        discardDraft(source.project, stage);
        currentDraft.current = undefined;
        setRestoredDraft(undefined);
        return;
      }
      if (source.drafts.durableEnabled.current && getDraft(source.project, stage) && !await flushAuthoringDraft(stage)) return;
      const serverDraft = source.drafts.server.current.get(authoringDraftKey(source.project.id, stage));
      const consumed = canonicalDraftConsumption(serverDraft, stage, source.project.stageRevisions[stage], content);
      const saved: { stage: StageHead; consumedDraftRevision?: number } = consumed
        ? await plotloomApi.patchStageWithDraft(source.project.id, stage, source.project.stageRevisions[stage], content, consumed)
        : { stage: await plotloomApi.patchStage(source.project.id, stage, source.project.stageRevisions[stage], content) };
      if (consumed && saved.consumedDraftRevision === consumed.draftRevision) {
        source.drafts.server.current.delete(authoringDraftKey(source.project.id, stage));
        setDurableDraftStatus("idle");
      } else if (!source.drafts.durableEnabled.current) {
        discardDraft(source.project, stage);
      }
      if (!source.route.isCurrent(operation)) {
        refreshStaleAcceptedProject(source.project.id);
        return;
      }
      source.workspace.setProject((existing) => markDownstreamStale({ ...existing, [key]: content, stageRevisions: { ...existing.stageRevisions, [stage]: saved.stage.revision } }, stage));
      source.workspace.setStageHeads((existing) => ({ ...existing, [stage]: saved.stage }));
      source.workspace.setIssues((existing) => ({ ...existing, [stage]: [] }));
      if (stage === "storyboard") {
        const review = await plotloomApi.getStoryboardReview(source.project.id).catch(() => null);
        if (source.route.isCurrent(operation)) source.workspace.setReview(review);
      }
      currentDraft.current = undefined;
      setRestoredDraft(undefined);
    } catch (error) {
      if (!source.route.isCurrent(operation)) return;
      const issues = validationIssuesFrom(error);
      if (issues.length) {
        source.workspace.setIssues((existing) => ({ ...existing, [stage]: issues }));
        source.feedback.setError(`${stageLabels[stage]}未通过领域校验。已保留草稿并标出 ${issues.length} 个问题。`);
      } else {
        source.feedback.setError(messageFrom(error));
      }
      if (error instanceof ApiError && error.status === 409) {
        const record = getDraft(source.project, stage) ?? putDraft(source.project, stage, content);
        setDraftConflict({ scope: stage, record, workspace: nextLocal, serverReloaded: false });
        source.drafts.onConflict();
      }
      if (source.connection === "demo") source.workspace.setProject((existing) => markDownstreamStale(workspaceWithStageDraft(existing, stage, content), stage));
    } finally {
      finishSave(operation, generation);
    }
  }, [beginSave, createProjectFrom, finishSave, flushAuthoringDraft, refreshStaleAcceptedProject]);

  const rememberDraft = useCallback((scope: DraftScope, payload: unknown) => {
    const source = current.current;
    if (source.project.archivedAt) return;
    currentDraft.current = { scope, payload };
    const local = getDraft(source.project, scope);
    const recovered = source.project.id && restoredDraft?.scope === scope && restoredDraft.source === "server"
      ? source.drafts.server.current.get(authoringDraftKey(source.project.id, scope))
      : undefined;
    putDraft(source.project, scope, payload, local?.serverDraftRevision ?? recovered?.draftRevision ?? 0);
    scheduleAuthoringDraftAutosave(scope);
    if (restoredDraft?.scope === scope) setRestoredDraft({ ...restoredDraft, payload });
  }, [restoredDraft, scheduleAuthoringDraftAutosave]);

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
  };
}
