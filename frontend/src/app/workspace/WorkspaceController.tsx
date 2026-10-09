import { useCallback, useEffect, useMemo, useRef, useState, type SyntheticEvent } from "react";
import { formatUiTimestamp } from "../../ui-time";
import type { SceneBeatPlan, StoryBible, StoryGraph, Storyboard } from "../../types";
import { plotloomApi } from "../../api";
import { providerSessionKeys } from "../../session-key";
import { findProjectDrafts, hasDraft, type DraftScope } from "../../draft-registry";
import { stageLabels } from "../../model";
import { editorRevisionKey } from "../../workspace-state";
import { Badge, Button, ErrorNotice, Spinner } from "../../components";
import { BriefPage } from "../../pages/BriefPage";
import { StoryBiblePage } from "../../pages/StoryBiblePage";
import { ProfessionalGraphWorkbench } from "../../features/graph/ProfessionalGraphWorkbench";
import { CreatorWorkbench } from "../../features/graph/CreatorWorkbench";
import { GraphWorkbenchProvider } from "../../features/graph/GraphWorkbenchProvider";
import { SceneBeatsPage } from "../../pages/SceneBeatsPage";
import { StoryboardPage } from "../../pages/StoryboardPage";
import { TracePage } from "../../pages/TracePage";
import { QuarantinePage } from "../../pages/QuarantinePage";
import { SourceOutlinePage } from "../../pages/SourceOutlinePage";
import { CharactersPage } from "../../pages/CharactersPage";
import { SpecialistSettingsDialog } from "../../features/specialists/SpecialistSettingsDialog";
import { DraftConflictDialog, DraftNavigationDialog, DraftRecoveryDialog, ProjectDirectoryDialog, RebuildDialog, SettingsDialog, UnsafeDraftDialog, WelcomeOnboarding, WorkspaceInspector } from "./WorkspaceViews";
import { useAuthoringDraftRecovery } from "./useAuthoringDraftRecovery";
import { useProjectAuthoringPersistence } from "./useProjectAuthoringPersistence";
import { useProjectDirectory } from "./useProjectDirectory";
import { useProjectInitialization } from "./useProjectInitialization";
import { useProjectLifecycle } from "./useProjectLifecycle";
import { createProjectDraftQuiescence } from "../../features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../../features/authoring/reviewDraftStore";
import { ReviewDraftContext } from "../../features/authoring/ReviewDraftContext";
import { useRunCommands } from "./useRunCommands";
import { useRunSession } from "./useRunSession";
import { useTextProviderProfiles } from "./useTextProviderProfiles";
import { useWorkspaceNavigation } from "./useWorkspaceNavigation";
import { useWorkspaceProjectLoader } from "./useWorkspaceProjectLoader";
import { useWorkspaceSession } from "./useWorkspaceSession";
import { editableStages, messageFrom, navigation, stageForPage } from "./contracts";
import { CreatorWorkflowNavigation } from "./CreatorWorkflowNavigation";
import { sourceWorkflowLabel } from "./sourceWorkflowNavigation";
import { encodeStoryboardEntity } from "../../storyboard-editor";
import { ProjectLoadDetails, ProjectUnavailable } from "./ProjectUnavailable";
import { projectUnavailableCopy } from "./projectAvailability";

function revealOpenedStatus(event: SyntheticEvent<HTMLDetailsElement>) {
  // Expanded diagnostics belong to document flow; reveal their reading entrance
  // after opening releases the sticky toolbar, even when the panel is very tall.
  if (event.currentTarget.open) event.currentTarget.querySelector("summary")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

/** Composes view wiring around independently owned workspace transitions. */
export default function WorkspaceController() {
  const session = useWorkspaceSession();
  const [busy, setBusy] = useState(false);
  const [specialistsOpen, setSpecialistsOpen] = useState(false);
  const [error, setError] = useState("");
  const discardNoticeTarget = useRef<HTMLDivElement>(null);
  const [rebuildOpen, setRebuildOpen] = useState(false);
  const [durableDraftsEnabled, setDurableDraftsEnabled] = useState(false);
  const [durableMediaDraftsEnabled, setDurableMediaDraftsEnabled] = useState(false);
  const [explicitProjectCloseEnabled, setExplicitProjectCloseEnabled] = useState(false);
  const [portableSnapshotsEnabled, setPortableSnapshotsEnabled] = useState(false);
  const durableDraftsEnabledRef = useRef(false);
  const mediaDraftQuiescence = useRef(createProjectDraftQuiescence()).current;
  useEffect(() => {
    const project = session.project;
    if (project.id) mediaDraftQuiescence.setWriteAdmission(project.id,
      project.lifecycleStatus !== "archived" && !project.archivedAt);
  }, [mediaDraftQuiescence, session.project.id, session.project.lifecycleStatus, session.project.archivedAt]);
  const reviewDraftStore = useMemo(() => createReviewDraftStore(mediaDraftQuiescence, window.sessionStorage), [mediaDraftQuiescence]);
  const loadedDrafts = session.serverDrafts.current;
  useEffect(() => {
    const projectId = session.project.id;
    return () => { if (projectId) reviewDraftStore.leave(projectId); };
  }, [session.project.id, reviewDraftStore]);
  useEffect(() => {
    if (durableDraftsEnabled && session.project.id && session.connection === "connected") reviewDraftStore.hydrate(session.project.id, [...loadedDrafts.values()]);
  }, [durableDraftsEnabled, session.project.id, session.connection, loadedDrafts, reviewDraftStore]);
  const profiles = useTextProviderProfiles(setBusy, setError, messageFrom);
  const directory = useProjectDirectory(messageFrom);
  const { pollRun, loadTraceEvidence } = useRunSession({ session, setError, describeError: messageFrom });
  const observeRun = useCallback((runId: string, projectId: string) => {
    void pollRun(runId, projectId).catch((requestError) => setError(messageFrom(requestError)));
  }, [pollRun]);
  const { loadProject } = useWorkspaceProjectLoader({
    session,
    durableDrafts: durableDraftsEnabledRef,
    profiles: { loaded: profiles.loaded, catalog: profiles.catalog, refresh: profiles.refresh },
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
    reviewDraftStore,
    session,
    currentDraft: authoring.currentDraft,
    commitProject: async (patch) => { await authoring.commitProject(patch); },
    commitStage: authoring.commitStage,
    discardCurrentAuthoringDraft: authoring.discardCurrentAuthoringDraft,
    mediaDraftQuiescence,
    directory: { open: directory.openDirectory, close: directory.closeDirectory, refresh: directory.refresh, setError: directory.setError },
    openProject: (projectId) => workspaceNavigation.requestNavigation({ project: projectId, stage: "creator" }),
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
    if (!recovery.discardRetained(unsafeDraft.record)) return;
    const remaining = findProjectDrafts(unsafeDraft.record.projectId)[0];
    session.setUnsafeDraft(remaining ? { record: remaining, reason: unsafeDraft.reason } : undefined);
    if (!remaining) workspaceNavigation.continueAfterUnsafeDraft();
  };

  const { project, activePage, routeEntity, run, progress: runProgress, review: storyboardReview, issues: validationIssues, trace, executionTrace, mediaTasks, stageHeads, connection } = session;
  const staleCount = project.staleStages.length;
  const currentNav = navigation.find((item) => item.id === activePage)!;
  const currentNavLabel = activePage === "source" ? sourceWorkflowLabel(session.route.hash) || currentNav.label : currentNav.label;
  const secondaryNavigation = navigation.filter((item) => item.id !== "brief" && item.id !== "source" && item.id !== "characters" && item.id !== "creator");
  const running = run?.status === "queued" || run?.status === "running" || run?.status === "cancel_requested";
  const frozenProfileId = run ? String(run.providerSnapshot.profileId || "default") : "";
  const frozenProfile = profiles.profiles.profiles.find((profile) => profile.profileId === frozenProfileId);
  const frozenProfileNeedsKey = Boolean(run && runProgress?.actions.canResume && profiles.loaded.current && frozenProfile && run.providerSnapshot.textAuthMode !== "none" && !frozenProfile.serverKeyAvailable && !providerSessionKeys.read(frozenProfileId));
  const navigationProjectId = session.route.project || project.id || "";
  useEffect(() => {
    if (recovery.discardNotice?.projectId === navigationProjectId) discardNoticeTarget.current?.scrollIntoView({ block: "center", inline: "nearest" });
  }, [recovery.discardNotice, navigationProjectId]);
  const initialProjectUnavailable = connection === "error" && Boolean(session.route.project) && project.id !== session.route.project;
  const playUrl = navigationProjectId && !initialProjectUnavailable
    ? `?${new URLSearchParams({ project: navigationProjectId, view: "play" }).toString()}`
    : "";
  const workspaceHydrating = connection === "loading"
    && Boolean(navigationProjectId)
    && (project.id !== navigationProjectId || (activePage === "trace" && session.runSelectionPending));
  const unavailableLabel = projectUnavailableCopy[session.loadFailure?.projectId === navigationProjectId ? session.loadFailure.kind : "unavailable"].title;
  const recoveredValue = <T,>(scope: DraftScope, canonical: T): T => authoring.restoredDraft?.scope === scope ? authoring.restoredDraft.payload as T : canonical;
  const projectClosing = Boolean(project.id && lifecycle.closingProjectId === project.id);
  const projectTransitionLabel = lifecycle.deletingProjectId ? "正在删除项目" : "正在关闭项目";
  const projectSnapshotting = Boolean(project.id && lifecycle.snapshottingProjectId === project.id);
  const projectReadOnly = projectClosing || projectSnapshotting || project.lifecycleStatus === "archived" || Boolean(project.archivedAt);
  const toolbarHint = initialProjectUnavailable ? "项目内容尚未读入；请重新读取或打开项目目录。" : !project.id ? "保存项目后可刷新服务器版本或创建恢复快照。" : projectClosing ? `${projectTransitionLabel}，请稍候。` : projectSnapshotting ? "正在创建恢复快照，请稍候。" : connection === "loading" ? "正在读取服务器版本。" : projectReadOnly ? "归档项目只读，无法创建恢复快照。" : "";
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
      case "source": return project.id
        ? <SourceOutlinePage projectId={project.id} briefSeed={project.brief} readOnly={projectReadOnly} navigationTarget={session.route.hash} refreshToken={project} onProductionInstalled={async installedProjectId => {
          if (session.routeRef.current.project !== installedProjectId) return;
          session.markCanonicalRefreshRequired(installedProjectId);
          await loadProject(installedProjectId, session.refreshCurrentRoute());
          if (session.routeRef.current.project === installedProjectId && session.needsCanonicalRefresh(installedProjectId)) throw new Error("当前投产镜头尚未成功读入工作区");
        }} onOpenShot={(shotId) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "storyboard", entity: encodeStoryboardEntity({ kind: "shot", shotId }) })} onContinueToCharacters={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "characters" })} onContinueToScript={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source", hash: "script" })} onContinueToStoryboard={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source", hash: "storyboard-review" })} />
        : <section className="page"><p>请先保存项目，再添加来源和大纲候选。</p></section>;
      case "characters": return project.id
        ? <CharactersPage projectId={project.id} readOnly={projectReadOnly} onContinue={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source", hash: "art" })} />
        : <section className="page"><p>请先保存项目，再审核角色文字和外观参考。</p></section>;
      case "brief": return <BriefPage key={`${editorRevisionKey(project, "brief")}:${recovery.editorNonce}`} value={recoveredValue("brief", project.brief)} hasSavedProject={Boolean(project.id)} bible={project.storyBible} graph={project.storyGraph} saving={authoring.projectSaving} readOnly={projectReadOnly} proposalRunning={Boolean(running && run?.requestedStages.some((stage) => stage === "story_bible" || stage === "story_graph"))} proposalReady={Boolean(stageHeads.story_bible?.status === "ready" && stageHeads.story_graph?.status === "ready" && !project.staleStages.includes("story_bible") && !project.staleStages.includes("story_graph"))} storyboardRunning={Boolean(running && run?.requestedStages.some((stage) => stage === "scene_beats" || stage === "storyboard"))} onSave={(brief) => authoring.commitProject({ brief })} onSaveAndContinue={async (brief) => { const projectId = await authoring.commitProject({ brief }); if (projectId) workspaceNavigation.requestNavigation({ project: projectId, stage: "source", hash: "source" }); }} onGenerateProposal={async (brief) => { const projectId = await authoring.commitProject({ brief }); if (projectId) await commands.startProposal(projectId); }} onGenerateStoryboard={async () => { if (project.id) await commands.startStoryboard(project.id); }} onContinueToSource={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source", hash: "source" })} onDraftChange={(value) => authoring.rememberDraft("brief", value)} onReviewStage={(stage) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage })} onContinueToPlanning={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "beats" })} />;
      case "bible": return <StoryBiblePage key={`${editorRevisionKey(project, "story_bible")}:${recovery.editorNonce}`} value={recoveredValue("story_bible", project.storyBible)} stale={project.staleStages.includes("story_bible")} saving={authoring.projectSaving} entityId={routeEntity} referenceContext={{ sceneBeats: project.sceneBeats, storyboard: project.storyboard }} issues={validationIssues.story_bible} onEntitySelect={workspaceNavigation.selectRouteEntity} onSave={(value: StoryBible) => authoring.commitStage("story_bible", value)} onDraftChange={(value) => authoring.rememberDraft("story_bible", value)} />;
      case "graph": return <ProfessionalGraphWorkbench projectId={project.id || ""} canonical={project.storyGraph} readOnly={projectReadOnly} onOpenSource={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source" })} />;
      case "creator": return <CreatorWorkbench project={project} readOnly={projectReadOnly} onNavigate={(stage, hash) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage, hash })} onOpenShot={(shotId) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "storyboard", entity: encodeStoryboardEntity({ kind: "shot", shotId }) })} />;
      case "beats": return <SceneBeatsPage key={`${editorRevisionKey(project, "scene_beats")}:${recovery.editorNonce}`} value={recoveredValue("scene_beats", project.sceneBeats)} stale={project.staleStages.includes("scene_beats")} saving={authoring.projectSaving} entityId={routeEntity} referenceContext={{ nodes: project.storyGraph.nodes, characters: project.storyBible.characters, locations: project.storyBible.locations, props: project.storyBible.props, storyboard: { shots: project.storyboard.shots.map(({ id, sceneId, cueIds }) => ({ id, sceneId, cueIds })), shotBeatLinks: project.storyboard.shotBeatLinks.map(({ shotId, beatId }) => ({ shotId, beatId })) } }} issues={validationIssues.scene_beats} onEntitySelect={workspaceNavigation.selectRouteEntity} onSave={(value: SceneBeatPlan) => authoring.commitStage("scene_beats", value)} onDraftChange={(value) => authoring.rememberDraft("scene_beats", value)} />;
      case "storyboard": return <StoryboardPage key={`${editorRevisionKey(project, "storyboard")}:${recovery.editorNonce}`} projectId={project.id} lifecycleRevision={project.lifecycleRevision} lifecycleStatus={project.lifecycleStatus} revision={stageHeads.storyboard?.revision} contentHash={stageHeads.storyboard?.contentHash} bible={project.storyBible} graph={project.storyGraph} sceneBeats={project.sceneBeats} value={recoveredValue("storyboard", project.storyboard)} stale={project.staleStages.includes("storyboard")} mediaTasks={mediaTasks} saving={authoring.projectSaving} readOnly={projectReadOnly} entityId={routeEntity} issues={validationIssues.storyboard} review={storyboardReview} mediaDraftsEnabled={durableMediaDraftsEnabled} mediaDraftQuiescence={mediaDraftQuiescence} onEntitySelect={workspaceNavigation.selectRouteEntity} onNavigateIssue={(stage, entity) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage, entity })} onReturnToBridge={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "source", hash: "storyboard-review" })} onReviewChange={session.acceptStoryboardReview} onSave={(value: Storyboard) => authoring.commitStage("storyboard", value)} onDraftChange={(value) => authoring.rememberDraft("storyboard", value)} />;
      case "trace": return <TracePage run={run} progress={runProgress} trace={trace} executionTrace={executionTrace} running={Boolean(running)} onRun={commands.startRun} onResume={commands.resumeRun} onCancel={commands.cancelRun} />;
      case "quarantine": return <QuarantinePage items={project.quarantines} repairing={busy} onRepair={commands.repair} onRebuildStage={commands.rebuild} />;
    }
  // Commit callbacks intentionally read current canonical revisions at invocation time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, authoring, busy, executionTrace, mediaTasks, project, projectReadOnly, recovery, routeEntity, run, runProgress, running, storyboardReview, validationIssues, workspaceNavigation]);

  if (session.onboarding) return <>
    <WelcomeOnboarding onBlank={startBlank} onSample={openSample} onDirectory={directory.openDirectory} />
    {lifecycle.duplicateNotice && <div className="notice" role="status"><span>{lifecycle.duplicateNotice}</span><Button onClick={lifecycle.dismissDuplicateNotice}>知道了</Button></div>}
    {directory.open && <ProjectDirectoryDialog projects={directory.projects} currentProjectId={project.id} notice={lifecycle.closeNotice} busy={Boolean(lifecycle.closingProjectId || lifecycle.snapshottingProjectId)} showArchived={directory.showArchived} error={directory.error} loading={directory.loading} hasMore={Boolean(directory.nextCursor)} onLoadMore={directory.loadMore} onArchived={(next) => { directory.setShowArchived(next); void directory.refresh(next); }} onBlank={startBlank} onSample={openSample} onOpen={(item) => { if (item.operationalState === "closed") { void lifecycle.mutate(item, "open"); return; } directory.closeDirectory(); workspaceNavigation.requestNavigation({ project: item.id, stage: "creator" }); }} onAction={lifecycle.mutate} explicitProjectClose={explicitProjectCloseEnabled} onClose={directory.closeDirectory} />}
    {lifecycle.confirmation}
  </>;

  return <GraphWorkbenchProvider project={project} enabled={durableDraftsEnabled && connection === "connected"} readOnly={projectReadOnly}
    restoredPayload={authoring.restoredDraft?.scope === "story_graph" ? authoring.restoredDraft.payload : undefined}
    restoredNonce={recovery.editorNonce}
    serverDrafts={session.serverDrafts} remember={payload => authoring.rememberDraft("story_graph", payload)} flush={() => authoring.flushAuthoringDraft("story_graph")}
    revisionConflict={record => authoring.setDraftConflict({ scope: "story_graph", record, workspace: project, serverReloaded: false })}
    clearDraftWorkflow={authoring.clearDraftWorkflow} canonicalChanged={async () => { if (project.id) await loadProject(project.id, session.refreshCurrentRoute()); }}>
    <ReviewDraftContext.Provider value={{ store: reviewDraftStore, quiescence: mediaDraftQuiescence, projectId: project.id || "", revision: project.revision, enabled: durableDraftsEnabled }}><div className="app-shell">
    <a className="skip-link" href="#workspace-main">跳到工作区</a>
    <aside className="sidebar">
      <button type="button" className="brand brand-home" aria-label="返回首页" title="返回首页，不会关闭项目" disabled={projectClosing || projectSnapshotting || workspaceHydrating || authoring.projectSaving} onClick={() => workspaceNavigation.requestNavigation({ project: "", stage: "brief", home: true })}><span className="brand-mark" aria-hidden="true">PL</span><span className="brand-home-copy"><strong>Plotloom<span className="brand-home-label" aria-hidden="true">首页</span></strong><small>叙织 · PIPELINE WORKBENCH</small></span></button>
      <button className="project-switcher" disabled={projectClosing || projectSnapshotting} onClick={directory.openDirectory}><span>当前项目 · 切换</span><strong>{initialProjectUnavailable ? unavailableLabel : project.brief.title || "未命名项目"}</strong><small>{initialProjectUnavailable ? "当前链接的项目尚未读入" : project.id ? "项目版本与标识可在技术详情中查看" : "尚未保存的项目草稿"}</small></button>
      <div className="workbench-mode-switch" aria-label="工作台模式"><button aria-pressed={activePage === "creator"} disabled={workspaceHydrating || projectClosing || projectSnapshotting} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "creator" })}>创作工作台</button><button aria-pressed={activePage !== "creator"} disabled={workspaceHydrating || projectClosing || projectSnapshotting} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "graph" })}>专业工作台</button></div>
      <button className={`project-brief-navigation${activePage === "brief" ? " active" : ""}`} aria-current={activePage === "brief" ? "page" : undefined} disabled={projectClosing || projectSnapshotting || workspaceHydrating} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "brief" })}><strong>项目简报与创作设置</strong><small>当前项目的剧情结构、风格与分镜偏好</small></button>
      <CreatorWorkflowNavigation projectId={navigationProjectId} activePage={activePage} activeHash={session.route.hash} disabled={projectClosing || projectSnapshotting || workspaceHydrating} onNavigate={({ stage, hash }) => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage, hash })} />
      <details className="workspace-tools-navigation"><summary>编辑与工具</summary><nav aria-label="编辑与工具">{secondaryNavigation.map((item) => <button key={item.id} disabled={projectClosing || projectSnapshotting || workspaceHydrating} className={activePage === item.id ? "active" : ""} onClick={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: item.id, run: item.id === "trace" ? run?.id || "" : "" })}><strong>{item.label}</strong>{item.id === "quarantine" && project.quarantines.length > 0 && <i>{project.quarantines.length}</i>}</button>)}</nav></details>
      <div className="sidebar-footer"><Button variant="quiet" onClick={() => setSpecialistsOpen(true)}>生成助手设置</Button><Button variant="quiet" onClick={() => void profiles.openSettings()}>供应商与会话密钥</Button><small>设置不会写入项目</small></div>
    </aside>
    <div className="workspace-shell">
<header className="topbar"><div className="topbar-actions">{projectClosing ? <Badge tone="accent">{projectTransitionLabel}</Badge> : projectSnapshotting ? <Badge tone="accent">正在创建恢复快照</Badge> : projectReadOnly && <Badge tone="warning">归档只读</Badge>}{running && <Spinner label={runProgress?.failedStage ? stageLabels[runProgress.failedStage] : "Pipeline"} />}{explicitProjectCloseEnabled && <Button variant="quiet" disabled={!project.id || projectReadOnly || connection !== "connected" || busy} onClick={() => void lifecycle.saveAndCloseCurrent()}>保存并关闭项目</Button>}{playUrl && <a className="button quiet" href={playUrl}>播放故事</a>}<Button variant="quiet" disabled={!project.id || connection === "loading" || projectClosing || projectSnapshotting} onClick={requestProjectRefresh}>刷新服务器版本</Button>{portableSnapshotsEnabled && <Button variant="quiet" disabled={!project.id || projectReadOnly || connection === "loading"} onClick={() => void lifecycle.createSnapshot()}>{projectSnapshotting ? "正在创建恢复快照…" : "创建恢复快照"}</Button>}{staleCount > 0 && <Button variant="quiet" disabled={projectReadOnly} onClick={() => setRebuildOpen(true)}>{staleCount} 个阶段待重建</Button>}{toolbarHint && <span className="toolbar-prerequisite" role="note">{toolbarHint}</span>}<details className="topbar-technical-status" onToggle={revealOpenedStatus}><summary>服务状态</summary><div>{durableDraftsEnabled && <Badge tone={authoring.durableDraftStatus === "saved" ? "ok" : authoring.durableDraftStatus === "failed" || authoring.durableDraftStatus === "conflict" ? "danger" : authoring.durableDraftStatus === "saving" ? "accent" : "warning"}>草稿：{authoring.durableDraftStatus === "saving" ? "正在保存" : authoring.durableDraftStatus === "saved" ? "已保存" : authoring.durableDraftStatus === "failed" ? "保存失败" : authoring.durableDraftStatus === "conflict" ? "冲突" : "等待编辑"}</Badge>}<Badge tone={connection === "connected" ? "ok" : connection === "loading" ? "accent" : "warning"}>Plotloom 服务：{connection === "connected" ? "已连接" : connection === "loading" ? "连接中" : "未连接"}</Badge><Badge tone={profiles.profileDraft.readiness?.state === "available" ? "ok" : ["unreachable", "authentication_failed", "model_mismatch", "capability_mismatch"].includes(profiles.profileDraft.readiness?.state || "unverified") ? "danger" : "warning"}>文本后端：{profiles.profileDraft.readiness?.state || "unverified"} · {profiles.profileDraft.profileId} · {profiles.profileDraft.readiness?.reasonCode || "readiness.not_checked"}{profiles.profileDraft.readiness?.observedAt ? ` · ${formatUiTimestamp(profiles.profileDraft.readiness.observedAt)}` : " · 未检测"}</Badge>{lifecycle.latestSnapshot && lifecycle.latestSnapshot.projectId === project.id && <small title={lifecycle.latestSnapshot.location}>恢复快照已完成：{lifecycle.latestSnapshot.location}</small>}</div></details></div></header>
      {error && <div className="global-error"><ErrorNotice message={error} /><button aria-label="关闭错误" onClick={() => setError("")}>×</button></div>}
      {lifecycle.duplicateNotice && <div className="notice workspace-copy-notice" role="status"><span>{lifecycle.duplicateNotice}</span><Button onClick={lifecycle.dismissDuplicateNotice}>知道了</Button></div>}
      {recovery.discardNotice?.projectId === navigationProjectId && <div ref={discardNoticeTarget} className="notice workspace-copy-notice" role="status"><span>已丢弃本标签页选中的保留草稿。项目中已保存的草稿和已确认内容未删除。</span><Button onClick={recovery.dismissDiscardNotice}>知道了</Button></div>}
      <div className="workbench-grid">
        <main id="workspace-main">
          {!initialProjectUnavailable && session.loadFailure?.projectId === navigationProjectId && <ProjectLoadDetails projectId={navigationProjectId} failure={session.loadFailure} />}
          {!initialProjectUnavailable && <details className="workspace-technical-details">
            <summary>查看技术详情</summary>
            <div className="workspace-technical-grid">
              <section className="context-panel"><span className="eyebrow">项目上下文</span><strong>{project.brief.title || "新项目"}</strong><small>{project.lifecycleStatus === "archived" || project.archivedAt ? "归档快照 · 仅供审阅" : project.id ? `项目 ${project.id}` : navigationProjectId ? `加载项目 ${navigationProjectId}` : "空白项目；保存后建立规范项目"}</small><div className="context-assets"><span className="eyebrow">规范资产</span>{bibleAssets.map((asset) => <div key={asset.label}><strong>{asset.label} · {asset.items.length}</strong><small>{asset.items.length ? asset.items.slice(0, 3).map((item) => item.name).join("、") : "尚未定义"}{asset.items.length > 3 ? " …" : ""}</small></div>)}</div></section>
              <WorkspaceInspector currentLabel={currentNavLabel} project={project} routeEntity={routeEntity} stageOverview={stageOverview} run={run} progress={runProgress} review={storyboardReview} readOnly={projectReadOnly} frozenProfileId={frozenProfileId} frozenProfileNeedsKey={frozenProfileNeedsKey} onAuthorizeProfile={() => void profiles.openFrozen(frozenProfileId)} onOpenTrace={() => workspaceNavigation.requestNavigation({ project: navigationProjectId, stage: "trace", run: run?.id || "" })} onResume={commands.resumeRun} onCancel={commands.cancelRun} onRepair={commands.repair} onRebuild={(stage) => { setRebuildOpen(false); void commands.rebuild(stage); }} />
            </div>
          </details>}
          {workspaceHydrating ? <div className="workspace-hydrating" data-testid="workspace-hydrating" role="status"><Spinner label="正在加载项目" /><strong>正在加载项目…</strong><small>项目内容加载完成后才能编辑，当前导航选择会被保留。</small></div> : initialProjectUnavailable ? <ProjectUnavailable projectId={navigationProjectId} failure={session.loadFailure} onDirectory={directory.openDirectory} onRetry={() => { void loadProject(navigationProjectId, undefined, "read-only"); }} /> : <fieldset className="editor-host" disabled={Boolean(session.loadFailure) || connection === "loading" || connection === "error" || (projectReadOnly && activePage !== "storyboard")} onBlurCapture={() => { const scope = stageForPage(activePage); if (scope) void authoring.flushAuthoringDraft(scope); }}>{page}</fieldset>}
        </main>
      </div>
    </div>
    {profiles.settingsOpen && <SettingsDialog profiles={profiles.profiles} selectedProfileId={profiles.selectedProfileId} draft={profiles.profileDraft} sessionKey={profiles.sessionKey} busy={busy} onDraft={(draft) => { profiles.setProfileDraft(draft); profiles.setProfileDirty(true); }} onSessionKey={profiles.setSessionKey} onSelect={profiles.select} onCreate={() => profiles.create(false)} onCopy={() => profiles.create(true)} onDelete={profiles.remove} onActivate={profiles.activate} onAvailability={profiles.setAvailability} onProbe={profiles.probe} onClose={() => profiles.setSettingsOpen(false)} onSave={saveSettings} />}
    {specialistsOpen && <SpecialistSettingsDialog onClose={() => setSpecialistsOpen(false)} />}
    {rebuildOpen && <RebuildDialog staleStages={project.staleStages} busy={busy} onClose={() => setRebuildOpen(false)} onRebuild={commands.rebuild} />}
    {directory.open && <ProjectDirectoryDialog projects={directory.projects} currentProjectId={project.id} notice={lifecycle.closeNotice} busy={Boolean(lifecycle.closingProjectId || lifecycle.snapshottingProjectId)} showArchived={directory.showArchived} error={directory.error} loading={directory.loading} hasMore={Boolean(directory.nextCursor)} onLoadMore={directory.loadMore} onArchived={(next) => { directory.setShowArchived(next); void directory.refresh(next); }} onBlank={startBlank} onSample={openSample} onOpen={(item) => { if (item.operationalState === "closed") { void lifecycle.mutate(item, "open"); return; } directory.closeDirectory(); workspaceNavigation.requestNavigation({ project: item.id, stage: "creator" }); }} onAction={lifecycle.mutate} explicitProjectClose={explicitProjectCloseEnabled} onClose={directory.closeDirectory} />}
    {workspaceNavigation.pendingNavigation && !session.unsafeDraft && <DraftNavigationDialog intent="navigate" onSave={() => void workspaceNavigation.resolvePendingNavigation("save")} onDiscard={() => void workspaceNavigation.resolvePendingNavigation("discard")} onCancel={() => void workspaceNavigation.resolvePendingNavigation("cancel")} />}
    {lifecycle.pendingArchive && <DraftNavigationDialog intent={lifecycle.pendingArchive.action} onSave={() => void lifecycle.resolvePendingArchive("save")} onDiscard={() => void lifecycle.resolvePendingArchive("discard")} onCancel={() => void lifecycle.resolvePendingArchive("cancel")} />}
    {recovery.recovery && !session.unsafeDraft && <DraftRecoveryDialog source={recovery.recovery.source} busy={recovery.restoring} onRestore={() => void recovery.restore()} onDiscard={recovery.discard} />}
    {authoring.draftConflict && !session.unsafeDraft && <DraftConflictDialog graphRecovery={authoring.draftConflict.scope === "story_graph"} serverReloaded={authoring.draftConflict.serverReloaded} reloading={authoring.conflictReloading} busy={authoring.projectSaving} onReload={() => void recovery.reloadConflict()} onCopy={() => void recovery.copyConflict()} onDiscard={recovery.discardConflict} />}
    {session.unsafeDraft && !session.unsafeDraft.dismissed && <UnsafeDraftDialog reason={session.unsafeDraft.reason} records={findProjectDrafts(session.unsafeDraft.record.projectId)} busy={connection === "loading"} onDiscard={discardUnsafeDraft}
      onKeep={() => { session.setUnsafeDraft({ ...session.unsafeDraft!, dismissed: true }); workspaceNavigation.continueAfterUnsafeDraft(); }}
      onRetry={() => { void workspaceNavigation.resolvePendingNavigation("cancel"); void loadProject(session.unsafeDraft!.record.projectId); }} />}
    {session.unsafeDraft?.dismissed && <div className="notice"><span>草稿已保留，核实项目后才能恢复。</span><Button onClick={() => session.setUnsafeDraft({ ...session.unsafeDraft!, dismissed: false })}>查看保留草稿</Button></div>}
    {lifecycle.confirmation}
  </div></ReviewDraftContext.Provider></GraphWorkbenchProvider>;
}
