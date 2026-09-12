import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MediaTask, PipelineRun, ProjectListItem, ProviderSettings, QuarantineItem, RunExecutionTrace, RunProgress, SceneBeatPlan, ServerStageName, StageEnvelope, StageHead, StoryBible, StoryGraph, Storyboard, StoryboardReview, TextBackendReadiness, TextProviderPresetId, TextProviderProfileConfiguration, TextProviderProfilesResponse, TextProviderProfileView, TraceEvent, ValidationIssue, WorkspaceProject } from "./types";
import { plotloomApi, ApiError } from "./api";
import { providerSessionKeys } from "./session-key";
import { defaultProviderSettings, demoProject, demoRun, demoTrace, emptyStageContent } from "./demo";
import { discardDraft, discardDraftRecord, findProjectDrafts, findRevisionConflict, getDraft, hasDraft, putDraft, type DraftRecord, type DraftScope } from "./draft-registry";
import { markDownstreamStale, mergeProjectResponse, stageLabels, traceEvents } from "./model";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "./project-creation";
import { editorRevisionKey, hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromProgress } from "./workspace-state";
import { Badge, Button, ErrorNotice, Spinner } from "./components";
import { BriefPage } from "./pages/BriefPage";
import { StoryBiblePage } from "./pages/StoryBiblePage";
import { GraphPage } from "./pages/GraphPage";
import { SceneBeatsPage } from "./pages/SceneBeatsPage";
import { StoryboardPage } from "./pages/StoryboardPage";
import { TracePage } from "./pages/TracePage";
import { QuarantinePage } from "./pages/QuarantinePage";

type PageId = "brief" | "bible" | "graph" | "beats" | "storyboard" | "trace" | "quarantine";
type NavigationTarget = {
  project: string;
  stage: PageId;
  entity: string;
  run: string;
  history: "push" | "pop";
  forceReload?: boolean;
};

interface DraftConflictState {
  scope: DraftScope;
  record: DraftRecord;
  workspace: WorkspaceProject;
  serverReloaded: boolean;
}

const navigation: { id: PageId; index: string; label: string; description: string }[] = [
  { id: "brief", index: "01", label: "项目简报", description: "边界与预算" },
  { id: "bible", index: "02", label: "故事圣经", description: "人物与规则" },
  { id: "graph", index: "03", label: "剧情 DAG", description: "分支与汇合" },
  { id: "beats", index: "04", label: "场景节拍", description: "原子事件" },
  { id: "storyboard", index: "05", label: "分镜工作台", description: "路径与媒体" },
  { id: "trace", index: "06", label: "运行轨迹", description: "Prompt 与证据" },
  { id: "quarantine", index: "07", label: "隔离修复", description: "安全失败" },
];
const editableStages: ServerStageName[] = ["story_bible", "story_graph", "scene_beats", "storyboard"];

function headsByStage(stages: StageEnvelope[]): Partial<Record<ServerStageName, StageHead>> {
  return Object.fromEntries(stages.map((envelope) => [envelope.head.stage, envelope.head])) as Partial<Record<ServerStageName, StageHead>>;
}

function messageFrom(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) return `项目版本冲突：${error.message}。请刷新后再合并修改。`;
  return error instanceof Error ? error.message : "未知错误";
}

function validationIssuesFrom(error: unknown): ValidationIssue[] {
  if (!(error instanceof ApiError) || error.status !== 422 || !error.details || typeof error.details !== "object") return [];
  const rawIssues = (error.details as { issues?: unknown }).issues;
  if (!Array.isArray(rawIssues)) return [];
  return rawIssues.flatMap((raw): ValidationIssue[] => {
    if (!raw || typeof raw !== "object") return [];
    const candidate = raw as { code?: unknown; path?: unknown; message?: unknown };
    if (typeof candidate.code !== "string" || typeof candidate.message !== "string") return [];
    const path = Array.isArray(candidate.path)
      ? candidate.path.map(String).join(".")
      : typeof candidate.path === "string" ? candidate.path : "";
    return [{ code: candidate.code, path, message: candidate.message }];
  });
}

function formatDuration(durationMs: number | null | undefined): string {
  if (durationMs == null) return "—";
  return durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`;
}

function projectIdFromLocation(): string {
  return new URLSearchParams(window.location.search).get("project") || "";
}

function pageFromStage(stage: string | null): PageId {
  return navigation.some((item) => item.id === stage) ? stage as PageId : "brief";
}

function stageForPage(page: PageId): DraftScope | undefined {
  if (page === "brief") return "brief";
  if (page === "bible") return "story_bible";
  if (page === "graph") return "story_graph";
  if (page === "beats") return "scene_beats";
  if (page === "storyboard") return "storyboard";
  return undefined;
}

function routeFromLocation() {
  const query = new URLSearchParams(window.location.search);
  return { project: query.get("project") || "", stage: pageFromStage(query.get("stage")), entity: query.get("entity") || "", run: query.get("run") || "" };
}

function newClientDraftOwner(): string {
  return `workspace-${crypto.randomUUID()}`;
}

function blankWorkspace(clientDraftOwner = newClientDraftOwner()): WorkspaceProject {
  return {
    clientDraftOwner,
    revision: 0,
    brief: { title: "", synopsis: "", genre: null, visualStyle: null, language: "zh-CN", aspectRatio: "16:9", targetPlaythroughSeconds: 180, decisionPointsPerPath: 2, endingCount: 2, nodeBudget: 8, maxOutDegree: 3, desiredJoinCount: 1, shotsPerSceneMin: 1, shotsPerSceneMax: 4 },
    ...emptyStageContent, quarantines: [], staleStages: [],
    stageRevisions: { story_bible: 0, story_graph: 0, scene_beats: 0, storyboard: 0 },
  };
}

function defaultTextProfile(): TextProviderProfileView {
  const configuration: TextProviderProfileConfiguration = {
    profileSchemaVersion: 2, profileId: "default", profileVersion: 0, profileHash: "",
    textProvider: defaultProviderSettings.textProvider || "openai-compatible",
    textBaseUrl: defaultProviderSettings.textBaseUrl || "", textModel: defaultProviderSettings.textModel || "",
    textAuthMode: defaultProviderSettings.textAuthMode,
    textCapabilities: { ...defaultProviderSettings.textCapabilities, chatTemplateKwargs: false },
    textContextWindowTokens: defaultProviderSettings.textContextWindowTokens,
    textMaxOutputTokens: defaultProviderSettings.textMaxOutputTokens,
    textTemperature: defaultProviderSettings.textTemperature,
    textMaxConcurrency: defaultProviderSettings.textMaxConcurrency,
    textConnectTimeoutSeconds: defaultProviderSettings.textConnectTimeoutSeconds,
    textAttemptTimeoutSeconds: defaultProviderSettings.textAttemptTimeoutSeconds,
    redirectPolicy: "no_follow", requestExtension: "none", reasoningMode: "provider_default",
    extractionPolicy: { allowJsonFence: false, allowLeadingThinkBlock: false },
    stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 },
    maxSemanticCorrections: 2, presetId: "custom", presetVersion: "1",
  };
  return { profileId: "default", displayName: "Default", configuration, revision: 0, enabled: true, availabilityRevision: 0, adapterId: "openai_compatible", adapterVersion: "1", createdAt: "", updatedAt: "", serverKeyAvailable: false, readiness: { profileId: "default", profileRevision: 0, state: "unverified", reasonCode: "readiness.not_checked", observedAt: null } };
}

function profileFromLegacySettings(settings: ProviderSettings): TextProviderProfileView {
  const fallback = defaultTextProfile();
  return {
    ...fallback,
    displayName: settings.profileId || fallback.displayName,
    revision: settings.revision,
    updatedAt: settings.updatedAt || "",
    serverKeyAvailable: settings.textKeyAvailable,
    configuration: {
      ...fallback.configuration,
      textProvider: settings.textProvider || fallback.configuration.textProvider,
      textBaseUrl: settings.textBaseUrl || fallback.configuration.textBaseUrl,
      textModel: settings.textModel || fallback.configuration.textModel,
      textAuthMode: settings.textAuthMode,
      textCapabilities: { ...settings.textCapabilities, chatTemplateKwargs: false },
      textContextWindowTokens: settings.textContextWindowTokens,
      textMaxOutputTokens: settings.textMaxOutputTokens,
      textTemperature: settings.textTemperature,
      textMaxConcurrency: settings.textMaxConcurrency,
      textConnectTimeoutSeconds: settings.textConnectTimeoutSeconds,
      textAttemptTimeoutSeconds: settings.textAttemptTimeoutSeconds,
      redirectPolicy: settings.redirectPolicy,
    },
  };
}

const fallbackProfiles = (): TextProviderProfilesResponse => ({
  profiles: [defaultTextProfile()], activeProfileId: "default", selectionRevision: 0,
  trustedAdapters: [{ adapterId: "openai_compatible", adapterVersion: "1" }],
  presets: {
    compatible_v1: { presetId: "compatible_v1", presetVersion: "1", requestExtension: "none", reasoningMode: "provider_default", textContextWindowTokens: 32768, textMaxOutputTokens: 8192, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, textAttemptTimeoutSeconds: 300, maxSemanticCorrections: 2 },
    quality_reasoning_v1: { presetId: "quality_reasoning_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "enabled", textContextWindowTokens: 131072, textMaxOutputTokens: 32768, stageMaxOutputTokens: { story_bible: 32768, story_graph: 32768, scene_beats: 32768, storyboard: 32768 }, textAttemptTimeoutSeconds: 900, maxSemanticCorrections: 2 },
    final_only_v1: { presetId: "final_only_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "disabled", textContextWindowTokens: 32768, textMaxOutputTokens: 16384, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 8192, storyboard: 8192 }, textAttemptTimeoutSeconds: 600, maxSemanticCorrections: 2 },
  },
});

const readinessRemediation = (state: TextBackendReadiness["state"]): string => {
  switch (state) {
    case "disabled": return "启用此 Profile 后重新检查。";
    case "unreachable": return "检查 API 根地址、网络和服务进程后重新检查。";
    case "authentication_failed": return "为此 Profile 提供可用的服务器或当前标签页临时 Key 后重新检查。";
    case "model_mismatch": return "将文本模型改为服务 /models 返回的精确 ID 后保存并重新检查。";
    case "capability_mismatch": return "核对受信任适配器、端点协议和能力声明后重新检查。";
    case "available": return "可以创建新的生成、重建和修复运行。";
    default: return "点击“测试连接”取得不生成文本的最新就绪状态。";
  }
};

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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [rebuildOpen, setRebuildOpen] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => providerSessionKeys.read("default"));
  const [profiles, setProfiles] = useState<TextProviderProfilesResponse>(fallbackProfiles);
  const [selectedProfileId, setSelectedProfileId] = useState("default");
  const [profileDraft, setProfileDraft] = useState<TextProviderProfileView>(defaultTextProfile);
  const [profileDirty, setProfileDirty] = useState(false);
  const [executionTrace, setExecutionTrace] = useState<RunExecutionTrace | undefined>();
  const [stageHeads, setStageHeads] = useState<Partial<Record<ServerStageName, StageHead>>>({});
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [directoryError, setDirectoryError] = useState("");
  const [nextProjectCursor, setNextProjectCursor] = useState<string | null>(null);
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [routeEntity, setRouteEntity] = useState(() => routeFromLocation().entity);
  const [draftRecovery, setDraftRecovery] = useState<{ scope: DraftScope; payload: unknown } | undefined>();
  const [restoredDraft, setRestoredDraft] = useState<{ scope: DraftScope; payload: unknown } | undefined>();
  const [draftConflict, setDraftConflict] = useState<DraftConflictState | undefined>();
  const [unsafeDraft, setUnsafeDraft] = useState<{ record: DraftRecord; reason: "archived" | "unavailable" } | undefined>();
  const [pendingNavigation, setPendingNavigation] = useState<NavigationTarget | undefined>();
  const [editorNonce, setEditorNonce] = useState(0);
  const [onboarding, setOnboarding] = useState(() => !routeFromLocation().project);
  const [pendingArchive, setPendingArchive] = useState<ProjectListItem | undefined>();
  const pollingRunEpochs = useRef(new Map<string, number>());
  const loadEpoch = useRef(0);
  const currentDraft = useRef<{ scope: DraftScope; payload: unknown } | undefined>(undefined);
  const projectSaveInFlight = useRef(false);
  const projectSaveGeneration = useRef(0);
  const activeProjectSaveGeneration = useRef<number | undefined>(undefined);
  const canonicalRefreshRequired = useRef(new Set<string>());
  const creationKeyByBody = useRef(new Map<string, string>());
  const duplicateKeyByRequest = useRef(new Map<string, string>());
  const directoryEpoch = useRef(0);
  const profilesLoaded = useRef(false);
  const profileCatalog = useRef<TextProviderProfilesResponse>(fallbackProfiles());
  const repairKeyByUnit = useRef(new Map<string, string>());
  const traceEvidenceEpoch = useRef(0);
  const projectLoadController = useRef<AbortController | undefined>(undefined);
  const loadedTraceEvidenceFor = useRef<string | undefined>(undefined);
  const loadingTraceEvidenceFor = useRef<string | undefined>(undefined);
  useEffect(() => { profileCatalog.current = profiles; }, [profiles]);

  type WorkspaceOperation = { epoch: number; projectId: string; stage: PageId };
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

  const installProfiles = useCallback((next: TextProviderProfilesResponse, selectedId = next.activeProfileId) => {
    // Rolling upgrades may serve the previous profile shape briefly.  Absence
    // is not readiness: present it as an explicit unverified observation.
    const normalized: TextProviderProfilesResponse = {
      ...next,
      profiles: next.profiles.map((profile) => ({
        ...profile,
        readiness: profile.readiness || {
          profileId: profile.profileId,
          profileRevision: profile.revision,
          state: profile.enabled === false ? "disabled" : "unverified",
          reasonCode: profile.enabled === false ? "readiness.profile_disabled" : "readiness.not_checked",
          observedAt: null,
        },
      })),
    };
    const selected = normalized.profiles.find((profile) => profile.profileId === selectedId) || normalized.profiles[0];
    if (!selected) return;
    profilesLoaded.current = true;
    profileCatalog.current = normalized;
    setProfiles(normalized); setSelectedProfileId(selected.profileId); setProfileDraft(selected);
    setSessionKey(providerSessionKeys.read(selected.profileId)); setProfileDirty(false);
  }, []);

  const refreshProfiles = useCallback(async (): Promise<TextProviderProfilesResponse> => {
    const next = await plotloomApi.getTextProviderProfiles();
    installProfiles(next);
    return next;
  }, [installProfiles]);

  const loadProject = useCallback(async (projectId: string, epoch = loadEpoch.current) => {
    const isCurrent = () => epoch === loadEpoch.current && visibleRoute.current.project === projectId;
    if (!projectId) return;
    projectLoadController.current?.abort();
    const controller = new AbortController();
    projectLoadController.current = controller;
    setConnection("loading");
    try {
      const [incoming, stageResponse, runResponse, mediaResponse] = await Promise.all([
        plotloomApi.getProject(projectId, controller.signal),
        plotloomApi.getStages(projectId, controller.signal),
        plotloomApi.getProjectRuns(projectId, controller.signal),
        plotloomApi.getProjectMediaTasks(projectId, controller.signal),
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
      traceEvidenceEpoch.current += 1;
      loadedTraceEvidenceFor.current = undefined;
      loadingTraceEvidenceFor.current = undefined;
      setTrace([]);
      setExecutionTrace(undefined);
      setMediaTasks(newestMediaTasksByShot(mediaResponse.tasks));
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

  useEffect(() => {
    const initialRoute = routeFromLocation();
    const epoch = invalidateWorkspaceNavigation(initialRoute);
    if (initialRoute.project) void loadProject(initialRoute.project, epoch);
  // This runs once: navigation is owned by requestNavigation/popstate below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadProject]);
  useEffect(() => { void refreshProfiles().catch(() => undefined); }, [refreshProfiles]);
  const loadTraceEvidence = useCallback(async (runId: string, projectId: string) => {
    if (loadedTraceEvidenceFor.current === runId || loadingTraceEvidenceFor.current === runId) return;
    loadingTraceEvidenceFor.current = runId;
    const evidenceEpoch = ++traceEvidenceEpoch.current;
    const workspaceEpoch = loadEpoch.current;
    try {
      const [runTrace, nextExecutionTrace] = await Promise.all([
        plotloomApi.getTrace(runId),
        plotloomApi.getRunExecutionTrace(runId).catch(() => undefined),
      ]);
      // Evidence can be large. A delayed response must never repaint another
      // run after URL/back-forward navigation changed the inspector target.
      const routeChanged = visibleRoute.current.project !== projectId
        || visibleRoute.current.stage !== "trace"
        || (visibleRoute.current.run !== "" && visibleRoute.current.run !== runId);
      if (evidenceEpoch !== traceEvidenceEpoch.current || workspaceEpoch !== loadEpoch.current || routeChanged) return;
      setTrace(traceEvents(runTrace, nextExecutionTrace));
      setExecutionTrace(nextExecutionTrace);
      loadedTraceEvidenceFor.current = runId;
    } catch (traceError) {
      const routeChanged = visibleRoute.current.project !== projectId
        || visibleRoute.current.stage !== "trace"
        || (visibleRoute.current.run !== "" && visibleRoute.current.run !== runId);
      if (evidenceEpoch === traceEvidenceEpoch.current && workspaceEpoch === loadEpoch.current && !routeChanged) setError(`无法加载运行证据：${messageFrom(traceError)}`);
    } finally {
      if (loadingTraceEvidenceFor.current === runId) loadingTraceEvidenceFor.current = undefined;
    }
  }, []);
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

  const refreshProjectDirectory = useCallback(async (includeArchived = showArchived, cursor?: string, append = false) => {
    const epoch = ++directoryEpoch.current;
    setDirectoryLoading(true);
    try {
      const response = await plotloomApi.listProjects(includeArchived, 50, cursor);
      if (epoch !== directoryEpoch.current) return;
      setProjects((current) => append
        ? [...current, ...response.projects.filter((candidate) => !current.some((existing) => existing.id === candidate.id))]
        : response.projects);
      setNextProjectCursor(response.nextCursor); setDirectoryError("");
    } catch (listError) {
      if (epoch !== directoryEpoch.current) return;
      if (!append) { setProjects([]); setNextProjectCursor(null); }
      setDirectoryError(`无法读取项目目录：${messageFrom(listError)}`);
    } finally {
      if (epoch === directoryEpoch.current) setDirectoryLoading(false);
    }
  }, [showArchived]);

  const openDirectory = () => {
    setDirectoryOpen(true); void refreshProjectDirectory();
  };
  const loadMoreProjects = () => {
    if (nextProjectCursor && !directoryLoading) void refreshProjectDirectory(showArchived, nextProjectCursor, true);
  };

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
        const updated = await plotloomApi.patchProject(project.id, project.revision, nextLocal.brief);
        // A successful write owns the draft at the revision it was sent
        // from, even if the user has already navigated elsewhere.
        discardDraft(project, "brief");
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
      const envelope = await plotloomApi.patchStage(project.id, stage, project.stageRevisions[stage], content);
      // Do not repaint a newer route, but remove the exact draft whose base
      // revision the server has accepted. A later visit always reloads its
      // canonical aggregate instead of reviving this stale session draft.
      discardDraft(project, stage);
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
    putDraft(project, scope, payload);
    if (restoredDraft?.scope === scope) setRestoredDraft({ scope, payload });
  }, [project, restoredDraft?.scope]);

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
      setPendingNavigation(normalized);
      return;
    }
    applyNavigation(normalized);
  }, [activePage, applyNavigation, project, unsafeDraft]);

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
    if (saved) setDraftRecovery({ scope, payload: saved.payload });
    else {
      const conflict = findRevisionConflict(project, scope);
      if (conflict) setDraftConflict({ scope, record: conflict, workspace: project, serverReloaded: false });
    }
  }, [activePage, draftConflict, draftRecovery, editorNonce, project, restoredDraft, unsafeDraft]);

  async function pollRun(runId: string, projectIdToRefresh = project.id) {
    const pollingEpoch = loadEpoch.current;
    if (pollingRunEpochs.current.get(runId) === pollingEpoch) return;
    const pollOperation: WorkspaceOperation = { epoch: pollingEpoch, projectId: projectIdToRefresh || "", stage: visibleRoute.current.stage };
    pollingRunEpochs.current.set(runId, pollingEpoch);
    try {
      let keepPolling = true;
      while (keepPolling) {
        const nextProgress = await plotloomApi.getRunProgress(runId);
        if (!isWorkspaceOperationCurrent(pollOperation)) return;
        setRunProgress(nextProgress);
        setRun((current) => current?.id === runId ? {
          ...current,
          status: nextProgress.status,
          failureCode: nextProgress.failureCode,
          failedStage: nextProgress.failedStage,
        } : current);
        setProject((current) => ({ ...current, quarantines: quarantineItemsFromProgress(nextProgress) }));
        keepPolling = nextProgress.status === "queued" || nextProgress.status === "running" || nextProgress.status === "cancel_requested";
        if (keepPolling) await new Promise((resolve) => window.setTimeout(resolve, 1400));
      }
      if (projectIdToRefresh && isWorkspaceOperationCurrent(pollOperation)) await loadProject(projectIdToRefresh, pollOperation.epoch);
    } catch (pollError) {
      if (isWorkspaceOperationCurrent(pollOperation)) setError(messageFrom(pollError));
    } finally {
      if (pollingRunEpochs.current.get(runId) === pollingEpoch) pollingRunEpochs.current.delete(runId);
    }
  }

  const showRunTrace = (nextRun: PipelineRun, resetTrace = true) => {
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
    if (resetTrace) {
      traceEvidenceEpoch.current += 1;
      loadedTraceEvidenceFor.current = undefined;
      loadingTraceEvidenceFor.current = undefined;
      setTrace([]);
      setExecutionTrace(undefined);
    }
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

  const openFrozenProfileSettings = async (profileId: string) => {
    setSettingsOpen(true);
    try {
      const catalog = profilesLoaded.current ? profiles : await refreshProfiles();
      const selected = catalog.profiles.find((profile) => profile.profileId === profileId);
      if (!selected) { setError(`冻结 Profile ${profileId} 已不存在；该运行不能换用其他 Profile。`); return; }
      setSelectedProfileId(profileId);
      setProfileDraft(selected);
      setSessionKey(providerSessionKeys.read(profileId));
      setProfileDirty(false);
    } catch (profileError) {
      setError(`无法读取冻结 Profile ${profileId}：${messageFrom(profileError)}`);
    }
  };

  const ensureFrozenRunCredential = async (frozenRun: PipelineRun): Promise<boolean> => {
    if (frozenRun.providerSnapshot.textAuthMode === "none") return true;
    const profileId = String(frozenRun.providerSnapshot.profileId || "default");
    let catalog = profiles;
    if (!profilesLoaded.current) catalog = await refreshProfiles();
    const profile = catalog.profiles.find((candidate) => candidate.profileId === profileId);
    if (profile?.serverKeyAvailable || providerSessionKeys.read(profileId)) return true;
    await openFrozenProfileSettings(profileId);
    setError(`运行冻结在 Profile ${profileId}；请为这个 Profile 补充当前标签页 Key 后再继续。不会自动切换模型。`);
    return false;
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

  const saveProfile = async (draft: TextProviderProfileView, key: string): Promise<TextProviderProfileView> => {
    // `none` is a complete authentication mode, not an empty bearer key. Do
    // not retain an unnecessary credential or attach it to a later request.
    if (draft.configuration.textAuthMode === "bearer") providerSessionKeys.write(draft.profileId, key);
    else providerSessionKeys.clear(draft.profileId);
    const saved = await plotloomApi.updateTextProviderProfile(
      draft.profileId, draft.revision, draft.displayName, draft.configuration,
      draft.adapterId, draft.adapterVersion,
    );
    setProfiles((current) => ({ ...current, profiles: current.profiles.map((profile) => profile.profileId === saved.profileId ? saved : profile) }));
    if (saved.profileId === selectedProfileId) {
      setProfileDraft(saved); setSessionKey(saved.configuration.textAuthMode === "bearer" ? providerSessionKeys.read(saved.profileId) : "");
    }
    setProfileDirty(false);
    return saved;
  };

  const saveCurrentProfile = async (): Promise<TextProviderProfileView> => saveProfile(profileDraft, sessionKey);

  const openSettings = async () => {
    setSettingsOpen(true);
    try { await refreshProfiles(); }
    catch {
      // Keep the legacy read as an offline/rolling-upgrade fallback. It never
      // receives a profile key and preserves the existing settings entry path.
      try {
        const legacy = await plotloomApi.getProviderSettings();
        const fallback = fallbackProfiles();
        fallback.profiles[0] = profileFromLegacySettings(legacy);
        installProfiles(fallback);
      } catch { /* Defaults remain editable offline. */ }
    }
  };

  const saveSettings = async () => {
    setBusy(true);
    try { await saveCurrentProfile(); setSettingsOpen(false); }
    catch (settingsError) { setError(messageFrom(settingsError)); }
    finally { setBusy(false); }
  };

  const selectProfile = async (profileId: string) => {
    setBusy(true); setError("");
    try {
      if (profileDirty) await saveCurrentProfile();
      const selected = profiles.profiles.find((profile) => profile.profileId === profileId);
      if (!selected) return;
      setSelectedProfileId(profileId); setProfileDraft(selected);
      setSessionKey(providerSessionKeys.read(profileId)); setProfileDirty(false);
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const createProfile = async (copy = false) => {
    const profileId = window.prompt("新 Profile ID（小写字母、数字、下划线）", "")?.trim();
    if (!profileId) return;
    const displayName = window.prompt("显示名称", profileId)?.trim();
    if (!displayName) return;
    setBusy(true); setError("");
    try {
      const source = profileDirty ? await saveCurrentProfile() : profileDraft;
      const created = await plotloomApi.createTextProviderProfile(copy
        ? { profileId, displayName, copyFromProfileId: source.profileId }
        : { profileId, displayName, configuration: { ...source.configuration, profileId, profileVersion: 0, profileHash: "", presetId: "custom" }, adapterId: source.adapterId, adapterVersion: source.adapterVersion });
      setProfiles((current) => ({ ...current, profiles: [...current.profiles, created] }));
      setSelectedProfileId(created.profileId); setProfileDraft(created); setSessionKey(providerSessionKeys.read(created.profileId)); setProfileDirty(false);
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const activateProfile = async () => {
    setBusy(true); setError("");
    try {
      if (profileDirty) await saveCurrentProfile();
      await plotloomApi.activateTextProviderProfile(profileDraft.profileId, profiles.selectionRevision);
      await refreshProfiles();
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const setProfileAvailability = async () => {
    setBusy(true); setError("");
    try {
      const updated = await plotloomApi.setTextProviderProfileAvailability(
        profileDraft.profileId, profileDraft.availabilityRevision, profileDraft.enabled === false,
      );
      // Availability is independent control-plane state. Preserve unsaved
      // configuration and the tab-only key, including edits made while this
      // request was in flight; only merge the returned availability fields.
      setProfiles((current) => {
        const next = {
          ...current,
          profiles: current.profiles.map((profile) => profile.profileId === updated.profileId
            ? { ...profile, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision }
            : profile),
        };
        profileCatalog.current = next;
        return next;
      });
      setProfileDraft((current) => current.profileId === updated.profileId
        ? { ...current, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision }
        : current);
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const deleteProfile = async () => {
    if (profileDraft.profileId === profiles.activeProfileId) { setError("请先激活另一个 Profile，再删除当前活动 Profile。"); return; }
    setBusy(true); setError("");
    try {
      await plotloomApi.deleteTextProviderProfile(profileDraft.profileId, profileDraft.revision);
      providerSessionKeys.clear(profileDraft.profileId);
      const next = await plotloomApi.getTextProviderProfiles();
      installProfiles(next);
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const testProfile = async (): Promise<void> => {
    setBusy(true); setError("");
    try {
      const saved = await saveCurrentProfile();
      const probe = await plotloomApi.probeTextProviderProfile(saved.profileId, saved.configuration.textAuthMode === "bearer");
      await refreshProfiles();
      setError(probe.state === "available" ? `后端已就绪：${probe.reasonCode}` : `后端状态：${probe.state} · ${probe.reasonCode}`);
    } catch (profileError) { setError(messageFrom(profileError)); }
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
      case "bible": return <StoryBiblePage key={`${editorRevisionKey(project, "story_bible")}:${editorNonce}`} value={recoveredValue("story_bible", project.storyBible)} stale={project.staleStages.includes("story_bible")} saving={projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ sceneBeats: project.sceneBeats, storyboard: project.storyboard }} issues={validationIssues.story_bible} onEntitySelect={selectRouteEntity} onSave={(value: StoryBible) => commitStage("story_bible", value)} onDraftChange={(value) => rememberDraft("story_bible", value)} />;
      case "graph": return <GraphPage key={`${editorRevisionKey(project, "story_graph")}:${editorNonce}`} value={recoveredValue("story_graph", project.storyGraph)} stale={project.staleStages.includes("story_graph")} saving={projectSaving || projectReadOnly} entityId={routeEntity} sceneReferences={project.sceneBeats.scenes.map((scene) => ({ id: scene.id, storyNodeId: scene.storyNodeId, title: scene.title }))} issues={validationIssues.story_graph} onEntitySelect={selectRouteEntity} onSave={(value: StoryGraph) => commitStage("story_graph", value)} onDraftChange={(value) => rememberDraft("story_graph", value)} />;
      case "beats": return <SceneBeatsPage key={`${editorRevisionKey(project, "scene_beats")}:${editorNonce}`} value={recoveredValue("scene_beats", project.sceneBeats)} stale={project.staleStages.includes("scene_beats")} saving={projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ nodes: project.storyGraph.nodes, characters: project.storyBible.characters, locations: project.storyBible.locations, props: project.storyBible.props, storyboard: { shots: project.storyboard.shots.map(({ id, sceneId, cueIds }) => ({ id, sceneId, cueIds })), shotBeatLinks: project.storyboard.shotBeatLinks.map(({ shotId, beatId }) => ({ shotId, beatId })) } }} issues={validationIssues.scene_beats} onEntitySelect={selectRouteEntity} onSave={(value: SceneBeatPlan) => commitStage("scene_beats", value)} onDraftChange={(value) => rememberDraft("scene_beats", value)} />;
      case "storyboard": return <StoryboardPage key={`${editorRevisionKey(project, "storyboard")}:${editorNonce}`} projectId={project.id} revision={stageHeads.storyboard?.revision} contentHash={stageHeads.storyboard?.contentHash} bible={project.storyBible} graph={project.storyGraph} sceneBeats={project.sceneBeats} value={recoveredValue("storyboard", project.storyboard)} stale={project.staleStages.includes("storyboard")} mediaTasks={mediaTasks} saving={projectSaving || projectReadOnly} entityId={routeEntity} issues={validationIssues.storyboard} review={storyboardReview} onEntitySelect={selectRouteEntity} onNavigateIssue={(stage, entity) => requestNavigation({ project: navigationProjectId, stage, entity })} onReviewChange={setStoryboardReview} onSave={(value: Storyboard) => commitStage("storyboard", value)} onDraftChange={(value) => rememberDraft("storyboard", value)} />;
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
      <header className="topbar"><div><span>{currentNav.index}</span><strong>{currentNav.label}</strong></div><div className="topbar-actions">{projectReadOnly && <Badge tone="warning">归档只读</Badge>}<Badge tone={connection === "connected" ? "ok" : connection === "loading" ? "accent" : "warning"}>Plotloom 服务：{connection === "connected" ? "已连接" : connection === "loading" ? "连接中" : "未连接"}</Badge><Badge tone={profileDraft.readiness?.state === "available" ? "ok" : ["unreachable", "authentication_failed", "model_mismatch", "capability_mismatch"].includes(profileDraft.readiness?.state || "unverified") ? "danger" : "warning"}>文本后端：{profileDraft.readiness?.state || "unverified"} · {profileDraft.profileId} · {profileDraft.readiness?.reasonCode || "readiness.not_checked"}{profileDraft.readiness?.observedAt ? ` · ${new Date(profileDraft.readiness.observedAt).toLocaleString()}` : " · 未检测"}</Badge>{running && <Spinner label={runProgress?.failedStage ? stageLabels[runProgress.failedStage] : "Pipeline"} />}<Button variant="quiet" disabled={!project.id || connection === "loading"} onClick={requestProjectRefresh}>刷新服务器版本</Button>{staleCount > 0 && <Button variant="quiet" disabled={projectReadOnly} onClick={() => setRebuildOpen(true)}>{staleCount} 个阶段待重建</Button>}</div></header>
      {error && <div className="global-error"><ErrorNotice message={error} /><button aria-label="关闭错误" onClick={() => setError("")}>×</button></div>}
      <div className="workbench-grid">
        <aside className="context-panel"><span className="eyebrow">Context</span><strong>{project.brief.title || "新项目"}</strong><small>{project.lifecycleStatus === "archived" || project.archivedAt ? "归档快照 · 仅供审阅" : project.id ? `项目 ${project.id}` : navigationProjectId ? `加载项目 ${navigationProjectId}` : "空白项目；保存后建立规范项目"}</small><div className="context-stages">{navigation.slice(0, 5).map((item) => <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => requestNavigation({ project: navigationProjectId, stage: item.id })}>{item.index} {item.label}</button>)}</div><div className="context-assets"><span className="eyebrow">Canon assets</span>{bibleAssets.map((asset) => <div key={asset.label}><strong>{asset.label} · {asset.items.length}</strong><small>{asset.items.length ? asset.items.slice(0, 3).map((item) => item.name).join("、") : "尚未定义"}{asset.items.length > 3 ? " …" : ""}</small></div>)}</div></aside>
        <main id="workspace-main">{workspaceHydrating
          ? <div className="workspace-hydrating" data-testid="workspace-hydrating" role="status"><Spinner label="正在加载项目" /><strong>正在加载项目…</strong><small>项目内容加载完成后才能编辑，当前导航选择会被保留。</small></div>
          : <fieldset className="editor-host" disabled={projectReadOnly}>{page}</fieldset>}</main>
        <WorkspaceInspector currentLabel={currentNav.label} project={project} routeEntity={routeEntity} stageOverview={stageOverview} run={run} progress={runProgress} review={storyboardReview} readOnly={projectReadOnly} frozenProfileId={frozenProfileId} frozenProfileNeedsKey={frozenProfileNeedsKey} onAuthorizeProfile={() => void openFrozenProfileSettings(frozenProfileId)} onOpenTrace={() => requestNavigation({ project: navigationProjectId, stage: "trace", run: run?.id || "" })} onResume={resumeRun} onCancel={cancelRun} onRepair={repair} onRebuild={(stage) => { setRebuildOpen(false); void rebuild(stage); }} />
      </div>
    </div>
    {settingsOpen && <SettingsDialog profiles={profiles} selectedProfileId={selectedProfileId} draft={profileDraft} sessionKey={sessionKey} busy={busy} onDraft={(draft) => { setProfileDraft(draft); setProfileDirty(true); }} onSessionKey={setSessionKey} onSelect={selectProfile} onCreate={() => createProfile(false)} onCopy={() => createProfile(true)} onDelete={deleteProfile} onActivate={activateProfile} onAvailability={setProfileAvailability} onProbe={testProfile} onClose={() => setSettingsOpen(false)} onSave={saveSettings} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={rebuild} />}
    {directoryOpen && <ProjectDirectoryDialog projects={projects} showArchived={showArchived} error={directoryError} loading={directoryLoading} hasMore={Boolean(nextProjectCursor)} onLoadMore={loadMoreProjects} onArchived={(next) => { setShowArchived(next); void refreshProjectDirectory(next); }} onBlank={startBlankProject} onSample={openSampleProject} onOpen={(item) => { setDirectoryOpen(false); requestNavigation({ project: item.id, stage: "brief" }); }} onAction={mutateProjectLifecycle} onClose={() => setDirectoryOpen(false)} />}
    {pendingNavigation && !unsafeDraft && <DraftNavigationDialog onSave={() => void resolvePendingNavigation("save")} onDiscard={() => void resolvePendingNavigation("discard")} onCancel={() => void resolvePendingNavigation("cancel")} />}
    {pendingArchive && <DraftNavigationDialog onSave={() => void resolvePendingArchive("save")} onDiscard={() => void resolvePendingArchive("discard")} onCancel={() => void resolvePendingArchive("cancel")} />}
    {draftRecovery && <DraftRecoveryDialog onRestore={() => { currentDraft.current = { scope: draftRecovery.scope, payload: draftRecovery.payload }; setRestoredDraft(draftRecovery); setEditorNonce((value) => value + 1); setDraftRecovery(undefined); }} onDiscard={() => { discardDraft(project, draftRecovery.scope); setDraftRecovery(undefined); setRestoredDraft(undefined); setEditorNonce((value) => value + 1); }} />}
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

function WorkspaceInspector({ currentLabel, project, routeEntity, stageOverview, run, progress, review, readOnly, frozenProfileId, frozenProfileNeedsKey, onAuthorizeProfile, onOpenTrace, onResume, onCancel, onRepair, onRebuild }: {
  currentLabel: string;
  project: WorkspaceProject;
  routeEntity: string;
  stageOverview: Array<{ stage: ServerStageName; status: string }>;
  run?: PipelineRun;
  progress?: RunProgress;
  review: StoryboardReview | null;
  readOnly: boolean;
  frozenProfileId: string;
  frozenProfileNeedsKey: boolean;
  onAuthorizeProfile: () => void;
  onOpenTrace: () => void;
  onResume: () => Promise<void>;
  onCancel: () => Promise<void>;
  onRepair: (item: QuarantineItem) => Promise<void>;
  onRebuild: (stage: ServerStageName) => void;
}) {
  const requiredGates = review?.gateEvaluation?.results.filter((gate) => gate.required) ?? [];
  const failedRequiredGates = requiredGates.filter((gate) => gate.status !== "pass");
  return <aside className="workspace-inspector" data-testid="workspace-inspector">
    <span className="eyebrow">Inspector</span><strong>{currentLabel}</strong>
    <dl><div><dt>项目版本</dt><dd>r{project.revision}</dd></div><div><dt>实体</dt><dd>{routeEntity || "未选择"}</dd></div></dl>
    <div className="inspector-stages"><span className="eyebrow">Canonical stages</span>{stageOverview.map(({ stage, status }) => {
      const stageProgress = progress?.stageProgress.find((candidate) => candidate.stage === stage);
      return <div key={stage}><span>{stageLabels[stage]}{stageProgress && <small>{stageProgress.completedUnitCount}/{stageProgress.unitCount} units · {stageProgress.sealed ? "SEALED" : "OPEN"}</small>}</span><Badge tone={status === "ready" ? "ok" : status === "stale" ? "warning" : "neutral"}>{status.toUpperCase()}</Badge></div>;
    })}</div>
    <div className="inspector-run"><span className="eyebrow">Latest run</span>{run ? <><strong>{run.status} · {run.kind}</strong><small>{run.id}</small><small>{run.startedAt ? `开始 ${new Date(run.startedAt).toLocaleString()}` : `创建 ${new Date(run.createdAt).toLocaleString()}`}{run.finishedAt ? ` · 完成 ${new Date(run.finishedAt).toLocaleString()}` : ""}</small>{progress?.failureCode && <small className="danger-copy">{progress.failureCode}</small>}{frozenProfileNeedsKey && <div className="notice warning"><strong>冻结 Profile 缺少会话 Key</strong><span>{frozenProfileId}；补 Key 后继续，不会自动换模型。</span><Button variant="quiet" onClick={onAuthorizeProfile}>为冻结 Profile 补 Key</Button></div>}<Button variant="quiet" onClick={onOpenTrace}>按需打开 Prompt / 原始响应</Button></> : <small>尚无运行记录</small>}</div>
    {progress && <details className="inspector-units" open={progress.status === "quarantined"}><summary>Work units · {progress.workUnits.length}</summary>{progress.workUnits.map((unit) => {
      const attempt = unit.latestAttempt;
      const quarantine = project.quarantines.find((item) => item.id === unit.workUnitId);
      return <div className="inspector-unit" key={unit.workUnitId}><strong>{unit.stage} · #{unit.sequence}</strong><small>{unit.status} · seal {unit.sealed ? "yes" : "no"}</small><small>Attempt {attempt ? `${attempt.attemptNumber}/${unit.maxAttempts}` : `—/${unit.maxAttempts}`} · {formatDuration(attempt?.durationMs)} · token {attempt?.inputTokens ?? "—"}/{attempt?.outputTokens ?? "—"}</small>{attempt?.outcomeCode && <small>{attempt.outcomeCode}</small>}{unit.repairEligible && quarantine && <Button variant="quiet" disabled={readOnly} onClick={() => void onRepair(quarantine)}>修复这个 work unit</Button>}</div>;
    })}</details>}
    {progress && <div className="inspector-actions"><span className="eyebrow">Server-authorized actions</span>{progress.actions.canResume && <Button variant="quiet" disabled={readOnly} onClick={() => void onResume()}>继续运行</Button>}{progress.actions.canCancel && <Button variant="danger" disabled={readOnly} onClick={() => void onCancel()}>取消运行</Button>}{progress.actions.canRebuildStage && <Button variant="quiet" disabled={readOnly || !progress.failedStage} onClick={() => progress.failedStage && onRebuild(progress.failedStage)}>从失败阶段完整重建</Button>}</div>}
    <div className="inspector-review"><span className="eyebrow">Gate & Approval</span>{review?.gateEvaluation ? <><strong>{failedRequiredGates.length ? `${failedRequiredGates.length} 个 required gate 未通过` : `${requiredGates.length} 个 required gate 已通过`}</strong><small>{review.gateEvaluation.gateSetVersion}</small></> : <small>尚无 Gate receipt</small>}{review?.activeApproval ? <><Badge tone="ok">APPROVED</Badge><small>{review.activeApproval.reviewer} · r{review.activeApproval.subjectRevision}</small></> : <Badge tone={failedRequiredGates.length ? "danger" : "neutral"}>UNAPPROVED</Badge>}</div>
    {readOnly && <p>归档项目不可编辑或运行。请在项目目录中恢复后继续。</p>}
  </aside>;
}

function SettingsDialog({ profiles, selectedProfileId, draft, sessionKey, busy, onDraft, onSessionKey, onSelect, onCreate, onCopy, onDelete, onActivate, onAvailability, onProbe, onClose, onSave }: { profiles: TextProviderProfilesResponse; selectedProfileId: string; draft: TextProviderProfileView; sessionKey: string; busy: boolean; onDraft: (draft: TextProviderProfileView) => void; onSessionKey: (key: string) => void; onSelect: (profileId: string) => Promise<void>; onCreate: () => Promise<void>; onCopy: () => Promise<void>; onDelete: () => Promise<void>; onActivate: () => Promise<void>; onAvailability: () => Promise<void>; onProbe: () => Promise<void>; onClose: () => void; onSave: () => Promise<void> }) {
  const configuration = draft.configuration;
  const trustedAdapters = profiles.trustedAdapters || [{ adapterId: "openai_compatible", adapterVersion: "1" }];
  const update = (patch: Partial<TextProviderProfileConfiguration>) => onDraft({ ...draft, configuration: { ...configuration, ...patch } });
  const field = (key: "textProvider" | "textBaseUrl" | "textModel", label: string) => <label><span>{label}</span><input value={configuration[key]} onChange={(event) => update({ [key]: event.target.value } as Partial<TextProviderProfileConfiguration>)} /></label>;
  const numberField = (key: "textContextWindowTokens" | "textMaxOutputTokens" | "textTemperature" | "textMaxConcurrency" | "textConnectTimeoutSeconds" | "textAttemptTimeoutSeconds" | "maxSemanticCorrections", label: string) => <label><span>{label}</span><input type="number" value={configuration[key]} onChange={(event) => update({ [key]: Number(event.target.value), presetId: "custom" } as Partial<TextProviderProfileConfiguration>)} /></label>;
  const stageNumberField = (stage: ServerStageName) => <label><span>{stageLabels[stage]}最大输出 token</span><input type="number" value={configuration.stageMaxOutputTokens[stage]} onChange={(event) => update({ stageMaxOutputTokens: { ...configuration.stageMaxOutputTokens, [stage]: Number(event.target.value) }, presetId: "custom" })} /></label>;
  const capability = (key: keyof TextProviderProfileConfiguration["textCapabilities"], label: string) => <label><span>{label}</span><input type="checkbox" checked={configuration.textCapabilities[key]} onChange={(event) => update({ textCapabilities: { ...configuration.textCapabilities, [key]: event.target.checked }, presetId: "custom" })} /></label>;
  const applyPreset = (presetId: Exclude<TextProviderPresetId, "custom">) => {
    const preset = profiles.presets[presetId];
    update({ ...preset, presetId, textCapabilities: { ...configuration.textCapabilities, chatTemplateKwargs: preset.requestExtension === "chat_template_kwargs" } });
  };
  const keyHint = draft.serverKeyAvailable
    ? "服务器已配置文本密钥；留空即使用服务器密钥，填写则仅覆盖当前标签页。"
    : "服务器没有可用密钥；填写后仅在当前标签页会话中使用。";
  const unavailable = draft.enabled === false;
  const readiness = draft.readiness;
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card"><header><div><span>Text provider profile · {draft.profileId} r{draft.revision}</span><h2 id="settings-title">供应商 Profile 与会话 Key</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice"><strong>Key 不进入项目</strong><span>每个 Profile 的 Key 仅写入当前标签页 sessionStorage；保存、测试和生成请求都不会将它写入 JSON。</span></div><label><span>活动 Profile</span><select value={selectedProfileId} disabled={busy} onChange={(event) => void onSelect(event.target.value)}>{profiles.profiles.map((profile) => <option key={profile.profileId} value={profile.profileId}>{profile.displayName} · {profile.profileId}{profile.profileId === profiles.activeProfileId ? " · active" : ""}{profile.enabled === false ? " · unavailable" : ""}</option>)}</select></label><div className="profile-actions"><Button disabled={busy} onClick={() => void onCreate()}>新建</Button><Button disabled={busy} onClick={() => void onCopy()}>复制</Button><Button disabled={busy || draft.profileId === profiles.activeProfileId} variant="danger" onClick={() => void onDelete()}>删除</Button><Button disabled={busy || unavailable || draft.profileId === profiles.activeProfileId} onClick={() => void onActivate()}>设为活动</Button><Button disabled={busy} onClick={() => void onAvailability()}>{unavailable ? "启用后端" : "停用后端"}</Button></div><div className="notice"><strong>就绪状态：{readiness.state} · {readiness.reasonCode}</strong><span>Profile {readiness.profileId} r{readiness.profileRevision} · {readiness.observedAt ? new Date(readiness.observedAt).toLocaleString() : "尚未检测"}。{readinessRemediation(readiness.state)}</span></div>{unavailable && <div className="notice"><strong>此后端当前不可用</strong><span>新生成、重建和修复不会被接纳；已接纳的运行仍可按冻结 Profile 完成。启用后需重新确认服务就绪。</span></div>}<label><span>显示名称</span><input value={draft.displayName} onChange={(event) => onDraft({ ...draft, displayName: event.target.value })} /></label><label><span>受信任适配器</span><select value={`${draft.adapterId}@${draft.adapterVersion}`} onChange={(event) => { const selected = trustedAdapters.find((item) => `${item.adapterId}@${item.adapterVersion}` === event.target.value); if (selected) onDraft({ ...draft, adapterId: selected.adapterId, adapterVersion: selected.adapterVersion }); }}>{trustedAdapters.map((item) => <option key={`${item.adapterId}@${item.adapterVersion}`} value={`${item.adapterId}@${item.adapterVersion}`}>{item.adapterId} v{item.adapterVersion}</option>)}</select><small>适配器按 Profile 保存并冻结到新运行；端点、模型名或供应商标签不会选择代码路径。</small></label><label><span>执行预设</span><select value={configuration.presetId} onChange={(event) => event.target.value === "custom" ? update({ presetId: "custom" }) : applyPreset(event.target.value as Exclude<TextProviderPresetId, "custom">)}><option value="compatible_v1">兼容模式</option><option value="quality_reasoning_v1">高质量推理</option><option value="final_only_v1">仅最终答案</option><option value="custom">高级自定义</option></select></label>{field("textProvider", "文本供应商")}{field("textBaseUrl", "文本 API 根地址")}{field("textModel", "文本模型")}<label><span>文本认证</span><select value={configuration.textAuthMode} onChange={(event) => update({ textAuthMode: event.target.value as "none" | "bearer" })}><option value="none">none（不发送 Authorization）</option><option value="bearer">bearer</option></select></label><div className="profile-capabilities">{capability("chatCompletions", "支持 Chat Completions")}{capability("jsonObject", "支持 JSON object")}{capability("jsonSchema", "支持 JSON schema")}{capability("chatTemplateKwargs", "支持 Chat Template 参数")}</div><details><summary>高级设置</summary><div className="advanced-settings">{numberField("textContextWindowTokens", "文本上下文 token")}{numberField("textMaxOutputTokens", "文本最大输出 token")}{numberField("textTemperature", "文本 temperature")}{numberField("textMaxConcurrency", "文本并发")}{numberField("textConnectTimeoutSeconds", "文本连接超时（秒）")}{numberField("textAttemptTimeoutSeconds", "文本尝试超时（秒）")}{numberField("maxSemanticCorrections", "语义修正次数")}{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map(stageNumberField)}<label><span>请求扩展</span><select value={configuration.requestExtension} onChange={(event) => update({ requestExtension: event.target.value as TextProviderProfileConfiguration["requestExtension"], presetId: "custom" })}><option value="none">none</option><option value="chat_template_kwargs">chat_template_kwargs</option></select></label><label><span>推理模式</span><select value={configuration.reasoningMode} onChange={(event) => update({ reasoningMode: event.target.value as TextProviderProfileConfiguration["reasoningMode"], presetId: "custom" })}><option value="provider_default">provider_default</option><option value="enabled">enabled</option><option value="disabled">disabled</option></select></label><label><span>允许 JSON Fence</span><input type="checkbox" checked={configuration.extractionPolicy.allowJsonFence} onChange={(event) => update({ extractionPolicy: { ...configuration.extractionPolicy, allowJsonFence: event.target.checked }, presetId: "custom" })} /></label><label><span>允许开头 Think Block</span><input type="checkbox" checked={configuration.extractionPolicy.allowLeadingThinkBlock} onChange={(event) => update({ extractionPolicy: { ...configuration.extractionPolicy, allowLeadingThinkBlock: event.target.checked }, presetId: "custom" })} /></label></div></details>{configuration.textAuthMode === "bearer" ? <label><span>此 Profile 的临时 API Key</span><input type="password" autoComplete="off" value={sessionKey} placeholder={draft.serverKeyAvailable ? "留空使用服务器密钥" : "当前标签页的临时密钥"} onChange={(event) => onSessionKey(event.target.value)} /><small>{keyHint}</small></label> : <div className="notice"><strong>此 Profile 不需要 API Key</strong><span>authMode 为 none；保存后会清除此 Profile 的临时 key，测试和生成也不会发送它。</span></div>}</div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button disabled={busy || unavailable} onClick={() => void onProbe()}>{busy ? "正在处理…" : "测试连接"}</Button><Button variant="primary" disabled={busy} onClick={() => void onSave()}>{busy ? "正在保存…" : "保存设置"}</Button></footer></section></div>;
}

function RebuildDialog({ staleStages, busy, onClose, onRebuild }: { staleStages: ServerStageName[]; busy: boolean; onClose: () => void; onRebuild: (stage: ServerStageName) => Promise<void> }) {
  const [stage, setStage] = useState<ServerStageName>(staleStages[0] || "story_bible");
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rebuild-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card compact"><header><div><span>Dependency-aware rebuild</span><h2 id="rebuild-title">重建过期阶段</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice warning"><strong>现有内容不会静默覆盖</strong><span>服务器从选择的阶段创建可追踪运行；验证失败的输出进入隔离区。</span></div><label><span>从哪个阶段开始</span><select value={stage} onChange={(event) => setStage(event.target.value as ServerStageName)}>{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((item) => <option key={item} value={item}>{stageLabels[item]}{staleStages.includes(item) ? " · 待重建" : ""}</option>)}</select></label></div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button variant="primary" disabled={busy} onClick={() => void onRebuild(stage)}>创建重建运行</Button></footer></section></div>;
}

function WelcomeOnboarding({ onBlank, onSample, onDirectory }: { onBlank: () => void; onSample: () => void; onDirectory: () => void }) {
  return <main className="welcome-shell"><section className="welcome-card"><div className="brand-mark">PL</div><span className="eyebrow">Plotloom workbench</span><h1>从一个项目开始</h1><p>创建空白项目以编写自己的故事，打开示例以浏览完整工作流，或从目录继续已有项目。</p><div className="welcome-actions"><Button variant="primary" onClick={onBlank}>创建空白项目</Button><Button onClick={onSample}>打开示例项目</Button><Button variant="quiet" onClick={onDirectory}>打开项目目录</Button></div><small>示例不会在未选择时自动加载，也不会覆盖加载失败的项目。</small></section></main>;
}

function ProjectDirectoryDialog({ projects, showArchived, error, loading, hasMore, onLoadMore, onArchived, onBlank, onSample, onOpen, onAction, onClose }: { projects: ProjectListItem[]; showArchived: boolean; error: string; loading: boolean; hasMore: boolean; onLoadMore: () => void; onArchived: (show: boolean) => void; onBlank: () => void; onSample: () => void; onOpen: (project: ProjectListItem) => void; onAction: (project: ProjectListItem, action: "archive" | "restore" | "duplicate" | "delete") => Promise<void>; onClose: () => void }) {
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="project-directory-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card directory-dialog"><header><div><span>Project directory</span><h2 id="project-directory-title">项目目录</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="directory-onboarding"><Button variant="primary" onClick={onBlank}>新建空白项目</Button><Button onClick={onSample}>打开示例项目</Button><label><input type="checkbox" checked={showArchived} onChange={(event) => onArchived(event.target.checked)} /> 显示归档项目</label></div>{error && <ErrorNotice message={error} />}{!error && !loading && !projects.length && <div className="empty-state"><strong>还没有可用项目</strong><p>从空白项目开始，或先浏览教学示例。</p></div>}<div className="directory-list">{projects.map((item) => <article key={item.id} className="directory-item"><button className="directory-open" onClick={() => onOpen(item)}><strong>{item.brief.title || "未命名项目"}</strong><small>{item.lifecycleStatus === "archived" || item.archivedAt ? "已归档 · 只读" : "活动中"} · r{item.revision} · {new Date(item.updatedAt).toLocaleString()}</small></button><div className="directory-actions"><Button variant="quiet" onClick={() => void onAction(item, "duplicate")}>复制</Button>{item.lifecycleStatus === "archived" || item.archivedAt ? <><Button variant="quiet" onClick={() => void onAction(item, "restore")}>恢复</Button><Button variant="danger" onClick={() => void onAction(item, "delete")}>永久删除</Button></> : <Button variant="quiet" onClick={() => void onAction(item, "archive")}>归档</Button>}</div></article>)}</div>{hasMore && <div className="directory-more"><Button disabled={loading} onClick={onLoadMore}>{loading ? "正在加载…" : "加载更多项目"}</Button></div>}</div><footer><Button variant="quiet" onClick={onClose}>关闭</Button></footer></section></div>;
}

function DraftNavigationDialog({ onSave, onDiscard, onCancel }: { onSave: () => void; onDiscard: () => void; onCancel: () => void }) {
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-navigation-title"><button className="modal-backdrop" aria-label="继续编辑" onClick={onCancel} /><section className="modal-card compact"><header><div><span>Unsaved draft</span><h2 id="draft-navigation-title">保存当前草稿？</h2></div></header><div className="modal-body"><div className="notice warning"><strong>即将切换工作台</strong><span>当前阶段有未保存修改。保存会显式写入项目；丢弃只移除本标签页草稿。</span></div></div><footer><Button variant="quiet" onClick={onCancel}>取消</Button><Button variant="danger" onClick={onDiscard}>丢弃</Button><Button variant="primary" onClick={onSave}>保存并切换</Button></footer></section></div>;
}

function DraftRecoveryDialog({ onRestore, onDiscard }: { onRestore: () => void; onDiscard: () => void }) {
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-recovery-title"><button className="modal-backdrop" aria-label="保留提示" /><section className="modal-card compact"><header><div><span>Session recovery</span><h2 id="draft-recovery-title">发现未保存草稿</h2></div></header><div className="modal-body"><div className="notice"><strong>可恢复</strong><span>此草稿保存在当前标签页 sessionStorage，尚未写入服务器。</span></div></div><footer><Button variant="quiet" onClick={onDiscard}>丢弃草稿</Button><Button variant="primary" onClick={onRestore}>恢复草稿</Button></footer></section></div>;
}

function DraftConflictDialog({ serverReloaded, busy, onReload, onCopy, onDiscard }: { serverReloaded: boolean; busy: boolean; onReload: () => void; onCopy: () => void; onDiscard: () => void }) {
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-conflict-title"><button className="modal-backdrop" aria-label="保留提示" /><section className="modal-card compact"><header><div><span>Draft conflict</span><h2 id="draft-conflict-title">草稿版本已过期</h2></div></header><div className="modal-body"><div className="notice warning"><strong>草稿已保护，不会强制覆盖</strong><span>{serverReloaded ? "已重新加载服务器规范版本；冲突草稿仍保留，可复制成独立项目。" : "服务器项目已经更新。可先查看服务器版本，或把当前草稿及其连续阶段前缀复制成新项目。"}</span></div></div><footer><Button variant="quiet" disabled={busy || serverReloaded} onClick={onReload}>{serverReloaded ? "已加载服务器版本" : "重新加载服务器版本"}</Button><Button variant="primary" disabled={busy} onClick={onCopy}>{busy ? "正在复制…" : "复制草稿为新项目"}</Button><Button variant="danger" disabled={busy} onClick={onDiscard}>丢弃冲突草稿</Button></footer></section></div>;
}

function UnsafeDraftDialog({ reason, onDiscard }: { reason: "archived" | "unavailable"; onDiscard: () => void }) {
  const unavailable = reason === "unavailable";
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="unsafe-draft-title"><button className="modal-backdrop" aria-label="保留提示" /><section className="modal-card compact"><header><div><span>Draft safety</span><h2 id="unsafe-draft-title">{unavailable ? "项目不可用，草稿不可恢复" : "归档项目草稿不可恢复"}</h2></div></header><div className="modal-body"><div className="notice warning"><strong>仅可安全丢弃</strong><span>{unavailable ? "项目加载失败或已删除。为避免把草稿写入错误项目，不能恢复或保存此草稿。" : "归档项目为只读。请先恢复项目并从新的服务端版本继续；此标签页草稿不能恢复或保存。"}</span></div></div><footer><Button variant="danger" onClick={onDiscard}>丢弃不可用草稿</Button></footer></section></div>;
}
