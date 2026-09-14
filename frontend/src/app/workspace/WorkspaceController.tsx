import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AuthoringDraft, CanonicalDraftConsumption, MediaTask, PipelineRun, ProjectListItem, ProjectResource, ProviderSettings, QuarantineItem, RunExecutionTrace, RunProgress, SceneBeatPlan, ServerStageName, StageEnvelope, StageHead, StoryBible, StoryGraph, Storyboard, StoryboardReview, TextBackendReadiness, TextProviderPresetId, TextProviderProfileConfiguration, TextProviderProfilesResponse, TextProviderProfileView, TraceEvent, ValidationIssue, WorkspaceProject } from "../../types";
import { plotloomApi, ApiError } from "../../api";
import { providerSessionKeys } from "../../session-key";
import { defaultProviderSettings, demoProject, demoRun, demoTrace, emptyStageContent } from "../../demo";
import { acknowledgeDraft, discardDraft, discardDraftRecord, findProjectDrafts, findRevisionConflict, getDraft, hasDraft, putDraft, type DraftRecord, type DraftScope } from "../../draft-registry";
import { markDownstreamStale, mergeProjectResponse, stageLabels, traceEvents } from "../../model";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "../../project-creation";
import { editorRevisionKey, hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "../../workspace-state";
import { Badge, Button, ErrorNotice, Spinner } from "../../components";
import { BriefPage } from "../../pages/BriefPage";
import { StoryBiblePage } from "../../pages/StoryBiblePage";
import { GraphPage } from "../../pages/GraphPage";
import { SceneBeatsPage } from "../../pages/SceneBeatsPage";
import { StoryboardPage } from "../../pages/StoryboardPage";
import { TracePage } from "../../pages/TracePage";
import { QuarantinePage } from "../../pages/QuarantinePage";
import { useAuthoringDraftAutosave } from "../../features/authoring/useAuthoringDraftAutosave";
import { DraftConflictDialog, DraftNavigationDialog, DraftRecoveryDialog, ProjectDirectoryDialog, RebuildDialog, SettingsDialog, UnsafeDraftDialog, WelcomeOnboarding, WorkspaceInspector } from "./WorkspaceViews";
import { useTextProviderProfiles } from "./useTextProviderProfiles";
import { useProjectDirectory } from "./useProjectDirectory";
import { useRunSession } from "./useRunSession";
import { useRunCommands } from "./useRunCommands";
import { useWorkspaceProjectLoader } from "./useWorkspaceProjectLoader";
import { useProjectAuthoringPersistence } from "./useProjectAuthoringPersistence";
import { useWorkspaceNavigation } from "./useWorkspaceNavigation";
import { useAuthoringDraftRecovery } from "./useAuthoringDraftRecovery";
import { useProjectLifecycle } from "./useProjectLifecycle";
import { authoringDraftKey, blankWorkspace, canonicalDraftConsumption, editableStages, headsByStage, messageFrom, navigation, newClientDraftOwner, routeFromLocation, stageForPage, type DraftRecoverySource, type DurableDraftStatus, type NavigationTarget, type PageId, type WorkspaceOperation, validationIssuesFrom } from "./contracts";

interface DraftConflictState {
  scope: DraftScope;
  record: DraftRecord;
  workspace: WorkspaceProject;
  serverReloaded: boolean;
}


export default function App() {
  const localWorkspaceOwner = useRef(newClientDraftOwner());
  const visibleRoute = useRef(routeFromLocation());
  const [activePage, setActivePage] = useState<PageId>(() => routeFromLocation().stage);
  const [project, setProject] = useState<WorkspaceProject>(() => blankWorkspace(localWorkspaceOwner.current));
  const [connection, setConnection] = useState<"loading" | "connected" | "demo" | "blank" | "error">("blank");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState<PipelineRun | undefined>();
  const [runProgress, setRunProgress] = useState<RunProgress | undefined>();
  const [storyboardReview, setStoryboardReview] = useState<StoryboardReview | null>(null);
  const [validationIssues, setValidationIssues] = useState<Partial<Record<ServerStageName, ValidationIssue[]>>>({});
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [mediaTasks, setMediaTasks] = useState<Record<string, MediaTask>>({});
  const [rebuildOpen, setRebuildOpen] = useState(false);
  const profileOwner = useTextProviderProfiles(setBusy, setError, messageFrom);
  const { profiles, selectedProfileId, profileDraft, profileDirty, sessionKey, settingsOpen, setSettingsOpen, setProfileDraft, setSessionKey, setProfileDirty, loaded: profilesLoaded, catalog: profileCatalog, install: installProfiles, refresh: refreshProfiles, save: saveProfile, saveCurrent: saveCurrentProfile, openSettings, select: selectProfile, create: createProfile, activate: activateProfile, setAvailability: setProfileAvailability, remove: deleteProfile, probe: testProfile, openFrozen: openFrozenProfileSettings, ensureFrozenCredential: ensureFrozenRunCredential } = profileOwner;
  const [executionTrace, setExecutionTrace] = useState<RunExecutionTrace | undefined>();
  const [stageHeads, setStageHeads] = useState<Partial<Record<ServerStageName, StageHead>>>({});
  const directory = useProjectDirectory(messageFrom);
  const { projects, open: directoryOpen, setOpen: setDirectoryOpen, showArchived, setShowArchived, error: directoryError, setError: setDirectoryError, nextCursor: nextProjectCursor, loading: directoryLoading, refresh: refreshProjectDirectory, openDirectory, loadMore: loadMoreProjects } = directory;
  const [routeEntity, setRouteEntity] = useState(() => routeFromLocation().entity);
  const [unsafeDraft, setUnsafeDraft] = useState<{ record: DraftRecord; reason: "archived" | "unavailable" } | undefined>();
  const [pendingNavigation, setPendingNavigation] = useState<NavigationTarget | undefined>();
  const [durableDraftsEnabled, setDurableDraftsEnabled] = useState(false);
  const [durableMediaDraftsEnabled, setDurableMediaDraftsEnabled] = useState(false);
  const [onboarding, setOnboarding] = useState(() => !routeFromLocation().project);
  const loadEpoch = useRef(0);
  const canonicalRefreshRequired = useRef(new Set<string>());
  // Navigation owns when a load is no longer relevant; the loader owns the
  // controller itself. This narrow ref is the intentional cancellation seam.
  const abortProjectLoad = useRef<() => void>(() => undefined);
  const cancelProjectSave = useRef<() => void>(() => undefined);
  // A completed run refreshes canonical state through the loader. The stable
  // forwarding function avoids a polling loop retaining a superseded loader.
  const reloadProject = useRef<(projectId: string, epoch?: number) => Promise<void>>(async () => undefined);
  const durableDraftsEnabledRef = useRef(false);
  const serverAuthoringDrafts = useRef(new Map<string, AuthoringDraft>());

  const captureWorkspaceOperation = (): WorkspaceOperation => ({
    epoch: loadEpoch.current,
    // During a hard refresh, the URL is the only project identity available
    // until the first canonical response hydrates React state.  A user action
    // in that interval must remain scoped to the URL project, never silently
    // become an untitled local workspace.
    projectId: visibleRoute.current.project || project.id || "",
    stage: activePage,
  });
  const isWorkspaceOperationCurrent = (operation: WorkspaceOperation): boolean => (
    operation.epoch === loadEpoch.current
    && operation.projectId === visibleRoute.current.project
    && operation.stage === visibleRoute.current.stage
  );
  const invalidateWorkspaceNavigation = (next: ReturnType<typeof routeFromLocation>): number => {
    // Increment before any state update or request starts. A delayed write may
    // still finish on the server, but it can no longer repaint this workspace.
    loadEpoch.current += 1;
    abortProjectLoad.current();
    visibleRoute.current = next;
    cancelProjectSave.current();
    setBusy(false);
    return loadEpoch.current;
  };

  const reloadCanonicalProject = useCallback(
    (projectId: string, epoch?: number) => reloadProject.current(projectId, epoch),
    [],
  );
  const { pollRun, loadTraceEvidence, resetTrace } = useRunSession({
    loadEpoch,
    visibleRoute,
    isCurrent: isWorkspaceOperationCurrent,
    setProject,
    setRun,
    setProgress: setRunProgress,
    setTrace,
    setExecutionTrace,
    reloadProject: reloadCanonicalProject,
    setError,
    describeError: messageFrom,
  });
  const observeRun = useCallback((runId: string, projectId: string) => {
    void pollRun(runId, projectId).catch((error) => setError(messageFrom(error)));
  }, [pollRun]);
  const projectLoader = useWorkspaceProjectLoader({
    loadEpoch,
    route: visibleRoute,
    localOwner: localWorkspaceOwner,
    durableDrafts: durableDraftsEnabledRef,
    profiles: { loaded: profilesLoaded, catalog: profileCatalog },
    session: {
      beginProjectLoad: () => setConnection("loading"),
      acceptProjectLoad: ({ project: incoming, stages, run: loadedRun, progress, review, media, drafts, message }) => {
        setProject((current) => ({ ...hydrateWorkspaceProject(current, incoming, stages), quarantines: quarantineItemsFromProgress(progress) }));
        setStageHeads(headsByStage(stages)); setRun(loadedRun); setRunProgress(progress); setStoryboardReview(review); setValidationIssues({}); resetTrace(); setMediaTasks(newestMediaTasksByShot(media));
        serverAuthoringDrafts.current = new Map(drafts.filter((draft): draft is AuthoringDraft & { editorScope: DraftScope } => ["brief", "story_bible", "story_graph", "scene_beats", "storyboard"].includes(draft.editorScope)).map((draft) => [authoringDraftKey(incoming.id, draft.editorScope), draft]));
        setConnection("connected"); setOnboarding(false); setError(message);
      },
      rejectProjectLoad: (projectId, loadError, staleDraft) => {
        if (staleDraft) setUnsafeDraft(staleDraft);
        setProject(blankWorkspace(localWorkspaceOwner.current)); setStageHeads({}); setRun(undefined); setRunProgress(undefined); setStoryboardReview(null); setValidationIssues({}); resetTrace(); setMediaTasks({}); setConnection("error"); setOnboarding(false); setError(`无法加载项目 ${projectId}：${messageFrom(loadError)}。项目未加载；没有回退到示例。`);
      },
      clearCanonicalRefresh: (projectId) => canonicalRefreshRequired.current.delete(projectId),
    },
    serverDrafts: serverAuthoringDrafts,
    observeRun,
    onLoaded: (projectId) => canonicalRefreshRequired.current.delete(projectId),
  });
  const { loadProject } = projectLoader;
  reloadProject.current = loadProject;
  abortProjectLoad.current = projectLoader.abort;
  const authoring = useProjectAuthoringPersistence({
    project,
    connection,
    workspace: {
      setProject,
      setStageHeads,
      setRun,
      setProgress: setRunProgress,
      setReview: setStoryboardReview,
      setIssues: setValidationIssues,
      setTrace,
      setMediaTasks,
      setConnection,
    },
    feedback: { setBusy, setError },
    route: {
      current: visibleRoute,
      capture: captureWorkspaceOperation,
      isCurrent: isWorkspaceOperationCurrent,
      invalidate: invalidateWorkspaceNavigation,
      reload: loadProject,
      canonicalRefreshRequired,
    },
    drafts: {
      durableEnabled: durableDraftsEnabledRef,
      server: serverAuthoringDrafts,
      onConflict: () => {
        setPendingNavigation(undefined);
      },
    },
  });
  const {
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
    beginSave: beginProjectSave,
    finishSave: finishProjectSave,
    createProjectFrom,
  } = authoring;
  cancelProjectSave.current = authoring.cancelSave;
  const draftRecoveryOwner = useAuthoringDraftRecovery({
    activePage,
    project,
    durableEnabled: durableDraftsEnabled,
    serverDrafts: serverAuthoringDrafts,
    currentDraft,
    restoredDraft,
    setRestoredDraft,
    draftConflict,
    setDraftConflict,
    unsafeDraft,
    setUnsafeDraft,
    scheduleAutosave: scheduleAuthoringDraftAutosave,
    setError,
  });
  const { recovery: draftRecovery, setRecovery: setDraftRecovery, editorNonce, restore: restoreDraftRecovery, discard: discardDraftRecovery, bumpEditorNonce } = draftRecoveryOwner;
  const { applyNavigation, requestNavigation, selectRouteEntity, resolvePendingNavigation } = useWorkspaceNavigation({
    state: {
      route: visibleRoute,
      activePage,
      setActivePage,
      routeEntity,
      setRouteEntity,
      pending: pendingNavigation,
      setPending: setPendingNavigation,
    },
    workspace: {
      project,
      run,
      localOwner: localWorkspaceOwner,
      setProject,
      setStageHeads,
      setRun,
      setProgress: setRunProgress,
      setReview: setStoryboardReview,
      setIssues: setValidationIssues,
      setTrace,
      setMediaTasks,
      setConnection,
      setOnboarding,
    },
    drafts: {
      current: currentDraft,
      durableEnabled: durableDraftsEnabledRef,
      flush: flushAuthoringDraft,
      commitProject,
      commitStage,
      clearRecovery: () => setDraftRecovery(undefined),
      clearConflict: () => setDraftConflict(undefined),
      unsafe: unsafeDraft,
      setUnsafe: setUnsafeDraft,
    },
    loader: {
      invalidate: invalidateWorkspaceNavigation,
      loadProject,
      canonicalRefreshRequired,
    },
  });

  useEffect(() => {
    const initialRoute = routeFromLocation();
    const epoch = invalidateWorkspaceNavigation(initialRoute);
    if (initialRoute.project) void loadProject(initialRoute.project, epoch);
  // This runs once: navigation is owned by requestNavigation/popstate below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadProject]);
  useEffect(() => {
    void plotloomApi.getAuthoringDraftCapability()
      .then((capability) => {
        durableDraftsEnabledRef.current = capability.durableProjectDrafts === true;
        setDurableDraftsEnabled(durableDraftsEnabledRef.current);
        setDurableMediaDraftsEnabled(capability.durableMediaDrafts === true);
        // The direct folder composition deliberately has no installation-wide
        // profile registry. Do not probe that excluded authority merely to
        // fill a sidebar that the still/image workflow does not use.
        if (!durableDraftsEnabledRef.current) {
          void refreshProfiles().catch(() => undefined);
        }
        if (durableDraftsEnabledRef.current && visibleRoute.current.project) {
          const epoch = invalidateWorkspaceNavigation({ ...visibleRoute.current });
          void loadProject(visibleRoute.current.project, epoch);
        }
      })
      // The retained runtime intentionally does not expose this test-only
      // storage composition.  Absence is not a user-switchable mode.
      .catch(() => {
        durableDraftsEnabledRef.current = false;
        setDurableDraftsEnabled(false);
        setDurableMediaDraftsEnabled(false);
        void refreshProfiles().catch(() => undefined);
      });
  }, [loadProject, refreshProfiles]);
  useEffect(() => {
    if (activePage !== "trace" || !run?.id) return;
    void loadTraceEvidence(run.id, run.projectId);
  }, [activePage, loadTraceEvidence, run?.id, run?.projectId]);
  useEffect(() => {
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!currentDraft.current) return;
      event.preventDefault(); event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, []);

  const showRunTrace = (nextRun: PipelineRun, resetEvidence = true) => {
    const nextRoute = { project: nextRun.projectId, stage: "trace" as const, entity: "", run: nextRun.id };
    invalidateWorkspaceNavigation(nextRoute);
    history.pushState(null, "", `${location.pathname}?${new URLSearchParams({ project: nextRun.projectId, stage: "trace", run: nextRun.id }).toString()}`);
    currentDraft.current = undefined;
    setActivePage("trace"); setRouteEntity(""); setDraftRecovery(undefined); setRestoredDraft(undefined); setDraftConflict(undefined);
    setRun(nextRun); setRunProgress(undefined); if (resetEvidence) resetTrace(); setRebuildOpen(false);
    void pollRun(nextRun.id, nextRun.projectId).catch((error) => setError(messageFrom(error)));
  };
  const { startRun, cancelRun, resumeRun, repair, rebuild } = useRunCommands({
    project,
    activePage,
    run,
    profiles: { draft: profileDraft, sessionKey, loaded: profilesLoaded, refresh: refreshProfiles, save: saveProfile, ensureFrozenCredential: ensureFrozenRunCredential },
    currentness: { capture: captureWorkspaceOperation, isCurrent: isWorkspaceOperationCurrent },
    pollRun,
    openTrace: showRunTrace,
    setRun,
    setBusy,
    setError,
    hasDraft: (scope) => scope ? hasDraft(project, scope) : false,
  });

  const saveSettings = async () => {
    setBusy(true);
    try { await saveCurrentProfile(); setSettingsOpen(false); }
    catch (settingsError) { setError(messageFrom(settingsError)); }
    finally { setBusy(false); }
  };

  const startBlankProject = () => {
    const route = routeFromLocation();
    const nextRoute = { project: "", stage: route.stage, entity: "", run: "" };
    invalidateWorkspaceNavigation(nextRoute);
    localWorkspaceOwner.current = newClientDraftOwner();
    setProject(blankWorkspace(localWorkspaceOwner.current)); setStageHeads({}); setRun(undefined); setRunProgress(undefined); setStoryboardReview(null); setValidationIssues({}); setTrace([]); setMediaTasks({}); setConnection("blank");
    currentDraft.current = undefined; setDraftRecovery(undefined); setRestoredDraft(undefined); setDraftConflict(undefined); setUnsafeDraft(undefined); setActivePage(route.stage); setRouteEntity(""); setOnboarding(false);
    history.pushState(null, "", `${location.pathname}?stage=${encodeURIComponent(route.stage)}`);
    setDirectoryOpen(false);
  };

  const openSampleProject = () => {
    const route = routeFromLocation();
    const nextRoute = { project: "", stage: route.stage, entity: "", run: "" };
    invalidateWorkspaceNavigation(nextRoute);
    localWorkspaceOwner.current = newClientDraftOwner();
    // A teaching sample is a complete, validated canonical workspace. Its
    // first save must preserve that prefix even when the author starts on the
    // Brief page; blank workspaces intentionally leave this unset.
    setProject({ ...demoProject, clientDraftOwner: localWorkspaceOwner.current, initialStageOnFirstSave: "storyboard" }); setStageHeads({}); setRun(demoRun); setRunProgress(undefined); setStoryboardReview(null); setValidationIssues({}); setTrace(demoTrace); setConnection("demo");
    currentDraft.current = undefined; setDraftRecovery(undefined); setRestoredDraft(undefined); setDraftConflict(undefined); setUnsafeDraft(undefined); setActivePage(route.stage); setRouteEntity(""); setOnboarding(false);
    history.pushState(null, "", `${location.pathname}?stage=${encodeURIComponent(route.stage)}`);
    setDirectoryOpen(false);
  };

  const lifecycle = useProjectLifecycle({
    project,
    activePage,
    currentDraft,
    commitProject,
    commitStage,
    capture: captureWorkspaceOperation,
    isCurrent: isWorkspaceOperationCurrent,
    setProject,
    directory: { setOpen: setDirectoryOpen, refresh: refreshProjectDirectory, setError: setDirectoryError },
    openProject: (projectId) => requestNavigation({ project: projectId, stage: "brief" }),
    startBlank: startBlankProject,
  });
  const { pendingArchive, mutate: mutateProjectLifecycle, resolvePendingArchive } = lifecycle;

  const reloadConflictServer = async () => {
    if (!draftConflict || !project.id) return;
    currentDraft.current = undefined;
    setRestoredDraft(undefined);
    setDraftConflict((current) => current ? { ...current, serverReloaded: true } : current);
    const epoch = invalidateWorkspaceNavigation({ ...visibleRoute.current });
    await loadProject(project.id, epoch);
  };

  const copyConflictAsProject = async () => {
    if (!draftConflict) return;
    const saveGeneration = beginProjectSave();
    if (!saveGeneration) return;
    const operation = captureWorkspaceOperation();
    const staged = draftConflict.scope === "brief"
      ? { ...draftConflict.workspace, brief: draftConflict.record.payload as WorkspaceProject["brief"] }
      : workspaceWithStageDraft(draftConflict.workspace, draftConflict.scope, draftConflict.record.payload);
    const copy: WorkspaceProject = {
      ...staged,
      id: undefined,
      clientDraftOwner: newClientDraftOwner(),
      revision: 0,
      lifecycleRevision: 0,
      lifecycleStatus: "active",
      archivedAt: null,
      brief: {
        ...staged.brief,
        title: `${staged.brief.title || "未命名项目"}（冲突副本）`,
      },
    };
    try {
      const created = await createProjectFrom(
        copy,
        operation,
        draftConflict.scope === "brief" ? undefined : draftConflict.scope,
      );
      if (!created) return;
      discardDraftRecord(draftConflict.record);
      currentDraft.current = undefined;
      setDraftConflict(undefined);
      setValidationIssues({});
      bumpEditorNonce();
    } catch (copyError) {
      if (!isWorkspaceOperationCurrent(operation)) return;
      const issues = validationIssuesFrom(copyError);
      if (issues.length && draftConflict.scope !== "brief") {
        setValidationIssues((current) => ({ ...current, [draftConflict.scope as ServerStageName]: issues }));
      }
      setError(`无法创建冲突副本：${messageFrom(copyError)}`);
    } finally {
      finishProjectSave(operation, saveGeneration);
    }
  };

  const requestProjectRefresh = () => {
    if (!project.id) { setError("空白项目尚无可刷新的服务器版本。"); return; }
    requestNavigation({
      project: project.id,
      stage: activePage,
      entity: routeEntity,
      run: activePage === "trace" ? run?.id || "" : "",
      history: "pop",
      forceReload: true,
    });
  };

  const staleCount = project.staleStages.length;
  const currentNav = navigation.find((item) => item.id === activePage)!;
  const running = run?.status === "queued" || run?.status === "running" || run?.status === "cancel_requested";
  const frozenProfileId = run ? String(run.providerSnapshot.profileId || "default") : "";
  const frozenProfile = profiles.profiles.find((profile) => profile.profileId === frozenProfileId);
  const frozenProfileNeedsKey = Boolean(run && run.providerSnapshot.textAuthMode !== "none" && !frozenProfile?.serverKeyAvailable && !providerSessionKeys.read(frozenProfileId));
  // URL state is authoritative for workspace navigation.  `project.id` only
  // becomes available after hydration, so it cannot be the source here.
  const navigationProjectId = visibleRoute.current.project || project.id || "";
  // A persisted URL project must not briefly expose the blank teaching draft
  // while its canonical payload is in flight. Apart from misleading authors,
  // that provisional editor can accept input which is then discarded when the
  // real project's revision remounts the stage editor.
  const workspaceHydrating = connection === "loading"
    && Boolean(navigationProjectId)
    && project.id !== navigationProjectId;
  const recoveredValue = <T,>(scope: DraftScope, canonical: T): T => restoredDraft?.scope === scope ? restoredDraft.payload as T : canonical;
  const projectReadOnly = project.lifecycleStatus === "archived" || Boolean(project.archivedAt);
  const stageOverview = editableStages.map((stage) => ({
    stage,
    status: project.staleStages.includes(stage) ? "stale" : stageHeads[stage]?.status || (project.stageRevisions[stage] > 0 ? "ready" : "missing"),
  }));
  const bibleAssets = [
    { label: "角色", items: project.storyBible.characters },
    { label: "地点", items: project.storyBible.locations },
    { label: "道具", items: project.storyBible.props },
  ];
  const page = useMemo(() => {
    switch (activePage) {
      case "brief": return <BriefPage key={`${editorRevisionKey(project, "brief")}:${editorNonce}`} value={recoveredValue("brief", project.brief)} saving={projectSaving || projectReadOnly} onSave={(brief) => commitProject({ brief })} onDraftChange={(value) => rememberDraft("brief", value)} />;
      case "bible": return <StoryBiblePage key={`${editorRevisionKey(project, "story_bible")}:${editorNonce}`} projectId={project.id} storyBibleRevision={stageHeads.story_bible?.revision} value={recoveredValue("story_bible", project.storyBible)} stale={project.staleStages.includes("story_bible")} saving={projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ sceneBeats: project.sceneBeats, storyboard: project.storyboard }} issues={validationIssues.story_bible} onEntitySelect={selectRouteEntity} onSave={(value: StoryBible) => commitStage("story_bible", value)} onDraftChange={(value) => rememberDraft("story_bible", value)} />;
      case "graph": return <GraphPage key={`${editorRevisionKey(project, "story_graph")}:${editorNonce}`} value={recoveredValue("story_graph", project.storyGraph)} stale={project.staleStages.includes("story_graph")} saving={projectSaving || projectReadOnly} entityId={routeEntity} sceneReferences={project.sceneBeats.scenes.map((scene) => ({ id: scene.id, storyNodeId: scene.storyNodeId, title: scene.title }))} issues={validationIssues.story_graph} onEntitySelect={selectRouteEntity} onSave={(value: StoryGraph) => commitStage("story_graph", value)} onDraftChange={(value) => rememberDraft("story_graph", value)} />;
      case "beats": return <SceneBeatsPage key={`${editorRevisionKey(project, "scene_beats")}:${editorNonce}`} value={recoveredValue("scene_beats", project.sceneBeats)} stale={project.staleStages.includes("scene_beats")} saving={projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ nodes: project.storyGraph.nodes, characters: project.storyBible.characters, locations: project.storyBible.locations, props: project.storyBible.props, storyboard: { shots: project.storyboard.shots.map(({ id, sceneId, cueIds }) => ({ id, sceneId, cueIds })), shotBeatLinks: project.storyboard.shotBeatLinks.map(({ shotId, beatId }) => ({ shotId, beatId })) } }} issues={validationIssues.scene_beats} onEntitySelect={selectRouteEntity} onSave={(value: SceneBeatPlan) => commitStage("scene_beats", value)} onDraftChange={(value) => rememberDraft("scene_beats", value)} />;
      case "storyboard": return <StoryboardPage key={`${editorRevisionKey(project, "storyboard")}:${editorNonce}`} projectId={project.id} revision={stageHeads.storyboard?.revision} storyBibleRevision={stageHeads.story_bible?.revision} contentHash={stageHeads.storyboard?.contentHash} bible={project.storyBible} graph={project.storyGraph} sceneBeats={project.sceneBeats} value={recoveredValue("storyboard", project.storyboard)} stale={project.staleStages.includes("storyboard")} mediaTasks={mediaTasks} saving={projectSaving || projectReadOnly} entityId={routeEntity} issues={validationIssues.storyboard} review={storyboardReview} mediaDraftsEnabled={durableMediaDraftsEnabled} onEntitySelect={selectRouteEntity} onNavigateIssue={(stage, entity) => requestNavigation({ project: navigationProjectId, stage, entity })} onReviewChange={setStoryboardReview} onSave={(value: Storyboard) => commitStage("storyboard", value)} onDraftChange={(value) => rememberDraft("storyboard", value)} />;
      case "trace": return <TracePage run={run} progress={runProgress} trace={trace} executionTrace={executionTrace} running={Boolean(running)} onRun={startRun} onResume={resumeRun} onCancel={cancelRun} />;
      case "quarantine": return <QuarantinePage items={project.quarantines} repairing={busy} onRepair={repair} onRebuildStage={rebuild} />;
    }
  // Commit callbacks intentionally read the current revision at invocation time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, project, busy, projectSaving, run, runProgress, trace, executionTrace, mediaTasks, running, restoredDraft, editorNonce, projectReadOnly, rememberDraft, routeEntity, selectRouteEntity, validationIssues, storyboardReview, requestNavigation, navigationProjectId]);

  if (onboarding) return <>
    <WelcomeOnboarding onBlank={startBlankProject} onSample={openSampleProject} onDirectory={openDirectory} />
    {directoryOpen && <ProjectDirectoryDialog projects={projects} showArchived={showArchived} error={directoryError} loading={directoryLoading} hasMore={Boolean(nextProjectCursor)} onLoadMore={loadMoreProjects} onArchived={(next) => { setShowArchived(next); void refreshProjectDirectory(next); }} onBlank={startBlankProject} onSample={openSampleProject} onOpen={(item) => { setDirectoryOpen(false); setOnboarding(false); requestNavigation({ project: item.id, stage: "brief" }); }} onAction={mutateProjectLifecycle} onClose={() => setDirectoryOpen(false)} />}
  </>;

  return <div className="app-shell">
    <a className="skip-link" href="#workspace-main">跳到工作区</a>
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>叙织 · PIPELINE WORKBENCH</small></div></div>
      <button className="project-switcher" onClick={openDirectory}><span>当前项目 · 切换</span><strong>{project.brief.title || "未命名项目"}</strong><small>{project.id || "unsaved teaching draft"} · r{project.revision}</small></button>
      <nav aria-label="工作台阶段">
        {navigation.map((item) => <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => requestNavigation({ project: navigationProjectId, stage: item.id, run: item.id === "trace" ? run?.id || "" : "" })}><span>{item.index}</span><div><strong>{item.label}</strong><small>{item.description}</small></div>{item.id === "quarantine" && project.quarantines.length > 0 && <i>{project.quarantines.length}</i>}</button>)}
      </nav>
      <div className="sidebar-footer"><Button variant="quiet" onClick={() => void openSettings()}>供应商与会话 Key</Button><small>API contract `/api/v2`</small></div>
    </aside>
    <div className="workspace-shell">
      <header className="topbar"><div><span>{currentNav.index}</span><strong>{currentNav.label}</strong></div><div className="topbar-actions">{projectReadOnly && <Badge tone="warning">归档只读</Badge>}{durableDraftsEnabled && <Badge tone={durableDraftStatus === "saved" ? "ok" : durableDraftStatus === "failed" || durableDraftStatus === "conflict" ? "danger" : durableDraftStatus === "saving" ? "accent" : "warning"}>草稿：{durableDraftStatus === "saving" ? "正在保存" : durableDraftStatus === "saved" ? "已保存" : durableDraftStatus === "failed" ? "保存失败" : durableDraftStatus === "conflict" ? "冲突" : "等待编辑"}</Badge>}<Badge tone={connection === "connected" ? "ok" : connection === "loading" ? "accent" : "warning"}>Plotloom 服务：{connection === "connected" ? "已连接" : connection === "loading" ? "连接中" : "未连接"}</Badge><Badge tone={profileDraft.readiness?.state === "available" ? "ok" : ["unreachable", "authentication_failed", "model_mismatch", "capability_mismatch"].includes(profileDraft.readiness?.state || "unverified") ? "danger" : "warning"}>文本后端：{profileDraft.readiness?.state || "unverified"} · {profileDraft.profileId} · {profileDraft.readiness?.reasonCode || "readiness.not_checked"}{profileDraft.readiness?.observedAt ? ` · ${new Date(profileDraft.readiness.observedAt).toLocaleString()}` : " · 未检测"}</Badge>{running && <Spinner label={runProgress?.failedStage ? stageLabels[runProgress.failedStage] : "Pipeline"} />}<Button variant="quiet" disabled={!project.id || connection === "loading"} onClick={requestProjectRefresh}>刷新服务器版本</Button>{staleCount > 0 && <Button variant="quiet" disabled={projectReadOnly} onClick={() => setRebuildOpen(true)}>{staleCount} 个阶段待重建</Button>}</div></header>
      {error && <div className="global-error"><ErrorNotice message={error} /><button aria-label="关闭错误" onClick={() => setError("")}>×</button></div>}
      <div className="workbench-grid">
        <aside className="context-panel"><span className="eyebrow">Context</span><strong>{project.brief.title || "新项目"}</strong><small>{project.lifecycleStatus === "archived" || project.archivedAt ? "归档快照 · 仅供审阅" : project.id ? `项目 ${project.id}` : navigationProjectId ? `加载项目 ${navigationProjectId}` : "空白项目；保存后建立规范项目"}</small><div className="context-stages">{navigation.slice(0, 5).map((item) => <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => requestNavigation({ project: navigationProjectId, stage: item.id })}>{item.index} {item.label}</button>)}</div><div className="context-assets"><span className="eyebrow">Canon assets</span>{bibleAssets.map((asset) => <div key={asset.label}><strong>{asset.label} · {asset.items.length}</strong><small>{asset.items.length ? asset.items.slice(0, 3).map((item) => item.name).join("、") : "尚未定义"}{asset.items.length > 3 ? " …" : ""}</small></div>)}</div></aside>
        <main id="workspace-main">{workspaceHydrating
          ? <div className="workspace-hydrating" data-testid="workspace-hydrating" role="status"><Spinner label="正在加载项目" /><strong>正在加载项目…</strong><small>项目内容加载完成后才能编辑，当前导航选择会被保留。</small></div>
          : <fieldset className="editor-host" disabled={projectReadOnly} onBlurCapture={() => {
            const scope = stageForPage(activePage);
            if (scope) void flushAuthoringDraft(scope);
          }}>{page}</fieldset>}</main>
        <WorkspaceInspector currentLabel={currentNav.label} project={project} routeEntity={routeEntity} stageOverview={stageOverview} run={run} progress={runProgress} review={storyboardReview} readOnly={projectReadOnly} frozenProfileId={frozenProfileId} frozenProfileNeedsKey={frozenProfileNeedsKey} onAuthorizeProfile={() => void openFrozenProfileSettings(frozenProfileId)} onOpenTrace={() => requestNavigation({ project: navigationProjectId, stage: "trace", run: run?.id || "" })} onResume={resumeRun} onCancel={cancelRun} onRepair={repair} onRebuild={(stage) => { setRebuildOpen(false); void rebuild(stage); }} />
      </div>
    </div>
    {settingsOpen && <SettingsDialog profiles={profiles} selectedProfileId={selectedProfileId} draft={profileDraft} sessionKey={sessionKey} busy={busy} onDraft={(draft) => { setProfileDraft(draft); setProfileDirty(true); }} onSessionKey={setSessionKey} onSelect={selectProfile} onCreate={() => createProfile(false)} onCopy={() => createProfile(true)} onDelete={deleteProfile} onActivate={activateProfile} onAvailability={setProfileAvailability} onProbe={testProfile} onClose={() => setSettingsOpen(false)} onSave={saveSettings} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={rebuild} />}
    {directoryOpen && <ProjectDirectoryDialog projects={projects} showArchived={showArchived} error={directoryError} loading={directoryLoading} hasMore={Boolean(nextProjectCursor)} onLoadMore={loadMoreProjects} onArchived={(next) => { setShowArchived(next); void refreshProjectDirectory(next); }} onBlank={startBlankProject} onSample={openSampleProject} onOpen={(item) => { setDirectoryOpen(false); requestNavigation({ project: item.id, stage: "brief" }); }} onAction={mutateProjectLifecycle} onClose={() => setDirectoryOpen(false)} />}
    {pendingNavigation && !unsafeDraft && <DraftNavigationDialog onSave={() => void resolvePendingNavigation("save")} onDiscard={() => void resolvePendingNavigation("discard")} onCancel={() => void resolvePendingNavigation("cancel")} />}
    {pendingArchive && <DraftNavigationDialog onSave={() => void resolvePendingArchive("save")} onDiscard={() => void resolvePendingArchive("discard")} onCancel={() => void resolvePendingArchive("cancel")} />}
    {draftRecovery && <DraftRecoveryDialog source={draftRecovery.source} onRestore={restoreDraftRecovery} onDiscard={discardDraftRecovery} />}
    {draftConflict && <DraftConflictDialog serverReloaded={draftConflict.serverReloaded} busy={projectSaving} onReload={() => void reloadConflictServer()} onCopy={() => void copyConflictAsProject()} onDiscard={() => { discardDraftRecord(draftConflict.record); currentDraft.current = undefined; setDraftConflict(undefined); bumpEditorNonce(); }} />}
    {unsafeDraft && <UnsafeDraftDialog reason={unsafeDraft.reason} onDiscard={() => {
      const pending = pendingNavigation;
      const { record, reason } = unsafeDraft;
      discardDraftRecord(record);
      const remaining = findProjectDrafts(record.projectId)[0];
      setUnsafeDraft(remaining ? { record: remaining, reason } : undefined);
      bumpEditorNonce();
      if (!remaining && pending) { setPendingNavigation(undefined); applyNavigation(pending); }
    }} />}
  </div>;
}
