import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MediaKind, MediaTask, PipelineRun, ProviderSettings, QuarantineItem, RunExecutionTrace, SceneBeatPlan, ServerStageName, Shot, StoryBible, StoryGraph, Storyboard, TextProviderPresetId, TextProviderProfileConfiguration, TextProviderProfilesResponse, TextProviderProfileView, TraceEvent, WorkspaceProject } from "./types";
import { plotloomApi, ApiError } from "./api";
import { providerSessionKeys } from "./session-key";
import { defaultProviderSettings, demoProject, demoRun, demoTrace } from "./demo";
import { markDownstreamStale, mergeProjectResponse, stageLabels, traceEvents } from "./model";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "./project-creation";
import { editorRevisionKey, hydrateWorkspaceProject, newestMediaTasksByShot, quarantineItemsFromTrace } from "./workspace-state";
import { Badge, Button, ErrorNotice, Spinner } from "./components";
import { BriefPage } from "./pages/BriefPage";
import { StoryBiblePage } from "./pages/StoryBiblePage";
import { GraphPage } from "./pages/GraphPage";
import { SceneBeatsPage } from "./pages/SceneBeatsPage";
import { StoryboardPage } from "./pages/StoryboardPage";
import { TracePage } from "./pages/TracePage";
import { QuarantinePage } from "./pages/QuarantinePage";

type PageId = "brief" | "bible" | "graph" | "beats" | "storyboard" | "trace" | "quarantine";

const navigation: { id: PageId; index: string; label: string; description: string }[] = [
  { id: "brief", index: "01", label: "项目简报", description: "边界与预算" },
  { id: "bible", index: "02", label: "故事圣经", description: "人物与规则" },
  { id: "graph", index: "03", label: "剧情 DAG", description: "分支与汇合" },
  { id: "beats", index: "04", label: "场景节拍", description: "原子事件" },
  { id: "storyboard", index: "05", label: "分镜工作台", description: "路径与媒体" },
  { id: "trace", index: "06", label: "运行轨迹", description: "Prompt 与证据" },
  { id: "quarantine", index: "07", label: "隔离修复", description: "安全失败" },
];

function messageFrom(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) return `项目版本冲突：${error.message}。请刷新后再合并修改。`;
  return error instanceof Error ? error.message : "未知错误";
}

function projectIdFromLocation(): string {
  return new URLSearchParams(window.location.search).get("project") || "";
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
  return { profileId: "default", displayName: "Default", configuration, revision: 0, createdAt: "", updatedAt: "", serverKeyAvailable: false };
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
  presets: {
    compatible_v1: { presetId: "compatible_v1", presetVersion: "1", requestExtension: "none", reasoningMode: "provider_default", textContextWindowTokens: 32768, textMaxOutputTokens: 8192, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, textAttemptTimeoutSeconds: 300, maxSemanticCorrections: 2 },
    quality_reasoning_v1: { presetId: "quality_reasoning_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "enabled", textContextWindowTokens: 131072, textMaxOutputTokens: 32768, stageMaxOutputTokens: { story_bible: 32768, story_graph: 32768, scene_beats: 32768, storyboard: 32768 }, textAttemptTimeoutSeconds: 900, maxSemanticCorrections: 2 },
    final_only_v1: { presetId: "final_only_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "disabled", textContextWindowTokens: 32768, textMaxOutputTokens: 16384, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 8192, storyboard: 8192 }, textAttemptTimeoutSeconds: 600, maxSemanticCorrections: 2 },
  },
});

export default function App() {
  const [activePage, setActivePage] = useState<PageId>("brief");
  const [project, setProject] = useState<WorkspaceProject>(demoProject);
  const [connection, setConnection] = useState<"loading" | "connected" | "demo">("loading");
  const [busy, setBusy] = useState(false);
  const [projectSaving, setProjectSaving] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState<PipelineRun | undefined>(demoRun);
  const [trace, setTrace] = useState<TraceEvent[]>(demoTrace);
  const [mediaTasks, setMediaTasks] = useState<Record<string, MediaTask>>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [rebuildOpen, setRebuildOpen] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => providerSessionKeys.read("default"));
  const [profiles, setProfiles] = useState<TextProviderProfilesResponse>(fallbackProfiles);
  const [selectedProfileId, setSelectedProfileId] = useState("default");
  const [profileDraft, setProfileDraft] = useState<TextProviderProfileView>(defaultTextProfile);
  const [profileDirty, setProfileDirty] = useState(false);
  const [executionTrace, setExecutionTrace] = useState<RunExecutionTrace | undefined>();
  const pollingRunIds = useRef(new Set<string>());
  const projectSaveInFlight = useRef(false);
  const creationKeyByBody = useRef(new Map<string, string>());
  const profilesLoaded = useRef(false);

  const installProfiles = useCallback((next: TextProviderProfilesResponse, selectedId = next.activeProfileId) => {
    const selected = next.profiles.find((profile) => profile.profileId === selectedId) || next.profiles[0];
    if (!selected) return;
    profilesLoaded.current = true;
    setProfiles(next); setSelectedProfileId(selected.profileId); setProfileDraft(selected);
    setSessionKey(providerSessionKeys.read(selected.profileId)); setProfileDirty(false);
  }, []);

  const refreshProfiles = useCallback(async (): Promise<TextProviderProfilesResponse> => {
    const next = await plotloomApi.getTextProviderProfiles();
    installProfiles(next);
    return next;
  }, [installProfiles]);

  const loadProject = useCallback(async (projectId: string) => {
    if (!projectId) { setConnection("demo"); return; }
    setConnection("loading");
    try {
      const [incoming, stageResponse, runResponse, mediaResponse] = await Promise.all([
        plotloomApi.getProject(projectId),
        plotloomApi.getStages(projectId),
        plotloomApi.getProjectRuns(projectId),
        plotloomApi.getProjectMediaTasks(projectId),
      ]);
      const latestRun = runResponse.runs[0];
      const latestTrace = latestRun ? await plotloomApi.getTrace(latestRun.id) : undefined;
      // The execution shard is additive. A rolling upgrade must keep the
      // compact trace usable even if this endpoint is temporarily unavailable.
      const latestExecutionTrace = latestRun
        ? await plotloomApi.getRunExecutionTrace(latestRun.id).catch(() => undefined)
        : undefined;
      const quarantines = latestTrace ? quarantineItemsFromTrace(latestTrace) : [];
      setProject((current) => ({ ...hydrateWorkspaceProject(current, incoming, stageResponse.stages), quarantines }));
      setRun(latestRun);
      setTrace(latestTrace ? traceEvents(latestTrace, latestExecutionTrace) : []);
      setExecutionTrace(latestExecutionTrace);
      setMediaTasks(newestMediaTasksByShot(mediaResponse.tasks));
      setConnection("connected");
      setError("");
      if (latestRun && (latestRun.status === "queued" || latestRun.status === "running" || latestRun.status === "cancel_requested")) {
        if (latestRun.status === "cancel_requested") {
          void pollRun(latestRun.id, incoming.id).catch((pollError) => setError(messageFrom(pollError)));
        } else {
          const frozenProfileId = String(latestRun.providerSnapshot.profileId || "default");
          const usesBearer = latestRun.providerSnapshot.textAuthMode !== "none";
          void plotloomApi.resumeRun(latestRun.id, frozenProfileId, usesBearer)
            .then(() => pollRun(latestRun.id, incoming.id))
            .catch((resumeError) => setError(`运行保持排队：${messageFrom(resumeError)}`));
        }
      }
    } catch (loadError) {
      setConnection("demo");
      setError(`无法加载项目 ${projectId}：${messageFrom(loadError)}。当前显示只读教学草案。`);
    }
  }, []);

  useEffect(() => { void loadProject(projectIdFromLocation()); }, [loadProject]);
  useEffect(() => { void refreshProfiles().catch(() => undefined); }, [refreshProfiles]);

  const beginProjectSave = (): boolean => {
    // React state does not update synchronously enough to protect two clicks in
    // the same turn. The ref is the authoritative single-flight boundary.
    if (projectSaveInFlight.current) return false;
    projectSaveInFlight.current = true;
    setBusy(true);
    setProjectSaving(true);
    setError("");
    return true;
  };

  const finishProjectSave = () => {
    projectSaveInFlight.current = false;
    setProjectSaving(false);
    setBusy(false);
  };

  const createProjectFrom = async (nextLocal: WorkspaceProject, initialStage?: ServerStageName) => {
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
    const hydrated = hydrateWorkspaceProject(nextLocal, created, created.stages);

    // POST returns the complete canonical aggregate. Hydrating it directly
    // avoids racing a post-create read against the user's next edit.
    setProject(hydrated);
    setRun(undefined);
    setTrace([]);
    setMediaTasks({});
    setConnection("connected");
    if (created.id) history.replaceState(null, "", `${location.pathname}?project=${encodeURIComponent(created.id)}`);
    // Clear the retry identity only after the canonical aggregate and URL have
    // both been installed. A malformed/partial response must remain retryable
    // with the same key, or a retry could create a duplicate project.
    creationKeyByBody.current.delete(body);
  };

  const commitProject = async (patch: Partial<WorkspaceProject>) => {
    if (!beginProjectSave()) return;
    const nextLocal = mergeProjectResponse(project, patch);
    try {
      if (!project.id) {
        await createProjectFrom(nextLocal);
      } else {
        const updated = await plotloomApi.patchProject(project.id, project.revision, nextLocal.brief);
        setProject(mergeProjectResponse(nextLocal, updated));
        await loadProject(project.id);
      }
    } catch (saveError) {
      setError(messageFrom(saveError));
      if (connection === "demo") setProject((current) => mergeProjectResponse(current, patch));
    } finally { finishProjectSave(); }
  };

  const commitStage = async <T,>(stage: ServerStageName, content: T) => {
    if (!beginProjectSave()) return;
    const key = stage === "story_bible" ? "storyBible" : stage === "story_graph" ? "storyGraph" : stage === "scene_beats" ? "sceneBeats" : "storyboard";
    const nextLocal = markDownstreamStale(workspaceWithStageDraft(project, stage, content), stage);
    try {
      if (!project.id) {
        await createProjectFrom(nextLocal, stage);
        return;
      }
      const envelope = await plotloomApi.patchStage(project.id, stage, project.stageRevisions[stage], content);
      setProject((current) => markDownstreamStale({ ...current, [key]: content, stageRevisions: { ...current.stageRevisions, [stage]: envelope.revision } }, stage));
      await loadProject(project.id);
    } catch (stageError) {
      setError(messageFrom(stageError));
      if (connection === "demo") setProject((current) => markDownstreamStale(workspaceWithStageDraft(current, stage, content), stage));
    } finally { finishProjectSave(); }
  };

  async function pollRun(runId: string, projectIdToRefresh = project.id) {
    if (pollingRunIds.current.has(runId)) return;
    pollingRunIds.current.add(runId);
    try {
      let keepPolling = true;
      while (keepPolling) {
        const [nextRun, nextTrace] = await Promise.all([plotloomApi.getRun(runId), plotloomApi.getTrace(runId)]);
        const nextExecutionTrace = await plotloomApi.getRunExecutionTrace(runId).catch(() => undefined);
        setRun(nextRun); setTrace(traceEvents(nextTrace, nextExecutionTrace)); setExecutionTrace(nextExecutionTrace);
        keepPolling = nextRun.status === "queued" || nextRun.status === "running" || nextRun.status === "cancel_requested";
        if (keepPolling) await new Promise((resolve) => window.setTimeout(resolve, 1400));
        else if (nextRun.status === "quarantined") {
          setProject((current) => ({ ...current, quarantines: quarantineItemsFromTrace(nextTrace) }));
        }
      }
      if (projectIdToRefresh) await loadProject(projectIdToRefresh);
    } finally {
      pollingRunIds.current.delete(runId);
    }
  }

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
    setBusy(true); setError("");
    try {
      const saved = await prepareGenerationProfile();
      const started = await plotloomApi.startRun(
        project.id, stages, saved.profileId, saved.configuration.textAuthMode === "bearer",
      );
      setRun(started); setTrace([]); setExecutionTrace(undefined); void pollRun(started.id).catch((pollError) => setError(messageFrom(pollError)));
    }
    catch (runError) { setError(messageFrom(runError)); }
    finally { setBusy(false); }
  };

  const cancelRun = async () => {
    if (!run) return;
    try { setRun(await plotloomApi.cancelRun(run.id)); }
    catch (cancelError) { setError(messageFrom(cancelError)); }
  };

  const resumeRun = async () => {
    if (!run || (run.status !== "queued" && run.status !== "running")) return;
    const frozenProfileId = String(run.providerSnapshot.profileId || "default");
    const usesBearer = run.providerSnapshot.textAuthMode !== "none";
    try {
      const resumed = await plotloomApi.resumeRun(run.id, frozenProfileId, usesBearer);
      setRun(resumed);
      void pollRun(run.id).catch((pollError) => setError(messageFrom(pollError)));
    } catch (resumeError) { setError(messageFrom(resumeError)); }
  };

  const repair = async (item: QuarantineItem, instruction: string) => {
    if (!run) { setError("没有可修复的运行记录。"); return; }
    setBusy(true);
    try {
      const saved = await prepareGenerationProfile();
      const next = await plotloomApi.repairRun(
        run.id, item.stage, instruction, saved.profileId,
        saved.configuration.textAuthMode === "bearer",
      );
      setRun(next); setActivePage("trace"); void pollRun(next.id).catch((pollError) => setError(messageFrom(pollError)));
    }
    catch (repairError) { setError(messageFrom(repairError)); }
    finally { setBusy(false); }
  };

  const startMedia = async (shot: Shot, kind: MediaKind) => {
    if (!project.id) { setError("请先保存项目，再创建媒体任务。"); return; }
    const sourceTask = kind === "video" ? mediaTasks[`${shot.id}:image`] : undefined;
    const sourceUri = sourceTask?.status === "succeeded" ? sourceTask.outputUri : undefined;
    if (kind === "video" && !sourceUri) {
      setError("请先为这个镜头生成成功的关键帧，再创建视频任务。");
      return;
    }
    try {
      const task = await plotloomApi.startMediaTask(project.id, shot.id, kind, sourceUri ? { sourceUri } : undefined);
      const key = `${shot.id}:${kind}`;
      setMediaTasks((current) => ({ ...current, [key]: task }));
      let next = task;
      while (next.status === "queued" || next.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 1600));
        next = await plotloomApi.getMediaTask(next.id);
        setMediaTasks((current) => ({ ...current, [key]: next }));
      }
    } catch (mediaError) { setError(messageFrom(mediaError)); }
  };

  const rebuild = async (fromStage: ServerStageName) => {
    if (!project.id) { setError("请先保存项目，再重建下游阶段。"); return; }
    setBusy(true);
    try {
      const saved = await prepareGenerationProfile();
      const next = await plotloomApi.rebuild(
        project.id, fromStage, saved.profileId,
        saved.configuration.textAuthMode === "bearer",
      );
      setRun(next); setTrace([]); setExecutionTrace(undefined); setRebuildOpen(false); setActivePage("trace"); void pollRun(next.id).catch((pollError) => setError(messageFrom(pollError)));
    }
    catch (rebuildError) { setError(messageFrom(rebuildError)); }
    finally { setBusy(false); }
  };

  const saveProfile = async (draft: TextProviderProfileView, key: string): Promise<TextProviderProfileView> => {
    // `none` is a complete authentication mode, not an empty bearer key. Do
    // not retain an unnecessary credential or attach it to a later request.
    if (draft.configuration.textAuthMode === "bearer") providerSessionKeys.write(draft.profileId, key);
    else providerSessionKeys.clear(draft.profileId);
    const saved = await plotloomApi.updateTextProviderProfile(
      draft.profileId, draft.revision, draft.displayName, draft.configuration,
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
        : { profileId, displayName, configuration: { ...source.configuration, profileId, profileVersion: 0, profileHash: "", presetId: "custom" } });
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
      setError(probe.errorCode ? `连接测试失败：${probe.errorCode}` : `连接测试完成：${probe.model || saved.configuration.textModel} · ${probe.latencyMs}ms`);
    } catch (profileError) { setError(messageFrom(profileError)); }
    finally { setBusy(false); }
  };

  const staleCount = project.staleStages.length;
  const currentNav = navigation.find((item) => item.id === activePage)!;
  const running = run?.status === "queued" || run?.status === "running" || run?.status === "cancel_requested";
  const page = useMemo(() => {
    switch (activePage) {
      case "brief": return <BriefPage key={editorRevisionKey(project, "brief")} value={project.brief} saving={projectSaving} onSave={(brief) => commitProject({ brief })} />;
      case "bible": return <StoryBiblePage key={editorRevisionKey(project, "story_bible")} value={project.storyBible} stale={project.staleStages.includes("story_bible")} saving={projectSaving} onSave={(value: StoryBible) => commitStage("story_bible", value)} />;
      case "graph": return <GraphPage key={editorRevisionKey(project, "story_graph")} value={project.storyGraph} stale={project.staleStages.includes("story_graph")} saving={projectSaving} onSave={(value: StoryGraph) => commitStage("story_graph", value)} />;
      case "beats": return <SceneBeatsPage key={editorRevisionKey(project, "scene_beats")} value={project.sceneBeats} stale={project.staleStages.includes("scene_beats")} saving={projectSaving} onSave={(value: SceneBeatPlan) => commitStage("scene_beats", value)} />;
      case "storyboard": return <StoryboardPage key={editorRevisionKey(project, "storyboard")} graph={project.storyGraph} sceneBeats={project.sceneBeats} value={project.storyboard} stale={project.staleStages.includes("storyboard")} mediaTasks={mediaTasks} saving={projectSaving} onSave={(value: Storyboard) => commitStage("storyboard", value)} onMedia={startMedia} />;
      case "trace": return <TracePage run={run} trace={trace} executionTrace={executionTrace} running={Boolean(running)} onRun={startRun} onResume={resumeRun} onCancel={cancelRun} />;
      case "quarantine": return <QuarantinePage items={project.quarantines} repairing={busy} onRepair={repair} />;
    }
  // Commit callbacks intentionally read the current revision at invocation time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, project, busy, projectSaving, run, trace, executionTrace, mediaTasks, running]);

  return <div className="app-shell">
    <a className="skip-link" href="#workspace-main">跳到工作区</a>
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>叙织 · PIPELINE WORKBENCH</small></div></div>
      <div className="project-switcher"><span>当前项目</span><strong>{project.brief.title || "未命名项目"}</strong><small>{project.id || "unsaved teaching draft"} · r{project.revision}</small></div>
      <nav aria-label="工作台阶段">
        {navigation.map((item) => <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => setActivePage(item.id)}><span>{item.index}</span><div><strong>{item.label}</strong><small>{item.description}</small></div>{item.id === "quarantine" && project.quarantines.length > 0 && <i>{project.quarantines.length}</i>}</button>)}
      </nav>
      <div className="sidebar-footer"><Button variant="quiet" onClick={() => void openSettings()}>供应商与会话 Key</Button><small>API contract `/api/v2`</small></div>
    </aside>
    <div className="workspace-shell">
      <header className="topbar"><div><span>{currentNav.index}</span><strong>{currentNav.label}</strong></div><div className="topbar-actions"><Badge tone={connection === "connected" ? "ok" : connection === "loading" ? "accent" : "warning"}>{connection === "connected" ? "API 已连接" : connection === "loading" ? "正在连接" : "教学草案"}</Badge>{running && <Spinner label={trace.at(-1)?.stage ? stageLabels[trace.at(-1)!.stage] : "Pipeline"} />}{staleCount > 0 && <Button variant="quiet" onClick={() => setRebuildOpen(true)}>{staleCount} 个阶段待重建</Button>}</div></header>
      {error && <div className="global-error"><ErrorNotice message={error} /><button aria-label="关闭错误" onClick={() => setError("")}>×</button></div>}
      <main id="workspace-main">{page}</main>
    </div>
    {settingsOpen && <SettingsDialog profiles={profiles} selectedProfileId={selectedProfileId} draft={profileDraft} sessionKey={sessionKey} busy={busy} onDraft={(draft) => { setProfileDraft(draft); setProfileDirty(true); }} onSessionKey={setSessionKey} onSelect={selectProfile} onCreate={() => createProfile(false)} onCopy={() => createProfile(true)} onDelete={deleteProfile} onActivate={activateProfile} onProbe={testProfile} onClose={() => setSettingsOpen(false)} onSave={saveSettings} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={rebuild} />}
  </div>;
}

function SettingsDialog({ profiles, selectedProfileId, draft, sessionKey, busy, onDraft, onSessionKey, onSelect, onCreate, onCopy, onDelete, onActivate, onProbe, onClose, onSave }: { profiles: TextProviderProfilesResponse; selectedProfileId: string; draft: TextProviderProfileView; sessionKey: string; busy: boolean; onDraft: (draft: TextProviderProfileView) => void; onSessionKey: (key: string) => void; onSelect: (profileId: string) => Promise<void>; onCreate: () => Promise<void>; onCopy: () => Promise<void>; onDelete: () => Promise<void>; onActivate: () => Promise<void>; onProbe: () => Promise<void>; onClose: () => void; onSave: () => Promise<void> }) {
  const configuration = draft.configuration;
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
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card"><header><div><span>Text provider profile · {draft.profileId} r{draft.revision}</span><h2 id="settings-title">供应商 Profile 与会话 Key</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice"><strong>Key 不进入项目</strong><span>每个 Profile 的 Key 仅写入当前标签页 sessionStorage；保存、测试和生成请求都不会将它写入 JSON。</span></div><label><span>活动 Profile</span><select value={selectedProfileId} disabled={busy} onChange={(event) => void onSelect(event.target.value)}>{profiles.profiles.map((profile) => <option key={profile.profileId} value={profile.profileId}>{profile.displayName} · {profile.profileId}{profile.profileId === profiles.activeProfileId ? " · active" : ""}</option>)}</select></label><div className="profile-actions"><Button disabled={busy} onClick={() => void onCreate()}>新建</Button><Button disabled={busy} onClick={() => void onCopy()}>复制</Button><Button disabled={busy || draft.profileId === profiles.activeProfileId} variant="danger" onClick={() => void onDelete()}>删除</Button><Button disabled={busy || draft.profileId === profiles.activeProfileId} onClick={() => void onActivate()}>设为活动</Button></div><label><span>显示名称</span><input value={draft.displayName} onChange={(event) => onDraft({ ...draft, displayName: event.target.value })} /></label><label><span>执行预设</span><select value={configuration.presetId} onChange={(event) => event.target.value === "custom" ? update({ presetId: "custom" }) : applyPreset(event.target.value as Exclude<TextProviderPresetId, "custom">)}><option value="compatible_v1">兼容模式</option><option value="quality_reasoning_v1">高质量推理</option><option value="final_only_v1">仅最终答案</option><option value="custom">高级自定义</option></select></label>{field("textProvider", "文本供应商")}{field("textBaseUrl", "文本 API 根地址")}{field("textModel", "文本模型")}<label><span>文本认证</span><select value={configuration.textAuthMode} onChange={(event) => update({ textAuthMode: event.target.value as "none" | "bearer" })}><option value="none">none（不发送 Authorization）</option><option value="bearer">bearer</option></select></label><div className="profile-capabilities">{capability("chatCompletions", "支持 Chat Completions")}{capability("jsonObject", "支持 JSON object")}{capability("jsonSchema", "支持 JSON schema")}{capability("chatTemplateKwargs", "支持 Chat Template 参数")}</div><details><summary>高级设置</summary><div className="advanced-settings">{numberField("textContextWindowTokens", "文本上下文 token")}{numberField("textMaxOutputTokens", "文本最大输出 token")}{numberField("textTemperature", "文本 temperature")}{numberField("textMaxConcurrency", "文本并发")}{numberField("textConnectTimeoutSeconds", "文本连接超时（秒）")}{numberField("textAttemptTimeoutSeconds", "文本尝试超时（秒）")}{numberField("maxSemanticCorrections", "语义修正次数")}{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map(stageNumberField)}<label><span>请求扩展</span><select value={configuration.requestExtension} onChange={(event) => update({ requestExtension: event.target.value as TextProviderProfileConfiguration["requestExtension"], presetId: "custom" })}><option value="none">none</option><option value="chat_template_kwargs">chat_template_kwargs</option></select></label><label><span>推理模式</span><select value={configuration.reasoningMode} onChange={(event) => update({ reasoningMode: event.target.value as TextProviderProfileConfiguration["reasoningMode"], presetId: "custom" })}><option value="provider_default">provider_default</option><option value="enabled">enabled</option><option value="disabled">disabled</option></select></label><label><span>允许 JSON Fence</span><input type="checkbox" checked={configuration.extractionPolicy.allowJsonFence} onChange={(event) => update({ extractionPolicy: { ...configuration.extractionPolicy, allowJsonFence: event.target.checked }, presetId: "custom" })} /></label><label><span>允许开头 Think Block</span><input type="checkbox" checked={configuration.extractionPolicy.allowLeadingThinkBlock} onChange={(event) => update({ extractionPolicy: { ...configuration.extractionPolicy, allowLeadingThinkBlock: event.target.checked }, presetId: "custom" })} /></label></div></details>{configuration.textAuthMode === "bearer" ? <label><span>此 Profile 的临时 API Key</span><input type="password" autoComplete="off" value={sessionKey} placeholder={draft.serverKeyAvailable ? "留空使用服务器密钥" : "当前标签页的临时密钥"} onChange={(event) => onSessionKey(event.target.value)} /><small>{keyHint}</small></label> : <div className="notice"><strong>此 Profile 不需要 API Key</strong><span>authMode 为 none；保存后会清除此 Profile 的临时 key，测试和生成也不会发送它。</span></div>}</div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button disabled={busy} onClick={() => void onProbe()}>{busy ? "正在处理…" : "测试连接"}</Button><Button variant="primary" disabled={busy} onClick={() => void onSave()}>{busy ? "正在保存…" : "保存设置"}</Button></footer></section></div>;
}

function RebuildDialog({ staleStages, busy, onClose, onRebuild }: { staleStages: ServerStageName[]; busy: boolean; onClose: () => void; onRebuild: (stage: ServerStageName) => Promise<void> }) {
  const [stage, setStage] = useState<ServerStageName>(staleStages[0] || "story_bible");
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rebuild-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card compact"><header><div><span>Dependency-aware rebuild</span><h2 id="rebuild-title">重建过期阶段</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice warning"><strong>现有内容不会静默覆盖</strong><span>服务器从选择的阶段创建可追踪运行；验证失败的输出进入隔离区。</span></div><label><span>从哪个阶段开始</span><select value={stage} onChange={(event) => setStage(event.target.value as ServerStageName)}>{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((item) => <option key={item} value={item}>{stageLabels[item]}{staleStages.includes(item) ? " · 待重建" : ""}</option>)}</select></label></div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button variant="primary" disabled={busy} onClick={() => void onRebuild(stage)}>创建重建运行</Button></footer></section></div>;
}
