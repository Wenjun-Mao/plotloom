import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, plotloomApi } from "../api";
import { Button, ErrorNotice, RequiredMark, Spinner } from "../components";
import { StageGuide } from "../components/StageGuide";
import type { ProjectBrief, SourceMaterial, SourceOutlineReviewState, StoryGraph } from "../types";
import { SectionMapPanel } from "./SectionMapPanel";
import { OutlineAssignment } from "./OutlineAssignment";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { OutlineReport } from "./OutlineReport";
import { ArtPanel } from "./ArtPanel";
import { ScriptPanel } from "./ScriptPanel";
import { StoryboardReviewPanel } from "./StoryboardReviewPanel";
import { deriveRoutes } from "../model";
import { sourceWorkflowTarget } from "../app/workspace/sourceWorkflowNavigation";
import { useReviewActivation } from "./useReviewActivation";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";

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

export function SourceOutlinePage({ projectId, briefSeed, readOnly: ownerReadOnly, navigationTarget = "", refreshToken, onOpenShot, onContinueToCharacters, onContinueToScript, onContinueToStoryboard }: { projectId: string; briefSeed: ProjectBrief; readOnly: boolean; navigationTarget?: string; refreshToken?: unknown; onOpenShot?: (shotId: string) => void; onContinueToCharacters?: () => void; onContinueToScript?: () => void; onContinueToStoryboard?: () => void }) {
  const [state, setState] = useState<SourceOutlineReviewState>();
  const [draft, setDraft] = useState<SourceMaterial>(blankSource);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [graph, setGraph] = useState<{ payload: StoryGraph; revision: number; contentHash: string | null }>();
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const draftDirty = useRef(false);
  const activeProject = useRef({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  const ownsProject = (session: { projectId: string; epoch: number }) => activeProject.current === session;
  const focusedTarget = sourceWorkflowTarget(navigationTarget) || "source";

  const load = useCallback(async (isCurrent: () => boolean) => {
    const session = activeProject.current;
    setError("");
    try {
      const next = await plotloomApi.getSourceOutline(session.projectId);
      if (!ownsProject(session) || !isCurrent()) return false;
      const stages = await plotloomApi.getStages(session.projectId);
      if (!ownsProject(session) || !isCurrent()) return false;
      setState(next);
      const graphStage = stages.stages.find((stage) => stage.head.stage === "story_graph");
      setGraph(graphStage?.payload ? { payload: graphStage.payload as StoryGraph, revision: graphStage.head.revision, contentHash: graphStage.head.contentHash } : undefined);
      // React Strict Mode can issue a second initial read after the author
      // begins typing. A late read must not silently erase unsaved source text.
      if (!draftDirty.current) {
        setDraft(next.source?.material || sourceDraftFromBrief(briefSeed));
        draftDirty.current = false;
      }
      setLoadedProjectId(session.projectId);
      return true;
    } catch (loadError) { if (ownsProject(session) && isCurrent()) setError(sourceMessage(loadError)); }
    return false;
  }, [projectId, briefSeed]);

  useEffect(() => {
    const session = activeProject.current;
    draftDirty.current = false;
    setState(undefined); setGraph(undefined); setLoadedProjectId(""); setError(""); setBusy(false); setDraft(blankSource);
    return () => { if (ownsProject(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 }; };
  }, [projectId]); // The project route owns refreshes.
  const { checking, failed, recheck } = useReviewActivation({ projectId, active: focusedTarget === "source", refreshToken, load });
  const ownerDisabled = ownerReadOnly || checking || failed;
  const reviewDraft = useReviewEditorDraft(projectId, "source", state ? `source:${state.source?.revision ?? 0}` : "", text => {
    const recovered = JSON.parse(text) as SourceMaterial;
    if (typeof recovered.text !== "string" || typeof recovered.title !== "string") throw new Error("来源草稿格式无效，请复制内容后重新填写。");
    draftDirty.current = true; setDraft(recovered);
  }, ownerDisabled || busy, () => { draftDirty.current = false; setDraft(state?.source?.material || sourceDraftFromBrief(briefSeed)); });
  const readOnly = ownerDisabled || reviewDraft.stale;

  const updateDraft = (next: SourceMaterial) => {
    draftDirty.current = true;
    setDraft(next);
    reviewDraft.changed(JSON.stringify(next));
  };

  const mutate = async (operation: () => Promise<SourceOutlineReviewState>, savedSource = false) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    try {
      const next = await operation();
      if (!ownsProject(session)) return false;
      setState(next);
      if (savedSource) { setDraft(next.source?.material || sourceDraftFromBrief(briefSeed)); draftDirty.current = false; await reviewDraft.clear(); }
      await recheck();
      return true;
    } catch (mutationError) { if (ownsProject(session)) setError(sourceMessage(mutationError)); return false; }
    finally { if (ownsProject(session)) setBusy(false); }
  };

  const candidate = state?.candidate;
  const accepted = state?.acceptedOutline;
  const needsAdaptationGoal = draft.kind !== "synopsis";
  const missingSource = !draft.title.trim() || !draft.text.trim();
  const missingGoal = needsAdaptationGoal && !draft.adaptationIntent.trim();
  const canSave = !readOnly && !busy && !missingSource && !missingGoal;
  const sourceHint = checking ? "正在读取当前版本。" : failed ? "读取失败，请先重试刷新。" : ownerReadOnly ? "项目当前只读。" : busy ? "正在处理，请稍候。" : missingSource ? "请填写标题和故事内容，再确认改编内容。" : missingGoal ? "请填写改编目标，说明如何将原作改编成互动短片。" : "确认只保存故事来源；生成大纲需要下方单独准备并发送任务。";

  return <section id="source" className="page source-outline-page" data-project-id={loadedProjectId || projectId}>
    {error && focusedTarget !== "source" && <ErrorNotice message={error} />}
    <section className="source-workflow-source" hidden={focusedTarget !== "source"} aria-labelledby="source-workflow-heading">
      <header className="page-header"><div><h1 id="source-workflow-heading">来源与大纲</h1><p>填写故事来源，审阅大纲，并确定分支路线。</p></div><Button variant="quiet" disabled={busy || checking} onClick={() => void recheck()}>刷新</Button></header>
      <StageGuide>{failed ? "无法读取当前进度，请先刷新重试；保留内容不代表版本已核实。" : checking || !state ? "正在读取故事来源和当前进度。" : state.outlineStatus === "reopened" ? "大纲已重新打开。请准备新候选并确认；保留的旧大纲不会自动替换。" : candidate?.status === "ready" ? "先阅读候选大纲，再确认使用；随后设置开场、选择和两个结局。" : candidate?.status === "prepared" ? "大纲任务已准备。发送给文字创作助手，结果返回后再审核。" : state.graphAdmission?.status === "current" ? "故事分支已应用。可在下方继续角色设定；此操作只切换页面，不会生成内容。" : accepted ? "大纲已确认。请在下方完善故事分支，保存后应用到故事路线。" : state.source ? "故事来源已确认。下一步准备大纲任务，再发送给文字创作助手。" : "先确认故事来源，再准备大纲任务。* 为必填项，确认内容不会自动启动生成。"}</StageGuide>
      {error && <ErrorNotice message={error} />}
      {!state ? <Spinner /> : <div className="source-outline-grid">
      <article className="panel source-outline-source" data-testid="source-outline-source">
        {reviewDraft.notice}
        <header><span>已确认的改编内容</span><strong>{state.source ? `改编内容 r${state.source.revision}` : "尚未保存故事内容"}</strong></header>
        <p className="required-legend">* 为必填项。原创故事可直接确认已带入的梗概，无需重写。</p>
        <label>来源类型<select disabled={readOnly || busy} value={draft.kind} onChange={(event) => updateDraft({ ...draft, kind: event.target.value as SourceMaterial["kind"] })}><option value="synopsis">原创故事梗概</option><option value="imported_text">导入故事文本</option><option value="existing_work">既有作品改编</option></select></label>
        <label><span>标题<RequiredMark /></span><input aria-required="true" disabled={readOnly || busy} value={draft.title} onChange={(event) => updateDraft({ ...draft, title: event.target.value })} /></label>
        <label><span>故事内容<RequiredMark /></span><textarea aria-required="true" disabled={readOnly || busy} value={draft.text} onChange={(event) => updateDraft({ ...draft, text: event.target.value })} rows={10} /></label>
        <p className="action-prerequisite">{needsAdaptationGoal ? "填写本次要改编的原作内容；下方说明要保留什么、如何调整。" : "已从项目简报带入故事梗概。可直接使用，也可按需补充细节。"}</p>
        <label><span>{needsAdaptationGoal ? "改编目标" : "补充创作要求（可选）"}{needsAdaptationGoal && <RequiredMark />}</span><textarea aria-required={needsAdaptationGoal ? "true" : undefined} placeholder={needsAdaptationGoal ? "例如：保留原作的核心冲突，改成一个观众选择和两个结局。" : "如有额外偏好可填写，例如不用旁白；没有可留空。"} disabled={readOnly || busy} value={draft.adaptationIntent} onChange={(event) => updateDraft({ ...draft, adaptationIntent: event.target.value })} rows={3} /></label>
        <p className="action-prerequisite">大纲任务会自动使用简报中已保存的语言、类型、视觉风格、画幅、目标时长和生产范围，无需在这里重复填写。</p>
        <label>允许的原创补充（可选）<textarea disabled={readOnly || busy} value={draft.inventedAdditions || ""} onChange={(event) => updateDraft({ ...draft, inventedAdditions: event.target.value || null })} rows={3} /></label>
        <Button variant="primary" busy={busy} aria-describedby="source-save-hint" disabled={!canSave} onClick={() => void mutate(() => plotloomApi.saveSourceMaterial(projectId, state.source?.revision || 0, draft), true)}>{busy ? "正在保存…" : "确认改编内容"}</Button>
        <p id="source-save-hint" className="action-prerequisite">{sourceHint}</p>
      </article>

      <article className="panel source-outline-candidate" data-testid="source-outline-candidate">
        <header><span>大纲候选</span><strong>{candidate ? `${candidate.status === "ready" ? "待审阅" : candidate.status === "accepted" ? "已确认" : candidate.status === "cancelled" ? "已取消" : "任务已准备"} · ${candidate.jobId.slice(0, 11)}` : "尚无候选"}</strong></header>
        <p>候选只能来自当前已确认的改编内容和大纲版本；它不会自动替换已确认内容。</p>
        {(!candidate || candidate.status === "cancelled") && <Button variant="primary" disabled={readOnly || busy || !state.source} onClick={() => {
          setBusy(true); setError("");
          const session = activeProject.current;
          void plotloomApi.prepareOutlineCandidate(projectId).then(() => {
            if (ownsProject(session)) return recheck();
          }).catch((prepareError) => { if (ownsProject(session)) setError(sourceMessage(prepareError)); }).finally(() => { if (ownsProject(session)) setBusy(false); });
        }}>{busy ? "正在准备…" : candidate?.status === "cancelled" ? "重新准备大纲任务" : "准备大纲任务"}</Button>}
        {candidate?.status === "cancelled" && <p>使用已确认的来源准备新任务；原任务记录保留，发送与确认仍需单独操作。取消不会解除助手占用。</p>}
        {candidate && <>
          <small>冻结来源 r{candidate.sourceRevision} · 目标已接受大纲 r{candidate.expectedOutlineRevision}</small>
          {candidate.status === "prepared" && <SpecialistTaskActions projectId={projectId} stage="outline" jobId={candidate.jobId} disabled={readOnly || busy} onDelivered={recheck} />}
          {(candidate.status === "prepared" || candidate.status === "ready") && <Button variant="danger" disabled={readOnly || busy} onClick={() => void mutate(() => plotloomApi.cancelOutlineCandidate(projectId, candidate.jobId))}>取消此任务</Button>}
          {candidate.status === "ready" && <><details><summary>查看上游 outline.json</summary><pre>{JSON.stringify(candidate.outline, null, 2)}</pre></details>{candidate.outline && <section className="source-outline-upstream-report" data-testid="source-outline-upstream-report"><p role="note">这是候选大纲，尚未经你确认。阅读不会接受或修改内容。</p><OutlineReport key={`${projectId}:${candidate.jobId}`} outline={candidate.outline} url={candidate.reportAvailable ? plotloomApi.outlineCandidateReportUrl(projectId, candidate.jobId) : undefined} /></section>}</>}
          {candidate.status === "ready" && state.source && <><Button variant="primary" disabled={readOnly || busy} onClick={() => void mutate(() => plotloomApi.acceptOutlineCandidate(projectId, { jobId: candidate.jobId, expectedSourceRevision: state.source!.revision, expectedOutlineRevision: accepted?.revision || 0 }))}>确认使用此大纲</Button><p>确认后，将以这份大纲继续设计分支和剧本；不会自动生成后续内容。</p></>}
        </>}
        {candidate?.status === "prepared" && <details><summary>查看任务说明（手动方式）</summary><OutlineAssignment key={`${projectId}:${candidate.jobId}`} projectId={projectId} jobId={candidate.jobId} /></details>}
      </article>

      <article className="panel source-outline-accepted" data-testid="source-outline-accepted">
        <header><span>已确认的大纲</span><strong>{accepted ? `已确认 r${accepted.revision}` : "尚未确认"}</strong></header>
        <p>当前状态：{state.outlineStatus === "accepted" ? "已确认" : state.outlineStatus === "reopened" ? "已重新打开，需新的候选" : state.outlineStatus === "candidate_ready" ? "待审阅" : "缺失"}</p>
        {accepted ? <><small>基于故事内容 r{accepted.sourceRevision} · 候选 {accepted.candidateJobId.slice(0, 11)}</small><details><summary>查看已确认的原始 outline.json</summary><pre>{JSON.stringify(accepted.outline, null, 2)}</pre></details><Button variant="quiet" disabled={readOnly || busy || state.outlineStatus === "reopened"} onClick={() => void mutate(() => plotloomApi.reopenOutline(projectId, accepted.revision))}>重新打开，不替换内容</Button></> : <p className="muted">确认会新建独立的大纲版本；此处绝不从候选静默同步。</p>}
      </article>

      <SectionMapPanel key={projectId} projectId={projectId}
        outline={accepted || null} accepted={state.acceptedSectionMap} status={state.sectionMapStatus}
        staleReasons={state.sectionMapStaleReasons} readOnly={readOnly} busy={busy}
        graphAdmission={state.graphAdmission}
        graphReady={Boolean(state.graphAdmission?.status === "current" && graph?.revision === state.graphAdmission.graphRevision && graph?.contentHash === state.graphAdmission.graphContentHash)}
        sourceDirty={draftDirty.current}
        routes={state.graphAdmission?.status === "current" && graph?.revision === state.graphAdmission.graphRevision && graph?.contentHash === state.graphAdmission.graphContentHash ? deriveRoutes(graph.payload) : []}
        onSave={(mapping) => {
          if (!state.source || !accepted) return;
          return mutate(() => plotloomApi.saveSectionMap(projectId, {
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
        onContinue={() => {
          if (draftDirty.current) { setError("故事内容有未保存修改。请先保存或放弃这些修改，再继续角色设定。"); return; }
          onContinueToCharacters?.();
        }}
      />
      </div>}
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "art"} aria-labelledby="art-workflow-heading">
      <header className="page-header"><div><h1 id="art-workflow-heading">美术参考</h1><p>审阅地点、道具及其可复用参考。</p></div></header>
      <ArtPanel projectId={projectId} readOnly={ownerReadOnly} active={focusedTarget === "art"} refreshToken={refreshToken} onContinue={onContinueToScript && (() => { if (draftDirty.current) { setError("故事内容有未保存修改，请先确认或放弃修改。"); return; } onContinueToScript(); })} />
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "script"} aria-labelledby="script-workflow-heading">
      <header className="page-header"><div><h1 id="script-workflow-heading">剧本</h1><p>审阅完整剧本，按需修改开场或结局章节。</p></div></header>
      <ScriptPanel projectId={projectId} readOnly={ownerReadOnly} active={focusedTarget === "script"} refreshToken={refreshToken} onContinue={onContinueToStoryboard && (() => { if (draftDirty.current) { setError("故事内容有未保存修改，请先确认或放弃修改。"); return; } onContinueToStoryboard(); })} />
    </section>
    <section className="source-workflow-focus" hidden={focusedTarget !== "storyboard-review"} aria-labelledby="storyboard-review-workflow-heading">
      <header className="page-header"><div><h1 id="storyboard-review-workflow-heading">分镜评审</h1><p>将已确认剧本拆成镜头，审阅后准备投产。</p></div></header>
      <StoryboardReviewPanel projectId={projectId} readOnly={ownerReadOnly} active={focusedTarget === "storyboard-review"} refreshToken={refreshToken} onOpenShot={(shotId) => {
        if (draftDirty.current) return false;
        onOpenShot?.(shotId);
        return true;
      }} />
    </section>
  </section>;
}
