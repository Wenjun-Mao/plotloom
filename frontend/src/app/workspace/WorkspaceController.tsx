import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SceneBeatPlan, StoryBible, StoryGraph, Storyboard } from "../../types";
import { plotloomApi } from "../../api";
import { providerSessionKeys } from "../../session-key";
import { discardDraftRecord, findProjectDrafts, hasDraft, type DraftScope } from "../../draft-registry";
import { stageLabels } from "../../model";
import { editorRevisionKey } from "../../workspace-state";
import { Badge, Button, ErrorNotice, Spinner } from "../../components";
import { BriefPage } from "../../pages/BriefPage";
import { StoryBiblePage } from "../../pages/StoryBiblePage";
import { GraphPage } from "../../pages/GraphPage";
import { SceneBeatsPage } from "../../pages/SceneBeatsPage";
import { StoryboardPage } from "../../pages/StoryboardPage";
import { TracePage } from "../../pages/TracePage";
import { QuarantinePage } from "../../pages/QuarantinePage";
import { DraftConflictDialog, DraftNavigationDialog, DraftRecoveryDialog, ProjectDirectoryDialog, RebuildDialog, SettingsDialog, UnsafeDraftDialog, WelcomeOnboarding, WorkspaceInspector } from "./WorkspaceViews";
import { useAuthoringDraftRecovery } from "./useAuthoringDraftRecovery";
import { useProjectAuthoringPersistence } from "./useProjectAuthoringPersistence";
import { useProjectDirectory } from "./useProjectDirectory";
import { useProjectInitialization } from "./useProjectInitialization";
import { useProjectLifecycle } from "./useProjectLifecycle";
import { createProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";
import { useRunCommands } from "./useRunCommands";
import { useRunSession } from "./useRunSession";
import { useTextProviderProfiles } from "./useTextProviderProfiles";
import { useWorkspaceNavigation } from "./useWorkspaceNavigation";
import { useWorkspaceProjectLoader } from "./useWorkspaceProjectLoader";
import { useWorkspaceSession } from "./useWorkspaceSession";
import { editableStages, messageFrom, navigation, stageForPage } from "./contracts";

/** Composes view wiring around independently owned workspace transitions. */
export default function WorkspaceController() {
  const session = useWorkspaceSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rebuildOpen, setRebuildOpen] = useState(false);
  const [durableDraftsEnabled, setDurableDraftsEnabled] = useState(false);
  const [durableMediaDraftsEnabled, setDurableMediaDraftsEnabled] = useState(false);
  const [explicitProjectCloseEnabled, setExplicitProjectCloseEnabled] = useState(false);
  const [portableSnapshotsEnabled, setPortableSnapshotsEnabled] = useState(false);
  const durableDraftsEnabledRef = useRef(false);
  const mediaDraftQuiescence = useRef(createProjectDraftQuiescence()).current;
  const profiles = useTextProviderProfiles(setBusy, setError, messageFrom);
  const directory = useProjectDirectory(messageFrom);
  const { pollRun, loadTraceEvidence } = useRunSession({ session, setError, describeError: messageFrom });
  const observeRun = useCallback((runId: string, projectId: string) => {
    void pollRun(runId, projectId).catch((requestError) => setError(messageFrom(requestError)));
  }, [pollRun]);
  const { loadProject } = useWorkspaceProjectLoader({
    session,
    durableDrafts: durableDraftsEnabledRef,
    profiles: { loaded: profiles.loaded, catalog: profiles.catalog },
    observeRun,
    reportMessage: setError,
  });
  const authoring = useProjectAuthoringPersistence({
    session,
    durableDraftsEnabled: durableDraftsEnabledRef,
    feedback: { setBusy, setError },
    draftQuiescence: mediaDraftQuiescence,
  });
  const recovery = useAuthoringDraftRecovery({
    session,
    durableEnabled: durableDraftsEnabled,
    currentDraft: authoring.currentDraft,
    restoredDraft: authoring.restoredDraft,
    setRestoredDraft: authoring.setRestoredDraft,
    draftConflict: authoring.draftConflict,
    setDraftConflict: authoring.setDraftConflict,
    scheduleAutosave: authoring.scheduleAuthoringDraftAutosave,
    setError,
    reloadDraftConflict: authoring.reloadDraftConflict,
    copyDraftConflict: authoring.copyDraftConflict,
    discardDraftConflict: authoring.discardDraftConflict,
  });
  const workspaceNavigation = useWorkspaceNavigation({
    session,
    drafts: {
      current: authoring.currentDraft,
      durableEnabled: durableDraftsEnabledRef,
      flush: authoring.flushAuthoringDraft,
      commitProject: async (patch) => { await authoring.commitProject(patch); },
      commitStage: authoring.commitStage,
      clearRecovery: () => recovery.setRecovery(undefined),
      clearConflict: () => authoring.setDraftConflict(undefined),
    },
    loadProject,
    pollRun,
    isProjectClosing: mediaDraftQuiescence.isClosing,
  });
  const initialization = useProjectInitialization({ session, clearDraftWorkflow: authoring.clearDraftWorkflow });
  const lifecycle = useProjectLifecycle({
    session,
    currentDraft: authoring.currentDraft,
    commitProject: async (patch) => { await authoring.commitProject(patch); },
    commitStage: authoring.commitStage,
    discardCurrentAuthoringDraft: authoring.discardCurrentAuthoringDraft,
    mediaDraftQuiescence,
    directory: { close: directory.closeDirectory, refresh: directory.refresh, setError: directory.setError },
    openProject: (projectId) => workspaceNavigation.requestNavigation({ project: projectId, stage: "brief" }),
    startBlank: initialization.startBlankProject,
    explicitProjectClose: explicitProjectCloseEnabled,
    portableSnapshots: portableSnapshotsEnabled,
    reportError: setError,
  });
  const commands = useRunCommands({
    session,
    profiles: {
      draft: profiles.profileDraft,
      sessionKey: profiles.sessionKey,
      loaded: profiles.loaded,
      refresh: profiles.refresh,
      save: profiles.save,
      ensureFrozenCredential: profiles.ensureFrozenCredential,
    },
    pollRun,
    openTrace: workspaceNavigation.openRunTrace,
    setBusy,
    setError,
    hasDraft: (scope) => scope ? hasDraft(session.project, scope) : false,
  });

  useEffect(() => {
    if (session.route.project) void loadProject(session.route.project);
    // Initial route loading is separate from user navigation/popstate ownership.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadProject]);
  useEffect(() => {
    void plotloomApi.getAuthoringDraftCapability()
      .then((capability) => {
        durableDraftsEnabledRef.current = capability.durableProjectDrafts === true;
        setDurableDraftsEnabled(durableDraftsEnabledRef.current);
        setDurableMediaDraftsEnabled(capability.durableMediaDrafts === true);
        setExplicitProjectCloseEnabled(capability.explicitProjectClose === true);
        setPortableSnapshotsEnabled(capability.portableSnapshots === true);
        if (!durableDraftsEnabledRef.current) {
          void profiles.refresh().catch(() => undefined);
        }
        if (durableDraftsEnabledRef.current && session.routeRef.current.project) {
          const epoch = session.refreshCurrentRoute();
          void loadProject(session.routeRef.current.project, epoch);
        }
      })
      .catch(() => {
        durableDraftsEnabledRef.current = false;
        setDurableDraftsEnabled(false);
        setDurableMediaDraftsEnabled(false);
        setExplicitProjectCloseEnabled(false);
        setPortableSnapshotsEnabled(false);
        void profiles.refresh().catch(() => undefined);
      });
  }, [loadProject, profiles.refresh, session.refreshCurrentRoute, session.routeRef]);
  useEffect(() => {
    if (session.activePage !== "trace" || !session.run?.id) return;
    void loadTraceEvidence(session.run.id, session.run.projectId);
  }, [loadTraceEvidence, session.activePage, session.run?.id, session.run?.projectId]);
  useEffect(() => {
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!authoring.currentDraft.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [authoring.currentDraft]);

  const saveSettings = async () => {
    setBusy(true);
    try { await profiles.saveCurrent(); profiles.setSettingsOpen(false); }
    catch (settingsError) { setError(messageFrom(settingsError)); }
    finally { setBusy(false); }
  };
  const startBlank = () => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    initialization.startBlankProject(); directory.closeDirectory();
  };
  const openSample = () => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    initialization.openSampleProject(); directory.closeDirectory();
  };
  const requestProjectRefresh = () => {
    if (session.project.id && mediaDraftQuiescence.isClosing(session.project.id)) return;
    if (!session.project.id) { setError("空白项目尚无可刷新的服务器版本。"); return; }
    workspaceNavigation.requestNavigation({
      project: session.project.id,
      stage: session.activePage,
      entity: session.routeEntity,
      run: session.activePage === "trace" ? session.run?.id || "" : "",
      history: "pop",
      forceReload: true,
    });
  };
  const discardUnsafeDraft = () => {
    const unsafeDraft = session.unsafeDraft;
    if (!unsafeDraft) return;
    discardDraftRecord(unsafeDraft.record);
    const remaining = findProjectDrafts(unsafeDraft.record.projectId)[0];
    session.setUnsafeDraft(remaining ? { record: remaining, reason: unsafeDraft.reason } : undefined);
    recovery.bumpEditorNonce();
    if (!remaining) workspaceNavigation.continueAfterUnsafeDraft();
  };

  const { project, activePage, routeEntity, run, progress: runProgress, review: storyboardReview, issues: validationIssues, trace, executionTrace, mediaTasks, stageHeads, connection } = session;
  const staleCount = project.staleStages.length;
  const currentNav = navigation.find((item) => item.id === activePage)!;
  const running = run?.status === "queued" || run?.status === "running" || run?.status === "cancel_requested";
  const frozenProfileId = run ? String(run.providerSnapshot.profileId || "default") : "";
  const frozenProfile = profiles.profiles.profiles.find((profile) => profile.profileId === frozenProfileId);
  const frozenProfileNeedsKey = Boolean(run && run.providerSnapshot.textAuthMode !== "none" && !frozenProfile?.serverKeyAvailable && !providerSessionKeys.read(frozenProfileId));
  const navigationProjectId = session.route.project || project.id || "";
  const playUrl = navigationProjectId
    ? `?${new URLSearchParams({ project: navigationProjectId, view: "play" }).toString()}`
    : "";
  const workspaceHydrating = connection === "loading"
    && Boolean(navigationProjectId)
    && (project.id !== navigationProjectId || (activePage === "trace" && session.runSelectionPending));
  const recoveredValue = <T,>(scope: DraftScope, canonical: T): T => authoring.restoredDraft?.scope === scope ? authoring.restoredDraft.payload as T : canonical;
  const projectClosing = Boolean(project.id && lifecycle.closingProjectId === project.id);
  const projectSnapshotting = Boolean(project.id && lifecycle.snapshottingProjectId === project.id);
  const projectReadOnly = projectClosing || projectSnapshotting || project.lifecycleStatus === "archived" || Boolean(project.archivedAt);
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
      case "brief": return <BriefPage key={`${editorRevisionKey(project, "brief")}:${recovery.editorNonce}`} value={recoveredValue("brief", project.brief)} bible={project.storyBible} graph={project.storyGraph} saving={authoring.projectSaving || projectReadOnly} proposalRunning={Boolean(running && run?.requestedStages.length === 2 && run.requestedStages[0] === "story_bible" && run.requestedStages[1] === "story_graph")} proposalReady={Boolean(stageHeads.story_bible?.status === "ready" && stageHeads.story_graph?.status === "ready" && !project.staleStages.includes("story_bible") && !project.staleStages.includes("story_graph"))} onSave={(brief) => authoring.commitProject({ brief })} onGenerateProposal={async (brief) => { const projectId = await authoring.commitProject({ brief }); if (projectId) await commands.startProposal(projectId); }} onDraftChange={(value) => authoring.rememberDraft("brief", value)} onReviewStage={(stage) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage })} onContinueToPlanning={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "beats" })} />;
      case "bible": return <StoryBiblePage key={`${editorRevisionKey(project, "story_bible")}:${recovery.editorNonce}`} projectId={project.id} storyBibleRevision={stageHeads.story_bible?.revision} value={recoveredValue("story_bible", project.storyBible)} stale={project.staleStages.includes("story_bible")} saving={authoring.projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ sceneBeats: project.sceneBeats, storyboard: project.storyboard }} issues={validationIssues.story_bible} onEntitySelect={workspaceNavigation.selectRouteEntity} onSave={(value: StoryBible) => authoring.commitStage("story_bible", value)} onDraftChange={(value) => authoring.rememberDraft("story_bible", value)} />;
      case "graph": return <GraphPage key={`${editorRevisionKey(project, "story_graph")}:${recovery.editorNonce}`} value={recoveredValue("story_graph", project.storyGraph)} stale={project.staleStages.includes("story_graph")} saving={authoring.projectSaving || projectReadOnly} entityId={routeEntity} sceneReferences={project.sceneBeats.scenes.map((scene) => ({ id: scene.id, storyNodeId: scene.storyNodeId, title: scene.title }))} issues={validationIssues.story_graph} onEntitySelect={workspaceNavigation.selectRouteEntity} onSave={(value: StoryGraph) => authoring.commitStage("story_graph", value)} onDraftChange={(value) => authoring.rememberDraft("story_graph", value)} />;
      case "beats": return <SceneBeatsPage key={`${editorRevisionKey(project, "scene_beats")}:${recovery.editorNonce}`} value={recoveredValue("scene_beats", project.sceneBeats)} stale={project.staleStages.includes("scene_beats")} saving={authoring.projectSaving || projectReadOnly} entityId={routeEntity} referenceContext={{ nodes: project.storyGraph.nodes, characters: project.storyBible.characters, locations: project.storyBible.locations, props: project.storyBible.props, storyboard: { shots: project.storyboard.shots.map(({ id, sceneId, cueIds }) => ({ id, sceneId, cueIds })), shotBeatLinks: project.storyboard.shotBeatLinks.map(({ shotId, beatId }) => ({ shotId, beatId })) } }} issues={validationIssues.scene_beats} onEntitySelect={workspaceNavigation.selectRouteEntity} onSave={(value: SceneBeatPlan) => authoring.commitStage("scene_beats", value)} onDraftChange={(value) => authoring.rememberDraft("scene_beats", value)} />;
      case "storyboard": return <StoryboardPage key={`${editorRevisionKey(project, "storyboard")}:${recovery.editorNonce}`} projectId={project.id} revision={stageHeads.storyboard?.revision} storyBibleRevision={stageHeads.story_bible?.revision} contentHash={stageHeads.storyboard?.contentHash} bible={project.storyBible} graph={project.storyGraph} sceneBeats={project.sceneBeats} value={recoveredValue("storyboard", project.storyboard)} stale={project.staleStages.includes("storyboard")} mediaTasks={mediaTasks} saving={authoring.projectSaving || projectReadOnly} entityId={routeEntity} issues={validationIssues.storyboard} review={storyboardReview} mediaDraftsEnabled={durableMediaDraftsEnabled} mediaDraftQuiescence={mediaDraftQuiescence} onEntitySelect={workspaceNavigation.selectRouteEntity} onNavigateIssue={(stage, entity) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage, entity })} onReviewChange={session.acceptStoryboardReview} onSave={(value: Storyboard) => authoring.commitStage("storyboard", value)} onDraftChange={(value) => authoring.rememberDraft("storyboard", value)} />;
      case "trace": return <TracePage run={run} progress={runProgress} trace={trace} executionTrace={executionTrace} running={Boolean(running)} onRun={commands.startRun} onResume={commands.resumeRun} onCancel={commands.cancelRun} />;
      case "quarantine": return <QuarantinePage items={project.quarantines} repairing={busy} onRepair={commands.repair} onRebuildStage={commands.rebuild} />;
    }
  // Commit callbacks intentionally read current canonical revisions at invocation time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, authoring, busy, executionTrace, mediaTasks, project, projectReadOnly, recovery, routeEntity, run, runProgress, running, storyboardReview, validationIssues, workspaceNavigation]);

  if (session.onboarding) return <>
    <WelcomeOnboarding onBlank={startBlank} onSample={openSample} onDirectory={directory.openDirectory} />
    {directory.open && <ProjectDirectoryDialog projects={directory.projects} showArchived={directory.showArchived} error={directory.error} loading={directory.loading} hasMore={Boolean(directory.nextCursor)} onLoadMore={directory.loadMore} onArchived={(next) => { directory.setShowArchived(next); void directory.refresh(next); }} onBlank={startBlank} onSample={openSample} onOpen={(item) => { if (item.operationalState === "closed") { void lifecycle.mutate(item, "open"); return; } directory.closeDirectory(); workspaceNavigation.requestNavigation({ project: item.id, stage: "brief" }); }} onAction={lifecycle.mutate} explicitProjectClose={explicitProjectCloseEnabled} onClose={directory.closeDirectory} />}
  </>;

  return <div className="app-shell">
    <a className="skip-link" href="#workspace-main">跳到工作区</a>
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>叙织 · PIPELINE WORKBENCH</small></div></div>
      <button className="project-switcher" disabled={projectClosing || projectSnapshotting} onClick={directory.openDirectory}><span>当前项目 · 切换</span><strong>{project.brief.title || "未命名项目"}</strong><small>{project.id || "unsaved teaching draft"} · r{project.revision}</small></button>
      <nav aria-label="工作台阶段">{navigation.map((item) => <button key={item.id} disabled={projectClosing || projectSnapshotting} className={activePage === item.id ? "active" : ""} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: item.id, run: item.id === "trace" ? run?.id || "" : "" })}><span>{item.index}</span><div><strong>{item.label}</strong><small>{item.description}</small></div>{item.id === "quarantine" && project.quarantines.length > 0 && <i>{project.quarantines.length}</i>}</button>)}</nav>
      <div className="sidebar-footer"><Button variant="quiet" onClick={() => void profiles.openSettings()}>供应商与会话 Key</Button><small>API contract `/api/v2`</small></div>
    </aside>
    <div className="workspace-shell">
      <header className="topbar"><div><span>{currentNav.index}</span><strong>{currentNav.label}</strong></div><div className="topbar-actions">{projectClosing ? <Badge tone="accent">正在关闭项目</Badge> : projectSnapshotting ? <Badge tone="accent">正在创建恢复快照</Badge> : projectReadOnly && <Badge tone="warning">归档只读</Badge>}{durableDraftsEnabled && <Badge tone={authoring.durableDraftStatus === "saved" ? "ok" : authoring.durableDraftStatus === "failed" || authoring.durableDraftStatus === "conflict" ? "danger" : authoring.durableDraftStatus === "saving" ? "accent" : "warning"}>草稿：{authoring.durableDraftStatus === "saving" ? "正在保存" : authoring.durableDraftStatus === "saved" ? "已保存" : authoring.durableDraftStatus === "failed" ? "保存失败" : authoring.durableDraftStatus === "conflict" ? "冲突" : "等待编辑"}</Badge>}<Badge tone={connection === "connected" ? "ok" : connection === "loading" ? "accent" : "warning"}>Plotloom 服务：{connection === "connected" ? "已连接" : connection === "loading" ? "连接中" : "未连接"}</Badge><Badge tone={profiles.profileDraft.readiness?.state === "available" ? "ok" : ["unreachable", "authentication_failed", "model_mismatch", "capability_mismatch"].includes(profiles.profileDraft.readiness?.state || "unverified") ? "danger" : "warning"}>文本后端：{profiles.profileDraft.readiness?.state || "unverified"} · {profiles.profileDraft.profileId} · {profiles.profileDraft.readiness?.reasonCode || "readiness.not_checked"}{profiles.profileDraft.readiness?.observedAt ? ` · ${new Date(profiles.profileDraft.readiness.observedAt).toLocaleString()}` : " · 未检测"}</Badge>{running && <Spinner label={runProgress?.failedStage ? stageLabels[runProgress.failedStage] : "Pipeline"} />}{playUrl && <a className="button quiet" href={playUrl}>播放故事</a>}<Button variant="quiet" disabled={!project.id || connection === "loading" || projectClosing || projectSnapshotting} onClick={requestProjectRefresh}>刷新服务器版本</Button>{portableSnapshotsEnabled && <Button variant="quiet" disabled={!project.id || projectReadOnly || connection === "loading"} onClick={() => void lifecycle.createSnapshot()}>{projectSnapshotting ? "正在创建恢复快照…" : "创建恢复快照"}</Button>}{staleCount > 0 && <Button variant="quiet" disabled={projectReadOnly} onClick={() => setRebuildOpen(true)}>{staleCount} 个阶段待重建</Button>}{lifecycle.latestSnapshot && lifecycle.latestSnapshot.projectId === project.id && <small title={lifecycle.latestSnapshot.location}>恢复快照已完成：{lifecycle.latestSnapshot.location}</small>}</div></header>
      {error && <div className="global-error"><ErrorNotice message={error} /><button aria-label="关闭错误" onClick={() => setError("")}>×</button></div>}
      <div className="workbench-grid">
        <aside className="context-panel"><span className="eyebrow">Context</span><strong>{project.brief.title || "新项目"}</strong><small>{project.lifecycleStatus === "archived" || project.archivedAt ? "归档快照 · 仅供审阅" : project.id ? `项目 ${project.id}` : navigationProjectId ? `加载项目 ${navigationProjectId}` : "空白项目；保存后建立规范项目"}</small><div className="context-stages">{navigation.slice(0, 5).map((item) => <button key={item.id} disabled={projectClosing || projectSnapshotting} className={activePage === item.id ? "active" : ""} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: item.id })}>{item.index} {item.label}</button>)}</div><div className="context-assets"><span className="eyebrow">Canon assets</span>{bibleAssets.map((asset) => <div key={asset.label}><strong>{asset.label} · {asset.items.length}</strong><small>{asset.items.length ? asset.items.slice(0, 3).map((item) => item.name).join("、") : "尚未定义"}{asset.items.length > 3 ? " …" : ""}</small></div>)}</div></aside>
        <main id="workspace-main">{workspaceHydrating ? <div className="workspace-hydrating" data-testid="workspace-hydrating" role="status"><Spinner label="正在加载项目" /><strong>正在加载项目…</strong><small>项目内容加载完成后才能编辑，当前导航选择会被保留。</small></div> : <fieldset className="editor-host" disabled={projectReadOnly} onBlurCapture={() => { const scope = stageForPage(activePage); if (scope) void authoring.flushAuthoringDraft(scope); }}>{page}</fieldset>}</main>
        <WorkspaceInspector currentLabel={currentNav.label} project={project} routeEntity={routeEntity} stageOverview={stageOverview} run={run} progress={runProgress} review={storyboardReview} readOnly={projectReadOnly} frozenProfileId={frozenProfileId} frozenProfileNeedsKey={frozenProfileNeedsKey} onAuthorizeProfile={() => void profiles.openFrozen(frozenProfileId)} onOpenTrace={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "trace", run: run?.id || "" })} onResume={commands.resumeRun} onCancel={commands.cancelRun} onRepair={commands.repair} onRebuild={(stage) => { setRebuildOpen(false); void commands.rebuild(stage); }} />
      </div>
    </div>
    {profiles.settingsOpen && <SettingsDialog profiles={profiles.profiles} selectedProfileId={profiles.selectedProfileId} draft={profiles.profileDraft} sessionKey={profiles.sessionKey} busy={busy} onDraft={(draft) => { profiles.setProfileDraft(draft); profiles.setProfileDirty(true); }} onSessionKey={profiles.setSessionKey} onSelect={profiles.select} onCreate={() => profiles.create(false)} onCopy={() => profiles.create(true)} onDelete={profiles.remove} onActivate={profiles.activate} onAvailability={profiles.setAvailability} onProbe={profiles.probe} onClose={() => profiles.setSettingsOpen(false)} onSave={saveSettings} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={commands.rebuild} />}
    {directory.open && <ProjectDirectoryDialog projects={directory.projects} showArchived={directory.showArchived} error={directory.error} loading={directory.loading} hasMore={Boolean(directory.nextCursor)} onLoadMore={directory.loadMore} onArchived={(next) => { directory.setShowArchived(next); void directory.refresh(next); }} onBlank={startBlank} onSample={openSample} onOpen={(item) => { if (item.operationalState === "closed") { void lifecycle.mutate(item, "open"); return; } directory.closeDirectory(); workspaceNavigation.requestNavigation({ project: item.id, stage: "brief" }); }} onAction={lifecycle.mutate} explicitProjectClose={explicitProjectCloseEnabled} onClose={directory.closeDirectory} />}
    {workspaceNavigation.pendingNavigation && !session.unsafeDraft && <DraftNavigationDialog onSave={() => void workspaceNavigation.resolvePendingNavigation("save")} onDiscard={() => void workspaceNavigation.resolvePendingNavigation("discard")} onCancel={() => void workspaceNavigation.resolvePendingNavigation("cancel")} />}
    {lifecycle.pendingArchive && <DraftNavigationDialog closing={lifecycle.pendingArchive.action === "close"} onSave={() => void lifecycle.resolvePendingArchive("save")} onDiscard={() => void lifecycle.resolvePendingArchive("discard")} onCancel={() => void lifecycle.resolvePendingArchive("cancel")} />}
    {recovery.recovery && <DraftRecoveryDialog source={recovery.recovery.source} onRestore={recovery.restore} onDiscard={recovery.discard} />}
    {authoring.draftConflict && <DraftConflictDialog serverReloaded={authoring.draftConflict.serverReloaded} busy={authoring.projectSaving} onReload={() => void recovery.reloadConflict()} onCopy={() => void recovery.copyConflict()} onDiscard={recovery.discardConflict} />}
    {session.unsafeDraft && <UnsafeDraftDialog reason={session.unsafeDraft.reason} onDiscard={discardUnsafeDraft} />}
  </div>;
}
