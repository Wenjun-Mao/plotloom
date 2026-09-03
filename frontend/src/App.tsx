import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MediaKind, MediaTask, PipelineRun, ProviderSettings, QuarantineItem, SceneBeatPlan, ServerStageName, Shot, StoryBible, StoryGraph, Storyboard, TraceEvent, WorkspaceProject } from "./types";
import { plotloomApi, ApiError } from "./api";
import { providerSessionKey } from "./session-key";
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
  const [providerSettings, setProviderSettings] = useState<ProviderSettings>(defaultProviderSettings);
  const [sessionKey, setSessionKey] = useState(providerSessionKey.read());
  const pollingRunIds = useRef(new Set<string>());
  const projectSaveInFlight = useRef(false);
  const creationKeyByBody = useRef(new Map<string, string>());

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
      const quarantines = latestTrace ? quarantineItemsFromTrace(latestTrace) : [];
      setProject((current) => ({ ...hydrateWorkspaceProject(current, incoming, stageResponse.stages), quarantines }));
      setRun(latestRun);
      setTrace(latestTrace ? traceEvents(latestTrace) : []);
      setMediaTasks(newestMediaTasksByShot(mediaResponse.tasks));
      setConnection("connected");
      setError("");
      if (latestRun && (latestRun.status === "queued" || latestRun.status === "running" || latestRun.status === "cancel_requested")) {
        void pollRun(latestRun.id, incoming.id).catch((pollError) => setError(messageFrom(pollError)));
      }
    } catch (loadError) {
      setConnection("demo");
      setError(`无法加载项目 ${projectId}：${messageFrom(loadError)}。当前显示只读教学草案。`);
    }
  }, []);

  useEffect(() => { void loadProject(projectIdFromLocation()); }, [loadProject]);

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
        setRun(nextRun); setTrace(traceEvents(nextTrace));
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

  const startRun = async (stages: ServerStageName[]) => {
    if (!project.id) { setError("请先保存项目，再启动生成流水线。"); return; }
    setBusy(true); setError("");
    try { const started = await plotloomApi.startRun(project.id, stages); setRun(started); setTrace([]); void pollRun(started.id).catch((pollError) => setError(messageFrom(pollError))); }
    catch (runError) { setError(messageFrom(runError)); }
    finally { setBusy(false); }
  };

  const cancelRun = async () => {
    if (!run) return;
    try { setRun(await plotloomApi.cancelRun(run.id)); }
    catch (cancelError) { setError(messageFrom(cancelError)); }
  };

  const repair = async (item: QuarantineItem, instruction: string) => {
    if (!run) { setError("没有可修复的运行记录。"); return; }
    setBusy(true);
    try { const next = await plotloomApi.repairRun(run.id, item.stage, instruction); setRun(next); setActivePage("trace"); void pollRun(next.id).catch((pollError) => setError(messageFrom(pollError))); }
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
    try { const next = await plotloomApi.rebuild(project.id, fromStage); setRun(next); setTrace([]); setRebuildOpen(false); setActivePage("trace"); void pollRun(next.id).catch((pollError) => setError(messageFrom(pollError))); }
    catch (rebuildError) { setError(messageFrom(rebuildError)); }
    finally { setBusy(false); }
  };

  const openSettings = async () => {
    setSettingsOpen(true);
    try { setProviderSettings(await plotloomApi.getProviderSettings()); } catch { /* Defaults remain editable offline. */ }
  };

  const saveSettings = async () => {
    setBusy(true);
    providerSessionKey.write(sessionKey);
    try { setProviderSettings(await plotloomApi.putProviderSettings(providerSettings)); setSettingsOpen(false); }
    catch (settingsError) { setError(messageFrom(settingsError)); }
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
      case "trace": return <TracePage run={run} trace={trace} running={Boolean(running)} onRun={startRun} onCancel={cancelRun} />;
      case "quarantine": return <QuarantinePage items={project.quarantines} repairing={busy} onRepair={repair} />;
    }
  // Commit callbacks intentionally read the current revision at invocation time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, project, busy, projectSaving, run, trace, mediaTasks, running]);

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
    {settingsOpen && <SettingsDialog settings={providerSettings} sessionKey={sessionKey} busy={busy} onSettings={setProviderSettings} onSessionKey={setSessionKey} onClose={() => setSettingsOpen(false)} onSave={saveSettings} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={rebuild} />}
  </div>;
}

function SettingsDialog({ settings, sessionKey, busy, onSettings, onSessionKey, onClose, onSave }: { settings: ProviderSettings; sessionKey: string; busy: boolean; onSettings: (settings: ProviderSettings) => void; onSessionKey: (key: string) => void; onClose: () => void; onSave: () => Promise<void> }) {
  const field = (key: keyof ProviderSettings, label: string) => <label><span>{label}</span><input value={String(settings[key] ?? "")} onChange={(event) => onSettings({ ...settings, [key]: event.target.value })} /></label>;
  const numberField = (key: keyof ProviderSettings, label: string) => <label><span>{label}</span><input type="number" value={Number(settings[key] ?? 0)} onChange={(event) => onSettings({ ...settings, [key]: Number(event.target.value) })} /></label>;
  const authMode = (key: "textAuthMode" | "imageAuthMode" | "videoAuthMode", label: string) => <label><span>{label}</span><select value={settings[key]} onChange={(event) => onSettings({ ...settings, [key]: event.target.value as "none" | "bearer" })}><option value="none">none（不发送 Authorization）</option><option value="bearer">bearer</option></select></label>;
  const capability = (key: "chatCompletions" | "jsonObject" | "jsonSchema", label: string) => <label><span>{label}</span><input type="checkbox" checked={settings.textCapabilities[key]} onChange={(event) => onSettings({ ...settings, textCapabilities: { ...settings.textCapabilities, [key]: event.target.checked } })} /></label>;
  const serverKeys = [
    settings.textKeyAvailable ? "文本" : "",
    settings.imageKeyAvailable ? "图像" : "",
    settings.videoKeyAvailable ? "视频" : "",
  ].filter(Boolean);
  const keyHint = serverKeys.length
    ? `服务器已配置${serverKeys.join("、")}密钥；留空即使用服务器密钥，填写则仅覆盖当前标签页。`
    : "服务器没有可用密钥；填写后仅在当前标签页会话中使用。";
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card"><header><div><span>Provider boundary · {settings.profileId} v{settings.profileVersion}</span><h2 id="settings-title">供应商与会话 Key</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice"><strong>Key 不进入项目</strong><span>仅写入当前标签页的 sessionStorage，并作为 `X-Plotloom-Session-API-Key` 请求头发送。HTTP 可用于本机、LAN 或 Tailnet 的已保存供应商根地址。</span></div>{field("textProvider", "文本供应商")}{field("textBaseUrl", "文本 API 根地址")}{field("textModel", "文本模型")}{authMode("textAuthMode", "文本认证")}{capability("chatCompletions", "支持 Chat Completions")}{capability("jsonObject", "支持 JSON object")}{capability("jsonSchema", "支持 JSON schema")}{numberField("textContextWindowTokens", "文本上下文 token")}{numberField("textMaxOutputTokens", "文本最大输出 token")}{numberField("textTemperature", "文本 temperature")}{numberField("textMaxConcurrency", "文本并发")}{numberField("textConnectTimeoutSeconds", "文本连接超时（秒）")}{numberField("textAttemptTimeoutSeconds", "文本尝试超时（秒）")}{field("imageProvider", "图像供应商")}{field("imageBaseUrl", "图像 API 根地址")}{field("imageModel", "图像模型")}{authMode("imageAuthMode", "图像认证")}{field("videoProvider", "视频供应商")}{field("videoBaseUrl", "视频 API 根地址")}{field("videoModel", "视频模型")}{authMode("videoAuthMode", "视频认证")}<label><span>临时 API Key</span><input type="password" autoComplete="off" value={sessionKey} placeholder={serverKeys.length ? "留空使用服务器密钥" : "当前标签页的临时密钥"} onChange={(event) => onSessionKey(event.target.value)} /><small>{keyHint}</small></label></div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button variant="primary" disabled={busy} onClick={() => void onSave()}>{busy ? "正在保存…" : "保存设置"}</Button></footer></section></div>;
}

function RebuildDialog({ staleStages, busy, onClose, onRebuild }: { staleStages: ServerStageName[]; busy: boolean; onClose: () => void; onRebuild: (stage: ServerStageName) => Promise<void> }) {
  const [stage, setStage] = useState<ServerStageName>(staleStages[0] || "story_bible");
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rebuild-title"><button className="modal-backdrop" aria-label="关闭" onClick={onClose} /><section className="modal-card compact"><header><div><span>Dependency-aware rebuild</span><h2 id="rebuild-title">重建过期阶段</h2></div><button aria-label="关闭" onClick={onClose}>×</button></header><div className="modal-body"><div className="notice warning"><strong>现有内容不会静默覆盖</strong><span>服务器从选择的阶段创建可追踪运行；验证失败的输出进入隔离区。</span></div><label><span>从哪个阶段开始</span><select value={stage} onChange={(event) => setStage(event.target.value as ServerStageName)}>{(["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((item) => <option key={item} value={item}>{stageLabels[item]}{staleStages.includes(item) ? " · 待重建" : ""}</option>)}</select></label></div><footer><Button variant="quiet" onClick={onClose}>取消</Button><Button variant="primary" disabled={busy} onClick={() => void onRebuild(stage)}>创建重建运行</Button></footer></section></div>;
}
