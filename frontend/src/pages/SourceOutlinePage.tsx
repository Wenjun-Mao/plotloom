import { useEffect, useRef, useState } from "react";
import { ApiError, plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProjectBrief, SourceMaterial, SourceOutlineReviewState, StoryGraph } from "../types";
import { SectionMapPanel } from "./SectionMapPanel";
import { OutlineAssignment } from "./OutlineAssignment";
import { OutlineReport } from "./OutlineReport";
import { ArtPanel } from "./ArtPanel";
import { ScriptPanel } from "./ScriptPanel";
import { StoryboardReviewPanel } from "./StoryboardReviewPanel";
import { deriveRoutes } from "../model";
import { sourceWorkflowTarget } from "../app/workspace/sourceWorkflowNavigation";

const blankSource: SourceMaterial = {
  kind: "synopsis",
  title: "",
  text: "",
  attribution: null,
  rightsDeclaration: null,
  adaptationIntent: "",
  inventedAdditions: null,
};

function sourceDraftFromBrief(brief: Pick<ProjectBrief, "title" | "synopsis">): SourceMaterial {
  return { ...blankSource, title: brief.title, text: brief.synopsis };
}

function sourceMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 409) return `当前版本已变化：${error.message}。请刷新后再决定。`;
  return error instanceof Error ? error.message : "来源与大纲操作失败。";
}

export function SourceOutlinePage({ projectId, briefSeed, readOnly, navigationTarget = "", onOpenShot }: { projectId: string; briefSeed: Pick<ProjectBrief, "title" | "synopsis">; readOnly: boolean; navigationTarget?: string; onOpenShot?: (shotId: string) => void }) {
  const [state, setState] = useState<SourceOutlineReviewState>();
  const [draft, setDraft] = useState<SourceMaterial>(blankSource);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [graph, setGraph] = useState<{ payload: StoryGraph; revision: number }>();
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const draftDirty = useRef(false);
  const activeProject = useRef({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  const ownsProject = (session: { projectId: string; epoch: number }) => activeProject.current === session;
  const focusedTarget = sourceWorkflowTarget(navigationTarget) || "source";

  const load = async (session = activeProject.current) => {
    setError("");
    try {
      const next = await plotloomApi.getSourceOutline(session.projectId);
      if (!ownsProject(session)) return;
      setState(next);
      const stages = await plotloomApi.getStages(session.projectId);
      if (!ownsProject(session)) return;
      const graphStage = stages.stages.find((stage) => stage.head.stage === "story_graph");
      setGraph(graphStage?.payload ? { payload: graphStage.payload as StoryGraph, revision: graphStage.head.revision } : undefined);
      // React Strict Mode can issue a second initial read after the author
      // begins typing. A late read must not silently erase unsaved source text.
      if (!draftDirty.current) {
        setDraft(next.source?.material || sourceDraftFromBrief(briefSeed));
        draftDirty.current = false;
      }
      setLoadedProjectId(session.projectId);
    } catch (loadError) { if (ownsProject(session)) setError(sourceMessage(loadError)); }
  };

  useEffect(() => {
    const session = activeProject.current;
    draftDirty.current = false;
    setState(undefined); setGraph(undefined); setLoadedProjectId(""); setError(""); setBusy(false); setDraft(blankSource);
    void load(session);
    return () => { if (ownsProject(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 }; };
  }, [projectId]); // The project route owns refreshes.

  const updateDraft = (next: SourceMaterial) => {
    draftDirty.current = true;
    setDraft(next);
  };

  const mutate = async (operation: () => Promise<SourceOutlineReviewState>, savedSource = false) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    try {
      const next = await operation();
      if (!ownsProject(session)) return;
      setState(next);
      if (savedSource) { setDraft(next.source?.material || sourceDraftFromBrief(briefSeed)); draftDirty.current = false; }
      const stages = await plotloomApi.getStages(session.projectId);
      if (!ownsProject(session)) return;
      const graphStage = stages.stages.find((stage) => stage.head.stage === "story_graph");
      setGraph(graphStage?.payload ? { payload: graphStage.payload as StoryGraph, revision: graphStage.head.revision } : undefined);
    } catch (mutationError) { if (ownsProject(session)) setError(sourceMessage(mutationError)); }
    finally { if (ownsProject(session)) setBusy(false); }
  };

  const candidate = state?.candidate;
  const accepted = state?.acceptedOutline;
  const canSave = !readOnly && !busy && Boolean(draft.title.trim() && draft.text.trim() && draft.adaptationIntent.trim());

  return <section id="source" className="page source-outline-page" data-project-id={loadedProjectId || projectId}>
    <section className="source-workflow-source" hidden={focusedTarget !== "source"} aria-labelledby="source-workflow-heading">
      <header className="page-header"><div><h1 id="source-workflow-heading">来源与大纲</h1><p>填写故事来源，审阅大纲，并确定分支路线。</p></div><Button variant="quiet" disabled={busy} onClick={() => void load()}>刷新</Button></header>
      {error && <ErrorNotice message={error} />}
      {!state ? <Spinner /> : <div className="source-outline-grid">
      <article className="panel source-outline-source" data-testid="source-outline-source">
        <header><span>已确认的改编内容</span><strong>{state.source ? `改编内容 r${state.source.revision}` : "尚未保存故事内容"}</strong></header>
        <label>来源类型<select disabled={readOnly || busy} value={draft.kind} onChange={(event) => updateDraft({ ...draft, kind: event.target.value as SourceMaterial["kind"] })}><option value="synopsis">梗概（发展为来源故事）</option><option value="imported_text">导入文字 / treatment</option><option value="existing_work">既有作品改编</option></select></label>
        <label>标题<input disabled={readOnly || busy} value={draft.title} onChange={(event) => updateDraft({ ...draft, title: event.target.value })} /></label>
        <label>故事内容<textarea disabled={readOnly || busy} value={draft.text} onChange={(event) => updateDraft({ ...draft, text: event.target.value })} rows={10} /></label>
        <label>改编意图<textarea disabled={readOnly || busy} value={draft.adaptationIntent} onChange={(event) => updateDraft({ ...draft, adaptationIntent: event.target.value })} rows={3} /></label>
        <label>允许的原创补充（可选）<textarea disabled={readOnly || busy} value={draft.inventedAdditions || ""} onChange={(event) => updateDraft({ ...draft, inventedAdditions: event.target.value || null })} rows={3} /></label>
        <Button variant="primary" disabled={!canSave} onClick={() => void mutate(() => plotloomApi.saveSourceMaterial(projectId, state.source?.revision || 0, draft), true)}>{busy ? "正在保存…" : "确认改编内容"}</Button>
        <p>将以这些内容和创作方向为依据，生成大纲。本次确认不会启动生成。</p>
      </article>

      <article className="panel source-outline-candidate" data-testid="source-outline-candidate">
        <header><span>大纲候选</span><strong>{candidate ? `${candidate.status === "ready" ? "待审阅" : candidate.status === "accepted" ? "已确认" : candidate.status === "cancelled" ? "已取消" : "任务已准备"} · ${candidate.jobId.slice(0, 11)}` : "尚无候选"}</strong></header>
        <p>候选只能来自当前已确认的改编内容和大纲版本；它不会自动替换已确认内容。</p>
        {!candidate && <Button variant="primary" disabled={readOnly || busy || !state.source} onClick={() => {
          setBusy(true); setError("");
          const session = activeProject.current;
          void plotloomApi.prepareOutlineCandidate(projectId).then(() => {
            if (ownsProject(session)) return load(session);
          }).catch((prepareError) => { if (ownsProject(session)) setError(sourceMessage(prepareError)); }).finally(() => { if (ownsProject(session)) setBusy(false); });
        }}>{busy ? "正在准备…" : "准备大纲任务"}</Button>}
        {candidate && <>
          <small>冻结来源 r{candidate.sourceRevision} · 目标已接受大纲 r{candidate.expectedOutlineRevision}</small>
          {candidate.status === "prepared" && <Button disabled={readOnly || busy} onClick={() => {
            setBusy(true); setError("");
            const session = activeProject.current;
            void plotloomApi.refreshOutlineCandidate(projectId, candidate.jobId).then(() => {
              if (ownsProject(session)) return load(session);
            }).catch((refreshError) => { if (ownsProject(session)) setError(sourceMessage(refreshError)); }).finally(() => { if (ownsProject(session)) setBusy(false); });
          }}>{busy ? "正在检查…" : "检查任务结果"}</Button>}
          {(candidate.status === "prepared" || candidate.status === "ready") && <Button variant="danger" disabled={readOnly || busy} onClick={() => void mutate(() => plotloomApi.cancelOutlineCandidate(projectId, candidate.jobId))}>取消此任务</Button>}
          {candidate.status === "ready" && <><details><summary>查看上游 outline.json</summary><pre>{JSON.stringify(candidate.outline, null, 2)}</pre></details>{candidate.outline && <section className="source-outline-upstream-report" data-testid="source-outline-upstream-report"><p role="note">这是候选大纲，尚未经你确认。阅读不会接受或修改内容。</p><OutlineReport key={`${projectId}:${candidate.jobId}`} outline={candidate.outline} url={candidate.reportAvailable ? plotloomApi.outlineCandidateReportUrl(projectId, candidate.jobId) : undefined} /></section>}</>}
          {candidate.status === "ready" && state.source && <><Button variant="primary" disabled={readOnly || busy} onClick={() => void mutate(() => plotloomApi.acceptOutlineCandidate(projectId, { jobId: candidate.jobId, expectedSourceRevision: state.source!.revision, expectedOutlineRevision: accepted?.revision || 0 }))}>确认使用此大纲</Button><p>确认后，将以这份大纲继续设计分支和剧本；不会自动生成后续内容。</p></>}
        </>}
        {candidate?.status === "prepared" && <OutlineAssignment key={`${projectId}:${candidate.jobId}`} projectId={projectId} jobId={candidate.jobId} />}
      </article>

      <article className="panel source-outline-accepted" data-testid="source-outline-accepted">
        <header><span>已确认的大纲</span><strong>{accepted ? `已确认 r${accepted.revision}` : "尚未确认"}</strong></header>
        <p>当前状态：{state.outlineStatus === "accepted" ? "已确认" : state.outlineStatus === "reopened" ? "已重新打开，需新的候选" : state.outlineStatus === "candidate_ready" ? "待审阅" : "缺失"}</p>
        {accepted ? <><small>基于故事内容 r{accepted.sourceRevision} · 候选 {accepted.candidateJobId.slice(0, 11)}</small><details><summary>查看已确认的原始 outline.json</summary><pre>{JSON.stringify(accepted.outline, null, 2)}</pre></details><Button variant="quiet" disabled={readOnly || busy || state.outlineStatus === "reopened"} onClick={() => void mutate(() => plotloomApi.reopenOutline(projectId, accepted.revision))}>重新打开，不替换内容</Button></> : <p className="muted">确认会新建不可变的大纲 revision；此处绝不从候选静默同步。</p>}
      </article>

      <SectionMapPanel
        outline={accepted || null} accepted={state.acceptedSectionMap} status={state.sectionMapStatus}
        staleReasons={state.sectionMapStaleReasons} readOnly={readOnly} busy={busy}
        graphAdmission={state.graphAdmission}
        routes={state.graphAdmission?.status === "current" && graph?.revision === state.graphAdmission.graphRevision ? deriveRoutes(graph.payload) : []}
        onSave={(mapping) => {
          if (!state.source || !accepted) return;
          void mutate(() => plotloomApi.saveSectionMap(projectId, {
            expectedSectionMapRevision: state.acceptedSectionMap?.revision || 0,
            expectedSourceRevision: state.source!.revision,
            expectedOutlineRevision: accepted.revision,
            expectedOutlineContentHash: accepted.contentHash,
            mapping,
          }));
        }}
        onInstall={() => {
          const map = state.acceptedSectionMap;
          const source = state.source;
          const admission = state.graphAdmission;
          if (!source || !accepted || !map) return;
          void mutate(() => plotloomApi.installSectionMapGraph(projectId, {
            expectedSourceRevision: source.revision, expectedSourceContentHash: source.contentHash,
            expectedOutlineRevision: accepted.revision, expectedOutlineContentHash: accepted.contentHash,
            expectedSectionMapRevision: map.revision, expectedSectionMapContentHash: map.contentHash,
            expectedGraphRevision: admission?.graphRevision || 0,
          }));
        }}
      />
      </div>}
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "art"} aria-labelledby="art-workflow-heading">
      <header className="page-header"><div><h1 id="art-workflow-heading">美术参考</h1><p>审阅地点、道具及其可复用参考。</p></div></header>
      <ArtPanel projectId={projectId} readOnly={readOnly} />
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "script"} aria-labelledby="script-workflow-heading">
      <header className="page-header"><div><h1 id="script-workflow-heading">剧本</h1><p>审阅当前完整 pilot，或编辑允许修改的稳定章节。</p></div></header>
      <ScriptPanel projectId={projectId} readOnly={readOnly} />
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "storyboard-review"} aria-labelledby="storyboard-review-workflow-heading">
      <header className="page-header"><div><h1 id="storyboard-review-workflow-heading">分镜评审</h1><p>审阅与已接受剧本绑定的 storyboard 证据。</p></div></header>
      <StoryboardReviewPanel projectId={projectId} readOnly={readOnly} onOpenShot={(shotId) => {
        if (draftDirty.current) return false;
        onOpenShot?.(shotId);
        return true;
      }} />
    </section>
  </section>;
}
