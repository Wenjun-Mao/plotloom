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
  const [projectSaving, setProjectSaving] = useState(false);
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
  const [draftRecovery, setDraftRecovery] = useState<{ scope: DraftScope; payload: unknown; source: DraftRecoverySource } | undefined>();
  const [restoredDraft, setRestoredDraft] = useState<{ scope: DraftScope; payload: unknown; source: DraftRecoverySource } | undefined>();
  const [draftConflict, setDraftConflict] = useState<DraftConflictState | undefined>();
  const [unsafeDraft, setUnsafeDraft] = useState<{ record: DraftRecord; reason: "archived" | "unavailable" } | undefined>();
  const [pendingNavigation, setPendingNavigation] = useState<NavigationTarget | undefined>();
  const [editorNonce, setEditorNonce] = useState(0);
  const [durableDraftsEnabled, setDurableDraftsEnabled] = useState(false);
  const [durableMediaDraftsEnabled, setDurableMediaDraftsEnabled] = useState(false);
  const [durableDraftStatus, setDurableDraftStatus] = useState<DurableDraftStatus>("idle");
  const [onboarding, setOnboarding] = useState(() => !routeFromLocation().project);
  const [pendingArchive, setPendingArchive] = useState<ProjectListItem | undefined>();
  const loadEpoch = useRef(0);
  const currentDraft = useRef<{ scope: DraftScope; payload: unknown } | undefined>(undefined);
  const projectSaveInFlight = useRef(false);
  const projectSaveGeneration = useRef(0);
  const activeProjectSaveGeneration = useRef<number | undefined>(undefined);
  const canonicalRefreshRequired = useRef(new Set<string>());
  const creationKeyByBody = useRef(new Map<string, string>());
  const duplicateKeyByRequest = useRef(new Map<string, string>());
  const repairKeyByUnit = useRef(new Map<string, string>());
  const projectLoadController = useRef<AbortController | undefined>(undefined);
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
    projectLoadController.current?.abort();
    projectLoadController.current = undefined;
    visibleRoute.current = next;
    projectSaveInFlight.current = false;
    activeProjectSaveGeneration.current = undefined;
    setBusy(false);
    setProjectSaving(false);
    return loadEpoch.current;
  };

  const loadProject = useCallback(async (projectId: string, epoch = loadEpoch.current) => {
    const isCurrent = () => epoch === loadEpoch.current && visibleRoute.current.project === projectId;
    if (!projectId) return;
    projectLoadController.current?.abort();
    const controller = new AbortController();
    projectLoadController.current = controller;
    setConnection("loading");
    try {
      const [incoming, stageResponse, runResponse, mediaResponse, authoringDrafts] = await Promise.all([
        plotloomApi.getProject(projectId, controller.signal),
        plotloomApi.getStages(projectId, controller.signal),
        plotloomApi.getProjectRuns(projectId, controller.signal),
        plotloomApi.getProjectMediaTasks(projectId, controller.signal),
        durableDraftsEnabledRef.current
          ? plotloomApi.getAuthoringDrafts(projectId, controller.signal)
          : Promise.resolve([] as AuthoringDraft[]),
      ]);
      const storyboardHead = stageResponse.stages.find((envelope) => envelope.head.stage === "storyboard")?.head;
      const reviewResponse = storyboardHead?.revision
        ? await plotloomApi.getStoryboardReview(projectId, controller.signal).catch(() => null)
        : null;
      const requestedRunId = routeFromLocation().run;
      const latestRun = requestedRunId
        ? runResponse.runs.find((candidate) => candidate.id === requestedRunId)
        : runResponse.runs[0];
      const requestedRunMissing = Boolean(requestedRunId && !latestRun);
      // Project load and polling use the deliberately small progress
      // projection. Provenance evidence is fetched only after the user opens
      // the Trace page; it must not travel on the high-frequency path.
      const latestProgress = latestRun ? await plotloomApi.getRunProgress(latestRun.id) : undefined;
      let automaticResumeBlocked = "";
      if (latestRun && (latestRun.status === "queued" || latestRun.status === "running") && latestRun.providerSnapshot.textAuthMode !== "none") {
        const frozenProfileId = String(latestRun.providerSnapshot.profileId || "default");
        let catalog = profileCatalog.current;
        if (!profilesLoaded.current) {
          try {
            catalog = await plotloomApi.getTextProviderProfiles(controller.signal);
          } catch (profileError) {
            automaticResumeBlocked = `运行冻结在 Profile ${frozenProfileId}；无法确认该 Profile 的密钥状态，因此没有自动恢复：${messageFrom(profileError)}`;
          }
        }
        if (!automaticResumeBlocked) {
          const frozenProfile = catalog.profiles.find((candidate) => candidate.profileId === frozenProfileId);
          if (!frozenProfile) {
            automaticResumeBlocked = `运行冻结在 Profile ${frozenProfileId}，但该 Profile 已不存在；不会自动切换模型。`;
          } else if (!frozenProfile.serverKeyAvailable && !providerSessionKeys.read(frozenProfileId)) {
            automaticResumeBlocked = `运行冻结在 Profile ${frozenProfileId}；请为这个 Profile 补充当前标签页 Key 后再继续。不会自动切换模型。`;
          }
        }
      }
      if (!isCurrent()) return;
      const quarantines = quarantineItemsFromProgress(latestProgress);
      setProject((current) => ({ ...hydrateWorkspaceProject(current, incoming, stageResponse.stages), quarantines }));
      canonicalRefreshRequired.current.delete(projectId);
      setStageHeads(headsByStage(stageResponse.stages));
      setRun(latestRun);
      setRunProgress(latestProgress);
      setStoryboardReview(reviewResponse);
      setValidationIssues({});
      resetTrace();
      setMediaTasks(newestMediaTasksByShot(mediaResponse.tasks));
      serverAuthoringDrafts.current = new Map(
        authoringDrafts
          .filter((draft): draft is AuthoringDraft & { editorScope: DraftScope } =>
            draft.editorScope === "brief" || draft.editorScope === "story_bible" || draft.editorScope === "story_graph" || draft.editorScope === "scene_beats" || draft.editorScope === "storyboard",
          )
          .map((draft) => [authoringDraftKey(projectId, draft.editorScope), draft]),
      );
      setConnection("connected");
      setOnboarding(false);
      setError(requestedRunMissing ? `运行 ${requestedRunId} 不属于当前项目或已不存在。` : automaticResumeBlocked);
      if (latestRun && (latestRun.status === "queued" || latestRun.status === "running" || latestRun.status === "cancel_requested")) {
        if (!isCurrent()) return;
        if (latestRun.status === "cancel_requested") {
          void pollRun(latestRun.id, incoming.id).catch((pollError) => setError(messageFrom(pollError)));
        } else {
          if (automaticResumeBlocked) return;
          const frozenProfileId = String(latestRun.providerSnapshot.profileId || "default");
          const usesBearer = latestRun.providerSnapshot.textAuthMode !== "none";
          void plotloomApi.resumeRun(latestRun.id, frozenProfileId, usesBearer)
            .then(() => {
              if (isCurrent()) return pollRun(latestRun.id, incoming.id);
              return undefined;
            })
            .catch((resumeError) => {
              if (isCurrent()) setError(`运行保持排队：${messageFrom(resumeError)}`);
            });
        }
      }
    } catch (loadError) {
      if (!isCurrent()) return;
      if (loadError instanceof DOMException && loadError.name === "AbortError") return;
      const staleDraft = findProjectDrafts(projectId)[0];
      if (staleDraft) setUnsafeDraft({ record: staleDraft, reason: "unavailable" });
      setProject(blankWorkspace(localWorkspaceOwner.current)); setStageHeads({}); setRun(undefined); setRunProgress(undefined); setStoryboardReview(null); setValidationIssues({}); setTrace([]); setMediaTasks({});
      setConnection("error");
      setOnboarding(false);
      setError(`无法加载项目 ${projectId}：${messageFrom(loadError)}。项目未加载；没有回退到示例。`);
    } finally {
      if (projectLoadController.current === controller) projectLoadController.current = undefined;
    }
  }, []);
  const { pollRun, loadTraceEvidence, resetTrace } = useRunSession({
    loadEpoch,
    visibleRoute,
    isCurrent: isWorkspaceOperationCurrent,
    setProject,
    setRun,
    setProgress: setRunProgress,
    setTrace,
    setExecutionTrace,
    reloadProject: loadProject,
    setError,
    describeError: messageFrom,
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

  const refreshStaleAcceptedProject = (projectId: string) => {
    canonicalRefreshRequired.current.add(projectId);
    if (visibleRoute.current.project !== projectId) return;
    // A newer local draft has priority over a late server response. Leave the
    // marker in place and make the deferral explicit rather than overwriting
    // that draft with the canonical reload.
    if (currentDraft.current || findProjectDrafts(projectId).length) {
      setError("服务器已接受较早保存；当前草稿不会被覆盖。请先保存或丢弃当前草稿后切换阶段以刷新规范版本。");
      return;
    }
    // Revalidation is itself a new read generation. Advancing the epoch keeps
    // an older in-flight load for this same route from winning the race after
    // the authoritative refresh.
    const refreshEpoch = invalidateWorkspaceNavigation({ ...visibleRoute.current });
    void loadProject(projectId, refreshEpoch);
  };

  const { flushAuthoringDraft, scheduleAuthoringDraftAutosave } =
    useAuthoringDraftAutosave({
      project,
      durableDraftsEnabledRef,
      serverAuthoringDrafts,
      captureWorkspaceOperation,
      isWorkspaceOperationCurrent,
      setDurableDraftStatus,
      setError,
      onConflict: (scope, record, workspace) =>
        setDraftConflict({ scope, record, workspace, serverReloaded: false }),
    });
  const beginProjectSave = (): number | undefined => {
    if (project.archivedAt) { setError("归档项目为只读；请先在项目目录中恢复它。"); return undefined; }
    // React state does not update synchronously enough to protect two clicks in
    // the same turn. The ref is the authoritative single-flight boundary.
    if (projectSaveInFlight.current) return undefined;
    projectSaveInFlight.current = true;
    const generation = ++projectSaveGeneration.current;
    activeProjectSaveGeneration.current = generation;
    setBusy(true);
    setProjectSaving(true);
    setError("");
    return generation;
  };

  const finishProjectSave = (operation: WorkspaceOperation, generation: number) => {
    // A later navigation (or save) owns the UI state. The finishing request
    // must still retire its own single-flight token so it cannot strand saves.
    if (activeProjectSaveGeneration.current !== generation) return;
    activeProjectSaveGeneration.current = undefined;
    projectSaveInFlight.current = false;
    if (!isWorkspaceOperationCurrent(operation)) return;
    setProjectSaving(false);
    setBusy(false);
  };

  const createProjectFrom = async (nextLocal: WorkspaceProject, operation: WorkspaceOperation, initialStage?: ServerStageName): Promise<boolean> => {
    const request = projectCreationRequest(
      nextLocal.brief,
      initialStage ? initialStagesThrough(nextLocal, initialStage) : [],
    );
    const body = projectCreationBody(request);
    let idempotencyKey = creationKeyByBody.current.get(body);
    if (!idempotencyKey) {
      idempotencyKey = `project-create-${crypto.randomUUID()}`;
      creationKeyByBody.current.set(body, idempotencyKey);
    }
    const created = await plotloomApi.createProject(request, idempotencyKey);
    if (!isWorkspaceOperationCurrent(operation)) return false;
    const hydrated = hydrateWorkspaceProject(nextLocal, created, created.stages);

    // POST returns the complete canonical aggregate. Hydrating it directly
    // avoids racing a post-create read against the user's next edit.
    setProject(hydrated);
    setStageHeads(headsByStage(created.stages));
    setRun(undefined);
    setRunProgress(undefined);
    setTrace([]);
    setMediaTasks({});
    setConnection("connected");
    // Initial-stage creation persists a storyboard Gate receipt in the same
    // transaction. Hydrating stages alone used to leave the review panel blank
    // until a later navigation, falsely suggesting the receipt was absent.
    if (created.id && created.stages.some((stage) => stage.head.stage === "storyboard" && stage.head.status === "ready")) {
      const review = await plotloomApi.getStoryboardReview(created.id).catch(() => null);
      // Gate hydration is an additional asynchronous boundary after creation.
      // Navigation or a newer save may have taken ownership while it was in
      // flight, so this creation must not complete its route or save updates.
      if (!isWorkspaceOperationCurrent(operation)) return false;
      if (review) setStoryboardReview(review);
    }
    if (created.id) {
      const query = new URLSearchParams(location.search);
      query.set("project", created.id);
      history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
      visibleRoute.current = { ...visibleRoute.current, project: created.id };
    }
    // Clear the retry identity only after the canonical aggregate and URL have
    // both been installed. A malformed/partial response must remain retryable
    // with the same key, or a retry could create a duplicate project.
    creationKeyByBody.current.delete(body);
    // Creation changes the route identity from a local workspace to the new
    // project. Complete this flight here because its original operation token
    // intentionally no longer names the visible route.
    projectSaveInFlight.current = false;
    setProjectSaving(false);
    setBusy(false);
    return true;
  };

  const commitProject = async (patch: Partial<WorkspaceProject>) => {
    const saveGeneration = beginProjectSave();
    if (!saveGeneration) return;
    const operation = captureWorkspaceOperation();
    const nextLocal = mergeProjectResponse(project, patch);
    try {
      if (!project.id) {
        if (!await createProjectFrom(nextLocal, operation, nextLocal.initialStageOnFirstSave)) return;
      } else {
        if (durableDraftsEnabledRef.current && getDraft(project, "brief") && !await flushAuthoringDraft("brief")) return;
        const serverDraft = serverAuthoringDrafts.current.get(authoringDraftKey(project.id, "brief"));
        const consumedDraft = canonicalDraftConsumption(
          serverDraft,
          "brief",
          project.revision,
          nextLocal.brief,
        );
        const saved: { project: ProjectResource; consumedDraftRevision?: number } = consumedDraft
          ? await plotloomApi.patchProjectWithDraft(project.id, project.revision, nextLocal.brief, consumedDraft)
          : { project: await plotloomApi.patchProject(project.id, project.revision, nextLocal.brief) };
        const updated = saved.project;
        if (consumedDraft && saved.consumedDraftRevision === consumedDraft.draftRevision) {
          serverAuthoringDrafts.current.delete(authoringDraftKey(project.id, "brief"));
          setDurableDraftStatus("idle");
        } else if (!durableDraftsEnabledRef.current) {
          discardDraft(project, "brief");
        }
        if (!isWorkspaceOperationCurrent(operation)) {
          refreshStaleAcceptedProject(project.id);
          return;
        }
        setProject(mergeProjectResponse(nextLocal, updated));
        currentDraft.current = undefined; setRestoredDraft(undefined);
        return;
      }
      discardDraft(project, "brief"); currentDraft.current = undefined; setRestoredDraft(undefined);
    } catch (saveError) {
      if (!isWorkspaceOperationCurrent(operation)) return;
      setError(messageFrom(saveError));
      if (saveError instanceof ApiError && saveError.status === 409) {
        const record = getDraft(project, "brief") ?? putDraft(project, "brief", nextLocal.brief);
        setDraftConflict({ scope: "brief", record, workspace: nextLocal, serverReloaded: false });
        setPendingNavigation(undefined); setPendingArchive(undefined);
      }
      if (connection === "demo") setProject((current) => mergeProjectResponse(current, patch));
    } finally { finishProjectSave(operation, saveGeneration); }
  };

  const commitStage = async <T,>(stage: ServerStageName, content: T) => {
    const saveGeneration = beginProjectSave();
    if (!saveGeneration) return;
    const operation = captureWorkspaceOperation();
    const key = stage === "story_bible" ? "storyBible" : stage === "story_graph" ? "storyGraph" : stage === "scene_beats" ? "sceneBeats" : "storyboard";
    const nextLocal = markDownstreamStale(workspaceWithStageDraft(project, stage, content), stage);
    try {
      if (!project.id) {
        if (!await createProjectFrom(nextLocal, operation, stage)) return;
        setValidationIssues((current) => ({ ...current, [stage]: [] }));
        discardDraft(project, stage); currentDraft.current = undefined; setRestoredDraft(undefined);
        return;
      }
      if (durableDraftsEnabledRef.current && getDraft(project, stage) && !await flushAuthoringDraft(stage)) return;
      const serverDraft = serverAuthoringDrafts.current.get(authoringDraftKey(project.id, stage));
      const consumedDraft = canonicalDraftConsumption(
        serverDraft,
        stage,
        project.stageRevisions[stage],
        content,
      );
      const saved: { stage: StageHead; consumedDraftRevision?: number } = consumedDraft
        ? await plotloomApi.patchStageWithDraft(project.id, stage, project.stageRevisions[stage], content, consumedDraft)
        : { stage: await plotloomApi.patchStage(project.id, stage, project.stageRevisions[stage], content) };
      const envelope = saved.stage;
      if (consumedDraft && saved.consumedDraftRevision === consumedDraft.draftRevision) {
        serverAuthoringDrafts.current.delete(authoringDraftKey(project.id, stage));
        setDurableDraftStatus("idle");
      } else if (!durableDraftsEnabledRef.current) {
        discardDraft(project, stage);
      }
      if (!isWorkspaceOperationCurrent(operation)) {
        refreshStaleAcceptedProject(project.id);
        return;
      }
      setProject((current) => markDownstreamStale({ ...current, [key]: content, stageRevisions: { ...current.stageRevisions, [stage]: envelope.revision } }, stage));
      setStageHeads((current) => ({ ...current, [stage]: envelope }));
      setValidationIssues((current) => ({ ...current, [stage]: [] }));
      if (stage === "storyboard") {
        const nextReview = await plotloomApi.getStoryboardReview(project.id).catch(() => null);
        if (isWorkspaceOperationCurrent(operation)) setStoryboardReview(nextReview);
      }
      currentDraft.current = undefined; setRestoredDraft(undefined);
    } catch (stageError) {
      if (!isWorkspaceOperationCurrent(operation)) return;
      const issues = validationIssuesFrom(stageError);
      if (issues.length) {
        setValidationIssues((current) => ({ ...current, [stage]: issues }));
        setError(`${stageLabels[stage]}未通过领域校验。已保留草稿并标出 ${issues.length} 个问题。`);
      } else setError(messageFrom(stageError));
      if (stageError instanceof ApiError && stageError.status === 409) {
        const record = getDraft(project, stage) ?? putDraft(project, stage, content);
        setDraftConflict({ scope: stage, record, workspace: nextLocal, serverReloaded: false });
        setPendingNavigation(undefined); setPendingArchive(undefined);
      }
      if (connection === "demo") setProject((current) => markDownstreamStale(workspaceWithStageDraft(current, stage, content), stage));
    } finally { finishProjectSave(operation, saveGeneration); }
  };

  const rememberDraft = useCallback((scope: DraftScope, payload: unknown) => {
    if (project.archivedAt) return;
    currentDraft.current = { scope, payload };
    const local = getDraft(project, scope);
    const recoveredServerDraft = project.id && restoredDraft?.scope === scope && restoredDraft.source === "server"
      ? serverAuthoringDrafts.current.get(authoringDraftKey(project.id, scope))
      : undefined;
    // A recovered server draft is already the acknowledged CAS base even
    // before the user makes the first post-recovery edit. Seed that first
    // session-only buffer from the durable receipt, never revision zero.
    putDraft(project, scope, payload, local?.serverDraftRevision ?? recoveredServerDraft?.draftRevision ?? 0);
    scheduleAuthoringDraftAutosave(scope);
    if (restoredDraft?.scope === scope) setRestoredDraft({ ...restoredDraft, payload });
  }, [project, restoredDraft, scheduleAuthoringDraftAutosave]);

  const applyNavigation = useCallback((next: NavigationTarget) => {
    const route = { project: next.project, stage: next.stage, entity: next.entity, run: next.run };
    const epoch = invalidateWorkspaceNavigation(route);
    if (next.history === "push") {
      const query = new URLSearchParams();
      if (next.project) query.set("project", next.project);
      query.set("stage", next.stage);
      if (next.entity) query.set("entity", next.entity);
      if (next.run) query.set("run", next.run);
      history.pushState(null, "", `${location.pathname}?${query.toString()}`);
    }
    currentDraft.current = undefined;
    setActivePage(next.stage); setRouteEntity(next.entity); setDraftRecovery(undefined); setRestoredDraft(undefined); setDraftConflict(undefined); setUnsafeDraft(undefined);
    if (!next.project && next.project !== (project.id || "")) {
      localWorkspaceOwner.current = newClientDraftOwner();
      setProject(blankWorkspace(localWorkspaceOwner.current)); setStageHeads({}); setRun(undefined); setRunProgress(undefined); setStoryboardReview(null); setValidationIssues({}); setTrace([]); setMediaTasks({}); setConnection("blank"); setOnboarding(true);
    } else if (next.project) {
      setOnboarding(false);
      if (next.project !== project.id) { setStoryboardReview(null); setValidationIssues({}); }
      if (next.forceReload || next.project !== project.id || next.run !== (run?.id || "") || canonicalRefreshRequired.current.has(next.project)) void loadProject(next.project, epoch);
    }
  }, [loadProject, project.id, run?.id]);

  const requestNavigation = useCallback((next: { project: string; stage: PageId; entity?: string; run?: string; history?: "push" | "pop"; forceReload?: boolean }) => {
    const normalized: NavigationTarget = { entity: "", run: "", history: "push", forceReload: false, ...next };
    const scope = stageForPage(activePage);
    // Unsafe drafts are never candidates for save/recovery. Keep a popstate
    // destination pending behind its discard-only dialog.
    if (unsafeDraft || (project.id && (project.archivedAt || project.lifecycleStatus === "archived") && findProjectDrafts(project.id).length)) {
      setPendingNavigation(normalized);
      return;
    }
    if (scope && hasDraft(project, scope)) {
      if (durableDraftsEnabledRef.current && project.id) {
        void flushAuthoringDraft(scope).then((saved) => {
          if (saved) applyNavigation(normalized);
          else setPendingNavigation(normalized);
        });
        return;
      }
      setPendingNavigation(normalized);
      return;
    }
    applyNavigation(normalized);
  }, [activePage, applyNavigation, flushAuthoringDraft, project, unsafeDraft]);

  const selectRouteEntity = useCallback((entity: string) => {
    const next = { ...visibleRoute.current, entity };
    if (next.entity === visibleRoute.current.entity) return;
    // Entity focus does not change the loaded project or invalidate an
    // in-flight canonical save. Keep the URL/ref authoritative without
    // advancing the project-operation epoch.
    visibleRoute.current = next;
    const query = new URLSearchParams();
    if (next.project) query.set("project", next.project);
    query.set("stage", next.stage);
    if (entity) query.set("entity", entity);
    if (next.run) query.set("run", next.run);
    history.pushState(null, "", `${location.pathname}?${query.toString()}`);
    setRouteEntity(entity);
  }, []);

  const resolvePendingNavigation = async (action: "save" | "discard" | "cancel") => {
    const pending = pendingNavigation;
    if (!pending || action === "cancel") {
      if (pending?.history === "pop") {
        const query = new URLSearchParams();
        if (project.id) query.set("project", project.id);
        query.set("stage", activePage);
        if (routeEntity) query.set("entity", routeEntity);
        if (activePage === "trace" && run?.id) query.set("run", run.id);
        history.replaceState(null, "", `${location.pathname}?${query.toString()}`);
      }
      setPendingNavigation(undefined); return;
    }
    const scope = stageForPage(activePage);
    if (scope && action === "save") {
      const draft = currentDraft.current;
      if (!draft || draft.scope !== scope) { setPendingNavigation(undefined); return; }
      if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await commitStage(scope, draft.payload);
      if (currentDraft.current) return;
    }
    if (scope) { discardDraft(project, scope); currentDraft.current = undefined; }
    setPendingNavigation(undefined); applyNavigation(pending);
  };

  useEffect(() => {
    const onPopState = () => {
      const route = routeFromLocation();
      // Entity focus is local UI state, not an edit. It must remain usable
      // while a form is dirty so Back/Forward can restore the prior selection.
      if (route.project === visibleRoute.current.project && route.stage === visibleRoute.current.stage && route.run === visibleRoute.current.run) {
        visibleRoute.current = route;
        setRouteEntity(route.entity);
        return;
      }
      requestNavigation({ ...route, history: "pop" });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [requestNavigation]);

  useEffect(() => {
    const scope = stageForPage(activePage);
    if (project.id && (project.archivedAt || project.lifecycleStatus === "archived")) {
      const record = findProjectDrafts(project.id)[0];
      if (record && !unsafeDraft) setUnsafeDraft({ record, reason: "archived" });
      return;
    }
    if (!scope || currentDraft.current || draftRecovery || draftConflict || unsafeDraft || restoredDraft) return;
    const saved = getDraft(project, scope);
    const serverDraft = project.id && durableDraftsEnabled
      ? serverAuthoringDrafts.current.get(authoringDraftKey(project.id, scope))
      : undefined;
    if (serverDraft) {
      setDraftRecovery({
        scope,
        payload: saved?.payload ?? serverDraft.payload,
        source: saved ? "reconcile" : "server",
      });
    } else if (saved) setDraftRecovery({ scope, payload: saved.payload, source: "session" });
    else {
      const conflict = findRevisionConflict(project, scope);
      if (conflict) setDraftConflict({ scope, record: conflict, workspace: project, serverReloaded: false });
    }
  }, [activePage, draftConflict, draftRecovery, durableDraftsEnabled, editorNonce, project, restoredDraft, unsafeDraft]);

  const showRunTrace = (nextRun: PipelineRun, resetEvidence = true) => {
    const nextRoute = { project: nextRun.projectId, stage: "trace" as const, entity: "", run: nextRun.id };
    invalidateWorkspaceNavigation(nextRoute);
    const query = new URLSearchParams({ project: nextRun.projectId, stage: "trace", run: nextRun.id });
    history.pushState(null, "", `${location.pathname}?${query.toString()}`);
    currentDraft.current = undefined;
    setActivePage("trace");
    setRouteEntity("");
    setDraftRecovery(undefined);
    setRestoredDraft(undefined);
    setDraftConflict(undefined);
    setRun(nextRun);
    setRunProgress(undefined);
    if (resetEvidence) resetTrace();
    setRebuildOpen(false);
    void pollRun(nextRun.id, nextRun.projectId).catch((pollError) => setError(messageFrom(pollError)));
  };

  const prepareGenerationProfile = async (): Promise<TextProviderProfileView> => {
    // Every provider-spending action freezes the public form currently shown.
    // A full-page refresh must first load the active server-side selection so
    // it cannot accidentally save or use the UI fallback profile.
    let profileToSave = profileDraft;
    let keyToUse = sessionKey;
    if (!profilesLoaded.current) {
      const loaded = await refreshProfiles();
      profileToSave = loaded.profiles.find((profile) => profile.profileId === loaded.activeProfileId) || profileToSave;
      keyToUse = providerSessionKeys.read(profileToSave.profileId);
    }
    return saveProfile(profileToSave, keyToUse);
  };

  const startRun = async (stages: ServerStageName[]) => {
    if (!project.id) { setError("请先保存项目，再启动生成流水线。"); return; }
    if (profileDraft.enabled === false) { setError("当前活动 Profile 已停用；请先在设置中启用可用 Profile。不会自动切换后端。"); return; }
    const operation = captureWorkspaceOperation();
    setBusy(true); setError("");
    try {
      const saved = await prepareGenerationProfile();
      if (!isWorkspaceOperationCurrent(operation)) return;
      const started = await plotloomApi.startRun(
        project.id, stages, saved.profileId, saved.configuration.textAuthMode === "bearer",
      );
      if (!isWorkspaceOperationCurrent(operation)) return;
      showRunTrace(started);
    }
    catch (runError) { if (isWorkspaceOperationCurrent(operation)) setError(messageFrom(runError)); }
    finally { if (isWorkspaceOperationCurrent(operation)) setBusy(false); }
  };

  const cancelRun = async () => {
    if (!run) return;
    const operation = captureWorkspaceOperation();
    try {
      const cancelled = await plotloomApi.cancelRun(run.id);
      if (!isWorkspaceOperationCurrent(operation)) return;
      setRun(cancelled);
      // A cancellation can race an in-flight provider attempt. Re-enter the
      // same lightweight observer so the inspector eventually reflects the
      // durable terminal outcome without fetching trace evidence.
      void pollRun(cancelled.id, cancelled.projectId).catch((pollError) => setError(messageFrom(pollError)));
    } catch (cancelError) { if (isWorkspaceOperationCurrent(operation)) setError(messageFrom(cancelError)); }
  };

  const resumeRun = async () => {
    if (!run || (run.status !== "queued" && run.status !== "running")) return;
    if (!await ensureFrozenRunCredential(run)) return;
    const frozenProfileId = String(run.providerSnapshot.profileId || "default");
    const usesBearer = run.providerSnapshot.textAuthMode !== "none";
    const operation = captureWorkspaceOperation();
    try {
      const resumed = await plotloomApi.resumeRun(run.id, frozenProfileId, usesBearer);
      if (!isWorkspaceOperationCurrent(operation)) return;
      setRun(resumed);
      void pollRun(run.id).catch((pollError) => setError(messageFrom(pollError)));
    } catch (resumeError) { if (isWorkspaceOperationCurrent(operation)) setError(messageFrom(resumeError)); }
  };

  const repair = async (item: QuarantineItem) => {
    if (!run || !item.repairEligible) { setError("这个 work unit 当前不具备精确修复资格。"); return; }
    if (!await ensureFrozenRunCredential(run)) return;
    const operation = captureWorkspaceOperation();
    setBusy(true);
    try {
      // Exact repair is bound to its parent run. It must not save the visible
      // profile form or switch models; only the matching profile-scoped
      // session key can accompany this request.
      const frozenProfileId = String(run.providerSnapshot.profileId || "default");
      const usesBearer = run.providerSnapshot.textAuthMode !== "none";
      const repairIdentity = `${run.id}:${item.id}`;
      let idempotencyKey = repairKeyByUnit.current.get(repairIdentity);
      if (!idempotencyKey) {
        idempotencyKey = `work-unit-repair-${crypto.randomUUID()}`;
        repairKeyByUnit.current.set(repairIdentity, idempotencyKey);
      }
      const next = await plotloomApi.repairWorkUnit(
        run.id, item.id, frozenProfileId, idempotencyKey, usesBearer,
      );
      if (!isWorkspaceOperationCurrent(operation)) return;
      repairKeyByUnit.current.delete(repairIdentity);
      showRunTrace(next);
    }
    catch (repairError) { if (isWorkspaceOperationCurrent(operation)) setError(messageFrom(repairError)); }
    finally { if (isWorkspaceOperationCurrent(operation)) setBusy(false); }
  };

  const rebuild = async (fromStage: ServerStageName) => {
    if (!project.id) { setError("请先保存项目，再重建下游阶段。"); return; }
    const scope = stageForPage(activePage);
    if (scope && hasDraft(project, scope)) {
      setError("请先保存或丢弃当前阶段草稿，再创建重建运行。");
      return;
    }
    const operation = captureWorkspaceOperation();
    setBusy(true);
    try {
      const saved = await prepareGenerationProfile();
      if (!isWorkspaceOperationCurrent(operation)) return;
      const next = await plotloomApi.rebuild(
        project.id, fromStage, saved.profileId,
        saved.configuration.textAuthMode === "bearer",
      );
      if (!isWorkspaceOperationCurrent(operation)) return;
      showRunTrace(next);
    }
    catch (rebuildError) { if (isWorkspaceOperationCurrent(operation)) setError(messageFrom(rebuildError)); }
    finally { if (isWorkspaceOperationCurrent(operation)) setBusy(false); }
  };

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

  const performProjectLifecycle = async (item: ProjectListItem, action: "archive" | "restore" | "duplicate" | "delete") => {
    const operation = captureWorkspaceOperation();
    try {
      if (action === "archive") {
        const updated = await plotloomApi.archiveProject(item.id, item.lifecycleRevision ?? item.revision);
        if (!isWorkspaceOperationCurrent(operation)) return;
        if (project.id === item.id) setProject((current) => ({ ...current, ...updated }));
      } else if (action === "restore") {
        const updated = await plotloomApi.restoreProject(item.id, item.lifecycleRevision ?? item.revision);
        if (!isWorkspaceOperationCurrent(operation)) return;
        if (project.id === item.id) setProject((current) => ({ ...current, ...updated }));
      } else if (action === "duplicate") {
        const revision = item.lifecycleRevision ?? item.revision;
        const duplicateRequest = `${item.id}:${revision}`;
        let idempotencyKey = duplicateKeyByRequest.current.get(duplicateRequest);
        if (!idempotencyKey) {
          idempotencyKey = `project-duplicate-${crypto.randomUUID()}`;
          duplicateKeyByRequest.current.set(duplicateRequest, idempotencyKey);
        }
        const duplicate = await plotloomApi.duplicateProject(item.id, revision, undefined, idempotencyKey);
        if (!isWorkspaceOperationCurrent(operation)) return;
        duplicateKeyByRequest.current.delete(duplicateRequest);
        setDirectoryOpen(false);
        requestNavigation({ project: duplicate.project.id, stage: "brief" });
      } else {
        const expectedTitle = item.brief.title || item.id;
        const confirmationTitle = window.prompt(`输入完整片名“${expectedTitle}”以永久删除`, "");
        if (confirmationTitle !== expectedTitle) {
          setDirectoryError("片名不匹配；未发送永久删除请求。");
          return;
        }
        await plotloomApi.permanentlyDeleteProject(item.id, item.lifecycleRevision ?? item.revision, confirmationTitle);
        if (!isWorkspaceOperationCurrent(operation)) return;
        if (project.id === item.id) startBlankProject();
      }
      if (!isWorkspaceOperationCurrent(operation)) return;
      await refreshProjectDirectory();
    } catch (lifecycleError) {
      if (isWorkspaceOperationCurrent(operation)) setDirectoryError(messageFrom(lifecycleError));
    }
  };

  const mutateProjectLifecycle = async (item: ProjectListItem, action: "archive" | "restore" | "duplicate" | "delete") => {
    const scope = stageForPage(activePage);
    if (action === "archive" && item.id === project.id && scope && hasDraft(project, scope)) {
      setPendingArchive(item);
      return;
    }
    await performProjectLifecycle(item, action);
  };

  const resolvePendingArchive = async (action: "save" | "discard" | "cancel") => {
    const item = pendingArchive;
    if (!item || action === "cancel") { setPendingArchive(undefined); return; }
    const scope = stageForPage(activePage);
    if (scope && action === "save") {
      const draft = currentDraft.current;
      if (!draft || draft.scope !== scope) { setPendingArchive(undefined); return; }
      if (scope === "brief") await commitProject({ brief: draft.payload as WorkspaceProject["brief"] });
      else await commitStage(scope, draft.payload);
      if (currentDraft.current) return;
    }
    if (scope) { discardDraft(project, scope); currentDraft.current = undefined; }
    setPendingArchive(undefined);
    await performProjectLifecycle(item, "archive");
  };

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
      setEditorNonce((value) => value + 1);
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
    {draftRecovery && <DraftRecoveryDialog source={draftRecovery.source} onRestore={() => {
      currentDraft.current = { scope: draftRecovery.scope, payload: draftRecovery.payload };
      setRestoredDraft(draftRecovery);
      if (draftRecovery.source !== "server") scheduleAuthoringDraftAutosave(draftRecovery.scope);
      setEditorNonce((value) => value + 1); setDraftRecovery(undefined);
    }} onDiscard={() => {
      const recovery = draftRecovery;
      discardDraft(project, recovery.scope);
      const serverDraft = project.id && serverAuthoringDrafts.current.get(authoringDraftKey(project.id, recovery.scope));
      if (serverDraft && project.id) {
        void plotloomApi.discardAuthoringDraft(project.id, {
          editorScope: recovery.scope, entityId: "root", expectedDraftRevision: serverDraft.draftRevision,
        }).then((receipt) => {
          if (receipt === serverDraft.draftRevision) serverAuthoringDrafts.current.delete(authoringDraftKey(project.id!, recovery.scope));
        }).catch((discardError) => setError(`草稿未丢弃：${messageFrom(discardError)}`));
      }
      currentDraft.current = undefined; setDraftRecovery(undefined); setRestoredDraft(undefined); setEditorNonce((value) => value + 1);
    }} />}
    {draftConflict && <DraftConflictDialog serverReloaded={draftConflict.serverReloaded} busy={projectSaving} onReload={() => void reloadConflictServer()} onCopy={() => void copyConflictAsProject()} onDiscard={() => { discardDraftRecord(draftConflict.record); currentDraft.current = undefined; setDraftConflict(undefined); setEditorNonce((value) => value + 1); }} />}
    {unsafeDraft && <UnsafeDraftDialog reason={unsafeDraft.reason} onDiscard={() => {
      const pending = pendingNavigation;
      const { record, reason } = unsafeDraft;
      discardDraftRecord(record);
      const remaining = findProjectDrafts(record.projectId)[0];
      setUnsafeDraft(remaining ? { record: remaining, reason } : undefined);
      setEditorNonce((value) => value + 1);
      if (!remaining && pending) { setPendingNavigation(undefined); applyNavigation(pending); }
    }} />}
  </div>;
}
