import { useCallback, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import type { DraftRecord, DraftScope } from "../../draft-registry";
import { hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "../../workspace-state";
import type { AuthoringDraft, MediaTask, PipelineRun, ProjectResource, RunExecutionTrace, RunProgress, ServerStageName, StageEnvelope, StageHead, StoryboardReview, TraceEvent, ValidationIssue, WorkspaceProject } from "../../types";
import { authoringDraftKey, blankWorkspace, headsByStage, newClientDraftOwner, routeFromLocation, type WorkspaceOperation } from "./contracts";

export type WorkspaceRoute = ReturnType<typeof routeFromLocation>;
export type ConnectionState = "loading" | "connected" | "demo" | "blank" | "error";
export type UnsafeDraft = { record: DraftRecord; reason: "archived" | "unavailable" };
export type RouteHistoryMode = "push" | "replace" | "none";

export interface WorkspaceProjectLoad {
  project: ProjectResource;
  stages: StageEnvelope[];
  run: PipelineRun | undefined;
  progress: RunProgress | undefined;
  review: StoryboardReview | null;
  media: MediaTask[];
  drafts: AuthoringDraft[];
}

interface CanonicalWorkspaceSnapshot {
  project: WorkspaceProject;
  connection: ConnectionState;
  run: PipelineRun | undefined;
  runSelectionPending: boolean;
  progress: RunProgress | undefined;
  review: StoryboardReview | null;
  issues: Partial<Record<ServerStageName, ValidationIssue[]>>;
  trace: TraceEvent[];
  executionTrace: RunExecutionTrace | undefined;
  mediaTasks: Record<string, MediaTask>;
  stageHeads: Partial<Record<ServerStageName, StageHead>>;
  onboarding: boolean;
  unsafeDraft: UnsafeDraft | undefined;
}

const isDraftScope = (value: string): value is DraftScope => (
  value === "brief"
  || value === "story_bible"
  || value === "story_graph"
  || value === "scene_beats"
  || value === "storyboard"
);

function emptySnapshot(owner: string, onboarding: boolean, connection: ConnectionState = "blank"): CanonicalWorkspaceSnapshot {
  return {
    project: blankWorkspace(owner),
    connection,
    run: undefined,
    runSelectionPending: false,
    progress: undefined,
    review: null,
    issues: {},
    trace: [],
    executionTrace: undefined,
    mediaTasks: {},
    stageHeads: {},
    onboarding,
    unsafeDraft: undefined,
  };
}

function writeRoute(route: WorkspaceRoute, mode: Exclude<RouteHistoryMode, "none">) {
  const query = new URLSearchParams();
  if (route.project) query.set("project", route.project);
  query.set("stage", route.stage);
  if (route.entity) query.set("entity", route.entity);
  if (route.run) query.set("run", route.run);
  const hash = route.hash ? `#${encodeURIComponent(route.hash)}` : "";
  history[`${mode}State`](null, "", `${location.pathname}?${query.toString()}${hash}`);
}

/**
 * Owns the only route epoch and canonical workspace snapshot. Domain hooks may
 * submit named transitions, but no caller receives individual snapshot setters.
 */
export function useWorkspaceSession() {
  const initialRoute = routeFromLocation();
  const localOwner = useRef(newClientDraftOwner());
  const [route, setRoute] = useState<WorkspaceRoute>(initialRoute);
  const routeRef = useRef(route);
  const epoch = useRef(0);
  const [snapshot, setSnapshot] = useState<CanonicalWorkspaceSnapshot>(() => emptySnapshot(localOwner.current, !initialRoute.project));
  const snapshotRef = useRef(snapshot);
  const navigationCleanups = useRef(new Set<() => void>());
  const serverDrafts = useRef(new Map<string, AuthoringDraft>());
  const canonicalRefreshRequired = useRef(new Set<string>());
  const canonicalReloader = useRef<(projectId: string, epoch?: number) => Promise<void>>(async () => undefined);

  const updateSnapshot = useCallback((update: (current: CanonicalWorkspaceSnapshot) => CanonicalWorkspaceSnapshot) => {
    setSnapshot((current) => {
      const next = update(current);
      snapshotRef.current = next;
      return next;
    });
  }, []);

  const capture = useCallback((): WorkspaceOperation => ({
    epoch: epoch.current,
    projectId: routeRef.current.project || snapshotRef.current.project.id || "",
    stage: routeRef.current.stage,
  }), []);
  const isCurrent = useCallback((operation: WorkspaceOperation): boolean => (
    operation.epoch === epoch.current
    && operation.projectId === routeRef.current.project
    && operation.stage === routeRef.current.stage
  ), []);
  const registerNavigationCleanup = useCallback((cleanup: () => void) => {
    navigationCleanups.current.add(cleanup);
    return () => { navigationCleanups.current.delete(cleanup); };
  }, []);
  const registerCanonicalReloader = useCallback((reload: (projectId: string, epoch?: number) => Promise<void>) => {
    canonicalReloader.current = reload;
    return () => {
      if (canonicalReloader.current === reload) canonicalReloader.current = async () => undefined;
    };
  }, []);
  const reloadCanonicalProject = useCallback((projectId: string, epoch?: number) => canonicalReloader.current(projectId, epoch), []);

  const navigate = useCallback((next: WorkspaceRoute, historyMode: RouteHistoryMode = "none") => {
    // Advance before informing any cleanup owner or rendering the next route.
    // A late load, poll, or save can therefore never match the new session.
    epoch.current += 1;
    navigationCleanups.current.forEach((cleanup) => cleanup());
    routeRef.current = next;
    setRoute(next);
    if (historyMode !== "none") writeRoute(next, historyMode);
    return epoch.current;
  }, []);
  const refreshCurrentRoute = useCallback(() => navigate({ ...routeRef.current }), [navigate]);
  const navigateToProject = useCallback((next: WorkspaceRoute, historyMode: RouteHistoryMode) => {
    const changedProject = next.project !== routeRef.current.project;
    const epoch = navigate(next, historyMode);
    updateSnapshot((current) => ({
      ...current,
      onboarding: false,
      review: changedProject ? null : current.review,
      issues: changedProject ? {} : current.issues,
    }));
    return epoch;
  }, [navigate, updateSnapshot]);
  const focusEntity = useCallback((entity: string) => {
    if (entity === routeRef.current.entity) return;
    const next = { ...routeRef.current, entity };
    routeRef.current = next;
    setRoute(next);
    writeRoute(next, "push");
  }, []);
  const updateRouteHash = useCallback((hash: string) => {
    if (hash === routeRef.current.hash) return;
    const next = { ...routeRef.current, hash };
    routeRef.current = next;
    setRoute(next);
  }, []);
  const navigateHash = useCallback((hash: string) => {
    if (hash === routeRef.current.hash) return;
    const next = { ...routeRef.current, hash };
    routeRef.current = next;
    setRoute(next);
    writeRoute(next, "push");
  }, []);
  const replaceCurrentRoute = useCallback(() => writeRoute(routeRef.current, "replace"), []);

  const beginProjectLoad = useCallback(() => {
    updateSnapshot((current) => ({ ...current, connection: "loading" }));
  }, [updateSnapshot]);
  const acceptProjectLoad = useCallback((incoming: WorkspaceProjectLoad) => {
    serverDrafts.current = new Map(
      incoming.drafts
        .filter((draft): draft is AuthoringDraft & { editorScope: DraftScope } => isDraftScope(draft.editorScope))
        .map((draft) => [authoringDraftKey(incoming.project.id, draft.editorScope), draft]),
    );
    updateSnapshot((current) => ({
      ...current,
      project: {
        ...hydrateWorkspaceProject(current.project, incoming.project, incoming.stages),
        quarantines: quarantineItemsFromProgress(incoming.progress),
      },
      connection: "connected",
      run: incoming.run,
      runSelectionPending: false,
      progress: incoming.progress,
      review: incoming.review,
      issues: {},
      trace: [],
      executionTrace: undefined,
      mediaTasks: newestMediaTasksByShot(incoming.media),
      stageHeads: headsByStage(incoming.stages),
      onboarding: false,
    }));
  }, [updateSnapshot]);
  const rejectProjectLoad = useCallback((staleDraft: UnsafeDraft | undefined) => {
    if (staleDraft) serverDrafts.current.clear();
    updateSnapshot((current) => ({
      ...emptySnapshot(localOwner.current, false, "error"),
      unsafeDraft: staleDraft ?? current.unsafeDraft,
    }));
  }, [updateSnapshot]);

  const clearTrace = useCallback(() => {
    updateSnapshot((current) => ({ ...current, trace: [], executionTrace: undefined }));
  }, [updateSnapshot]);
  const acceptRunProgress = useCallback((runId: string, progress: RunProgress) => {
    updateSnapshot((current) => ({
      ...current,
      progress,
      run: current.run?.id === runId
        ? { ...current.run, status: progress.status, failureCode: progress.failureCode, failedStage: progress.failedStage }
        : current.run,
      project: { ...current.project, quarantines: quarantineItemsFromProgress(progress) },
    }));
  }, [updateSnapshot]);
  const acceptRun = useCallback((run: PipelineRun | undefined) => {
    updateSnapshot((current) => ({ ...current, run, runSelectionPending: false }));
  }, [updateSnapshot]);
  const beginRunSelection = useCallback((runId: string) => {
    updateSnapshot((current) => {
      // An empty run ID means "resolve the latest run for this trace route".
      // It is still a selection, even when no run is currently projected.
      if (runId && runId === current.run?.id && !current.runSelectionPending) return current;
      return {
        ...current,
        run: runId === current.run?.id ? current.run : undefined,
        runSelectionPending: true,
        progress: undefined,
        trace: [],
        executionTrace: undefined,
      };
    });
  }, [updateSnapshot]);
  const cancelRunSelection = useCallback(() => {
    updateSnapshot((current) => {
      if (!current.runSelectionPending) return current;
      return {
        ...current,
        connection: current.connection === "loading" && current.project.id ? "connected" : current.connection,
        run: undefined,
        runSelectionPending: false,
        progress: undefined,
        trace: [],
        executionTrace: undefined,
      };
    });
  }, [updateSnapshot]);
  const acceptTraceEvidence = useCallback((trace: TraceEvent[], executionTrace: RunExecutionTrace | undefined) => {
    updateSnapshot((current) => ({ ...current, trace, executionTrace }));
  }, [updateSnapshot]);

  const acceptCanonicalProject = useCallback((project: WorkspaceProject) => {
    updateSnapshot((current) => ({ ...current, project }));
  }, [updateSnapshot]);
  const acceptCanonicalStage = useCallback((project: WorkspaceProject, stage: ServerStageName, head: StageHead) => {
    updateSnapshot((current) => ({
      ...current,
      project,
      stageHeads: { ...current.stageHeads, [stage]: head },
      issues: { ...current.issues, [stage]: [] },
    }));
  }, [updateSnapshot]);
  const acceptStoryboardReview = useCallback((review: StoryboardReview | null) => {
    updateSnapshot((current) => ({ ...current, review }));
  }, [updateSnapshot]);
  const showValidationIssues = useCallback((stage: ServerStageName, issues: ValidationIssue[]) => {
    updateSnapshot((current) => ({ ...current, issues: { ...current.issues, [stage]: issues } }));
  }, [updateSnapshot]);
  const clearValidationIssues = useCallback(() => {
    updateSnapshot((current) => ({ ...current, issues: {} }));
  }, [updateSnapshot]);
  const applyDemoSave = useCallback((project: WorkspaceProject) => {
    updateSnapshot((current) => ({ ...current, project }));
  }, [updateSnapshot]);

  const acceptCreatedProject = useCallback((draft: WorkspaceProject, created: ProjectResource & { stages: StageEnvelope[] }, review: StoryboardReview | null) => {
    const nextRoute = { ...routeRef.current, project: created.id };
    // Persisting a local draft creates a new route identity as well as a
    // canonical snapshot. It must advance the same epoch as every other
    // project transition so an older local operation cannot paint afterward.
    navigate(nextRoute);
    // Preserve the established blank-workspace query order (`stage` before the
    // newly assigned project ID) so the first-save route remains byte-stable.
    const query = new URLSearchParams(location.search);
    query.set("stage", nextRoute.stage);
    query.set("project", created.id);
    if (nextRoute.entity) query.set("entity", nextRoute.entity);
    if (nextRoute.run) query.set("run", nextRoute.run);
    history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
    serverDrafts.current.clear();
    updateSnapshot((current) => ({
      ...current,
      project: hydrateWorkspaceProject(draft, created, created.stages),
      connection: "connected",
      run: undefined,
      runSelectionPending: false,
      progress: undefined,
      review,
      issues: {},
      trace: [],
      executionTrace: undefined,
      mediaTasks: {},
      stageHeads: headsByStage(created.stages),
      onboarding: false,
    }));
  }, [navigate, updateSnapshot]);

  const startLocalWorkspace = useCallback((next: WorkspaceRoute, local: {
    project: WorkspaceProject;
    connection: "blank" | "demo";
    run?: PipelineRun;
    trace?: TraceEvent[];
    onboarding: boolean;
  }) => {
    navigate(next, "push");
    localOwner.current = newClientDraftOwner();
    serverDrafts.current.clear();
    updateSnapshot(() => ({
      ...emptySnapshot(localOwner.current, local.onboarding, local.connection),
      project: { ...local.project, clientDraftOwner: localOwner.current },
      run: local.run,
      trace: local.trace || [],
    }));
  }, [navigate, updateSnapshot]);
  const clearForEmptyRoute = useCallback((next: WorkspaceRoute, historyMode: RouteHistoryMode = "none") => {
    navigate(next, historyMode);
    localOwner.current = newClientDraftOwner();
    serverDrafts.current.clear();
    updateSnapshot(() => emptySnapshot(localOwner.current, true));
  }, [navigate, updateSnapshot]);

  const setUnsafeDraft = useCallback((unsafeDraft: UnsafeDraft | undefined) => {
    updateSnapshot((current) => ({ ...current, unsafeDraft }));
  }, [updateSnapshot]);
  const markCanonicalRefreshRequired = useCallback((projectId: string) => canonicalRefreshRequired.current.add(projectId), []);
  const clearCanonicalRefresh = useCallback((projectId: string) => canonicalRefreshRequired.current.delete(projectId), []);
  const needsCanonicalRefresh = useCallback((projectId: string) => canonicalRefreshRequired.current.has(projectId), []);

  return {
    route,
    routeRef,
    epoch,
    activePage: route.stage,
    routeEntity: route.entity,
    project: snapshot.project,
    connection: snapshot.connection,
    run: snapshot.run,
    runSelectionPending: snapshot.runSelectionPending,
    progress: snapshot.progress,
    review: snapshot.review,
    issues: snapshot.issues,
    trace: snapshot.trace,
    executionTrace: snapshot.executionTrace,
    mediaTasks: snapshot.mediaTasks,
    stageHeads: snapshot.stageHeads,
    onboarding: snapshot.onboarding,
    unsafeDraft: snapshot.unsafeDraft,
    serverDrafts,
    capture,
    isCurrent,
    registerNavigationCleanup,
    registerCanonicalReloader,
    reloadCanonicalProject,
    navigate,
    refreshCurrentRoute,
    navigateToProject,
    focusEntity,
    updateRouteHash,
    navigateHash,
    replaceCurrentRoute,
    beginProjectLoad,
    acceptProjectLoad,
    rejectProjectLoad,
    clearTrace,
    acceptRunProgress,
    acceptRun,
    beginRunSelection,
    cancelRunSelection,
    acceptTraceEvidence,
    acceptCanonicalProject,
    acceptCanonicalStage,
    acceptStoryboardReview,
    showValidationIssues,
    clearValidationIssues,
    applyDemoSave,
    acceptCreatedProject,
    startLocalWorkspace,
    clearForEmptyRoute,
    setUnsafeDraft,
    markCanonicalRefreshRequired,
    clearCanonicalRefresh,
    needsCanonicalRefresh,
  };
}

export type WorkspaceSession = ReturnType<typeof useWorkspaceSession>;
export type WorkspaceDraftMap = MutableRefObject<Map<string, AuthoringDraft>>;
