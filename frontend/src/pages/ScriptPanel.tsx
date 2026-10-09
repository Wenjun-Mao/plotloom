import { StaticReportReader } from "../components/StaticReportReader";
import { useCallback, useEffect, useRef, useState } from "react";
import { AcceptedEvidenceNotice } from "./AcceptedEvidenceNotice";
import { plotloomApi } from "../api";
import { Button, Spinner } from "../components";
import { ReviewContextErrorNotice, ReviewContextNotice, reviewContextFailure, reviewContextNextStep, type ReviewContextFailure } from "./ReviewContextNotice";
import type { AcceptedScriptRevision, ScriptCandidate, ScriptReviewState } from "../types";
import { ManualTaskAssignment } from "./ManualTaskAssignment";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { useReviewActivation } from "./useReviewActivation";
import { StageGuide } from "../components/StageGuide";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";
import { sectionEpisode } from "../features/graph/scriptProjection";
import { ScriptEpisodeView } from "../features/graph/ScriptEpisodeView";

type ProjectSession = { projectId: string; epoch: number };

/** F4 reviews one upstream JSON authority and permits only bound episode replacement. */
export function ScriptPanel({ projectId, readOnly: ownerReadOnly, active = true, refreshToken, onContinue, contextSectionId }: { projectId: string; readOnly: boolean; active?: boolean; refreshToken?: unknown; onContinue?: () => void; contextSectionId?: string }) {
  const [state, setState] = useState<ScriptReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState<ReviewContextFailure>("");
  const [busy, setBusy] = useState(false);
  const [sectionId, setSectionId] = useState("");
  const [draft, setDraft] = useState("");
  const [draftBase, setDraftBase] = useState<AcceptedScriptRevision | null>(null);
  const draftDirty = useRef(false);
  const activeProject = useRef<ProjectSession>({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) {
    activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  }
  const owns = (session: ProjectSession) => activeProject.current === session;
  const load = useCallback(async (isCurrent: () => boolean) => {
    const session = activeProject.current;
    if (owns(session)) setError("");
    try {
      const next = await plotloomApi.getScript(session.projectId);
      if (owns(session) && isCurrent()) { setState(next); return true; }
    } catch (reason) {
      if (owns(session) && isCurrent()) setError(reason instanceof Error ? reason.message : "无法读取剧本。");
    }
    return false;
  }, [projectId]);
  useEffect(() => {
    const session = activeProject.current;
    setState(undefined); setAssignment(""); setError(""); setBusy(false); setSectionId(""); setDraft("");
    setDraftBase(null); draftDirty.current = false;
    return () => {
      if (owns(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 };
    };
  }, [projectId, load]);
  const { checking, failed, recheck } = useReviewActivation({ projectId, active, refreshToken, load });
  const readOnly = ownerReadOnly || checking || failed;
  const acceptedHead = state?.acceptedScript;
  const reviewDraft = useReviewEditorDraft(projectId, "script", acceptedHead ? `script:${acceptedHead.revision}:${acceptedHead.contentHash}:${state?.status}` : "", text => {
    const recovered = JSON.parse(text) as { sectionId: string; text: string };
    if (typeof recovered.sectionId !== "string" || typeof recovered.text !== "string" || !acceptedHead?.binding.sectionBindings.some(item => item.sectionId === recovered.sectionId)) throw new Error("章节草稿无法匹配，请复制内容后重新填写。");
    setSectionId(recovered.sectionId); setDraft(recovered.text); setDraftBase(acceptedHead); draftDirty.current = true;
  }, readOnly || busy, () => { draftDirty.current = false; setSectionId(""); setDraft(""); setDraftBase(null); });
  useEffect(() => {
    // Dirty text keeps the revision/binding under which the author started.
    // A refreshed head can invalidate saving, but cannot discard that work.
    if (!draftDirty.current) { setSectionId(""); setDraft(""); setDraftBase(null); }
  }, [projectId, state?.acceptedScript?.revision, state?.acceptedScript?.contentHash, state?.status]);
  useEffect(() => {
    if (!contextSectionId || !acceptedHead || state?.status !== "reopened" || draftDirty.current) return;
    try {
      const episode = sectionEpisode(acceptedHead.script, acceptedHead.binding, contextSectionId);
      setSectionId(episode ? contextSectionId : ""); setDraft(episode ? JSON.stringify(episode, null, 2) : ""); setDraftBase(episode ? acceptedHead : null);
    } catch (reason) { setError(String(reason)); }
  }, [contextSectionId, acceptedHead?.revision, acceptedHead?.contentHash, state?.status]);

  const run = <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    void operation().then(async result => {
      if (!owns(session)) return;
      onSuccess?.(result);
      await recheck();
    }).catch(reason => {
      if (owns(session)) setError(reviewContextFailure(reason, "剧本操作失败。"));
    }).finally(() => {
      // Ownership remains held through response settlement; invalidation on
      // unmount/project switch makes this a deliberate no-op afterwards.
      if (owns(session)) setBusy(false);
    });
  };
  const prepare = () => run(() => plotloomApi.prepareScriptCandidate(projectId), result => setAssignment(result.assignment));
  if (!state) return <article id="script" className="panel cast-panel" data-testid="script-review">
    <header><span>剧本</span><strong>{error ? "无法加载" : "正在加载"}</strong></header>
    {error ? <><ReviewContextErrorNotice error={error} projectId={projectId} /><Button variant="quiet" onClick={() => void recheck()}>重试加载剧本</Button></> : <Spinner />}
  </article>;

  const { candidate, acceptedScript: accepted } = state;
  const draftMatches = Boolean(draftBase && accepted && draftBase.revision === accepted.revision && draftBase.contentHash === accepted.contentHash);
  const retained = Boolean(draftDirty.current && draftBase && (state.status !== "reopened" || !draftMatches));
  const selectSection = (nextSectionId: string) => {
    if (draftDirty.current && nextSectionId !== sectionId) { setError("请先保存或舍弃当前章节修改，再切换章节。"); return; }
    setSectionId(nextSectionId);
    setDraft(accepted ? episodeForSection(accepted, nextSectionId) : "");
    setDraftBase(accepted); draftDirty.current = false;
  };
  const editDraft = (next: string) => { draftDirty.current = next !== (draftBase ? episodeForSection(draftBase, sectionId) : ""); setDraft(next); reviewDraft.changed(JSON.stringify({ sectionId, text: next })); };
  const discardDraft = () => { draftDirty.current = false; setSectionId(""); setDraft(""); setDraftBase(null); void reviewDraft.clear(); };
  const adoptCurrent = () => { if (accepted) { draftDirty.current = false; setDraftBase(accepted); setDraft(episodeForSection(accepted, sectionId)); void reviewDraft.clear(); } };
  const save = () => {
    if (!draftBase || !draftMatches || state.status !== "reopened") { setError("草稿绑定已过期，请先明确舍弃草稿或采用当前章节。"); return; }
    try {
      const episode = JSON.parse(draft) as Record<string, unknown>;
      run(() => plotloomApi.saveScriptSection(projectId, {
        expectedScriptRevision: draftBase.revision,
        binding: draftBase.binding,
        sectionId,
        episode,
      }), discardDraft);
    } catch {
      setError("章节必须是有效 JSON。");
    }
  };
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : accepted?.candidateJobId;
  return <article id="script" className="panel cast-panel" data-testid="script-review">
    {reviewDraft.notice}
    <header><span>剧本</span><strong>{checking ? "正在刷新" : failed ? "无法刷新" : heading(state)}</strong></header>
    {failed && <Button variant="quiet" onClick={() => void recheck()}>重试加载剧本</Button>}
    <p>根据已确认的故事结构编写所有章节；每次完整播放依次经过选择、后续剧情与一个结局。</p>
    {contextSectionId && <><p>当前节点：{contextSectionId}。准备、发送、结果检查与确认使用影响整份剧本；章节保存仅替换所选稳定章节。</p>{accepted && <ScriptEpisodeView accepted={accepted} acceptedState={state.acceptedReviewState.status} sectionId={contextSectionId} />}</>}
    {contextSectionId && draftDirty.current && sectionId !== contextSectionId && <p role="status">正在保留 {sectionId} 的未保存章节；切换节点不会将其保存到 {contextSectionId}。请先保存或舍弃当前章节修改。</p>}
    <StageGuide next={onContinue && <Button variant="quiet" disabled={checking || failed || busy || draftDirty.current || state.acceptedReviewState.status !== "current" || !accepted} onClick={onContinue}>继续：分镜评审</Button>}>
      {checking ? "正在核对当前版本，请稍候。" : failed ? "读取失败，请先重试；暂时不能继续或修改。" : busy ? "正在处理剧本任务，请稍候。" : state.status === "reopened" || draftDirty.current ? "先保存或明确舍弃章节修改，再继续分镜。" : state.status === "stale" ? reviewContextNextStep(state.staleReasons[0], "请按当前审核要求重新准备并确认剧本。") : state.status === "accepted" && accepted ? "完整剧本已确认。下一步准备分镜评审；切换页面不会自动生成镜头或媒体。" : candidate?.status === "ready" ? "阅读候选剧本，确认开场、选择和结局表达，再确认使用。" : "准备剧本任务并发送给文字创作助手。返回的剧本须先审阅，再确认使用。"}
    </StageGuide>
    <ReviewContextNotice projectId={projectId} diagnostics={state.staleReasons} />
    {state.candidate && <AcceptedEvidenceNotice projectId={projectId} state={state.acceptedReviewState} />}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备剧本任务</Button>}
    {candidate?.status === "prepared" && <SpecialistTaskActions projectId={projectId} stage="script" jobId={candidate.jobId} disabled={readOnly || busy} sendDisabled={state.status === "stale"} onDelivered={recheck} />}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} stale={state.status === "stale"} busy={busy} run={run} />}
    {candidate?.status === "ready" && <><ScriptJson title="查看待审阅剧本" script={candidate.script} /><p>确认使用此剧本会确认整份故事结构中的所有章节。</p></>}
    {accepted && <AcceptedReview accepted={accepted} projectId={projectId} readOnly={readOnly || state.acceptedReviewState.status === "retained"} busy={busy} status={state.acceptedReviewState.status} retained={retained} sectionId={sectionId} draft={draft} onSelect={selectSection} onDraft={editDraft} onReopen={() => run(() => plotloomApi.reopenScript(projectId, accepted.revision))} onSave={save} />}
    {retained && draftBase && <section aria-label="保留的未保存章节">
      <p>保留的未保存章节基于剧本 r{draftBase.revision} · {sectionId}。当前上下文已变化，保存已停用；原草稿不会自动替换为新版本。</p>
      <textarea aria-label="保留的章节草稿" className="source-outline-json" rows={12} readOnly value={draft} />
      <Button disabled>保存此章节，不覆盖其他章节</Button>
      <Button disabled={ownerReadOnly || busy || checking} onClick={discardDraft}>舍弃章节草稿</Button>
      <Button disabled={readOnly || busy || !accepted} onClick={adoptCurrent}>用当前章节替换草稿</Button>
    </section>}
    {draftDirty.current && !retained && <Button disabled={readOnly || busy} onClick={discardDraft}>舍弃当前章节修改</Button>}
    {reportJobId && <StaticReportReader key={`${reportJobId}:${accepted?.revision}:${accepted?.contentHash}`} kind="script" url={plotloomApi.scriptCandidateReportUrl(projectId, reportJobId)} />}
    {candidate?.status === "prepared" && <details><summary>查看任务说明（手动方式）</summary><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverScriptHandoff(projectId, candidate.jobId), result => setAssignment(result.assignment))}>恢复剧本任务</Button>{assignment && <ManualTaskAssignment key={`${projectId}:${candidate.jobId}:${assignment}`} assignment={assignment} taskName="剧本" />}</details>}
    {error && <ReviewContextErrorNotice error={error} projectId={projectId} />}
  </article>;
}

function CandidateActions({ candidate, projectId, readOnly, stale, busy, run }: { candidate: ScriptCandidate; projectId: string; readOnly: boolean; stale: boolean; busy: boolean; run: <Result>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => void }) {
  if (candidate.status === "prepared") return <div className="button-row">
    <Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelScriptCandidate(projectId, candidate.jobId))}>取消此任务</Button>
  </div>;
  if (candidate.status === "ready") return <div className="button-row">
    <Button variant="primary" disabled={readOnly || stale || busy} onClick={() => run(() => plotloomApi.acceptScriptCandidate(projectId, { jobId: candidate.jobId, expectedScriptRevision: candidate.expectedScriptRevision, binding: candidate.binding, script: candidate.script || {} }))}>确认使用此剧本</Button>
    <Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelScriptCandidate(projectId, candidate.jobId))}>拒绝并取消此剧本</Button>
  </div>;
  return null;
}

function AcceptedReview({ accepted, projectId, readOnly, busy, status, retained, sectionId, draft, onSelect, onDraft, onReopen, onSave }: { accepted: AcceptedScriptRevision; projectId: string; readOnly: boolean; busy: boolean; status: ScriptReviewState["acceptedReviewState"]["status"]; retained: boolean; sectionId: string; draft: string; onSelect: (sectionId: string) => void; onDraft: (draft: string) => void; onReopen: () => void; onSave: () => void }) {
  const editing = status === "reopened";
  return <section>
    <small>{status === "retained" ? "保留的已确认剧本" : "已确认剧本"} r{accepted.revision} · hash {accepted.contentHash.slice(0, 12)}。原始报告保留最初交付的版本，可能与后续修改不同。</small>
    <ScriptJson title={status === "retained" ? "查看保留的已确认剧本" : "查看当前已确认剧本"} script={accepted.script} />
    {!editing && <Button variant="quiet" disabled={readOnly || busy} onClick={onReopen}>重新打开剧本</Button>}
    {editing && !retained && <SectionEditor accepted={accepted} disabled={readOnly || busy} sectionId={sectionId} draft={draft} onSelect={onSelect} onDraft={onDraft} onSave={onSave} />}
  </section>;
}

function SectionEditor({ accepted, disabled, sectionId, draft, onSelect, onDraft, onSave }: { accepted: AcceptedScriptRevision; disabled: boolean; sectionId: string; draft: string; onSelect: (sectionId: string) => void; onDraft: (draft: string) => void; onSave: () => void }) {
  return <section>
    <label>编辑章节<select disabled={disabled} value={sectionId} onChange={event => onSelect(event.target.value)}>
      <option value="">选择稳定章节</option>
      {accepted.binding.sectionBindings.map(item => <option key={item.sectionId} value={item.sectionId}>{item.sectionId} · episode {item.episode}</option>)}
    </select></label>
    {sectionId && <><textarea aria-label={`${sectionId} 章节剧本 JSON`} className="source-outline-json" disabled={disabled} rows={22} value={draft} onChange={event => onDraft(event.target.value)} /><Button variant="primary" disabled={disabled} onClick={onSave}>保存此章节，不覆盖其他章节</Button></>}
  </section>;
}

function ScriptJson({ title, script }: { title: string; script: Record<string, unknown> | null }) {
  return <details className="script-json-disclosure"><summary>{title}</summary><pre>{JSON.stringify(script, null, 2)}</pre></details>;
}

function episodeForSection(accepted: AcceptedScriptRevision, sectionId: string): string {
  if (!sectionId) return "";
  return JSON.stringify(sectionEpisode(accepted.script, accepted.binding, sectionId), null, 2);
}

function heading(state: ScriptReviewState): string {
  if (state.status === "stale") return "上下文已过期";
  if (state.status === "reopened") return "剧本正在编辑";
  if (state.candidate?.status === "ready") return "待审阅";
  if (state.candidate?.status === "prepared") return "任务尚未交付";
  if (state.acceptedScript) return `已确认 r${state.acceptedScript.revision}`;
  return "尚无剧本候选";
}
