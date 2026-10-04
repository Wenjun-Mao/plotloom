import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { AcceptedScriptRevision, ScriptCandidate, ScriptReviewState } from "../types";
import { ManualTaskAssignment } from "./ManualTaskAssignment";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { useReviewActivation } from "./useReviewActivation";
import { StageGuide } from "../components/StageGuide";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";

type ProjectSession = { projectId: string; epoch: number };

/** F4 reviews one upstream JSON authority and permits only bound episode replacement. */
export function ScriptPanel({ projectId, readOnly: ownerReadOnly, active = true, refreshToken, onContinue }: { projectId: string; readOnly: boolean; active?: boolean; refreshToken?: unknown; onContinue?: () => void }) {
  const [state, setState] = useState<ScriptReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
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

  const run = <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    void operation().then(async result => {
      if (!owns(session)) return;
      onSuccess?.(result);
      await recheck();
    }).catch(reason => {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "剧本操作失败。");
    }).finally(() => {
      // Ownership remains held through response settlement; invalidation on
      // unmount/project switch makes this a deliberate no-op afterwards.
      if (owns(session)) setBusy(false);
    });
  };
  const prepare = () => run(() => plotloomApi.prepareScriptCandidate(projectId), result => setAssignment(result.assignment));
  if (!state) return <article id="script" className="panel cast-panel" data-testid="script-review">
    <header><span>剧本</span><strong>{error ? "无法加载" : "正在加载"}</strong></header>
    {error ? <><ErrorNotice message={error} /><Button variant="quiet" onClick={() => void recheck()}>重试加载剧本</Button></> : <Spinner />}
  </article>;

  const { candidate, acceptedScript: accepted } = state;
  const script = activeScript(candidate, accepted);
  const draftMatches = Boolean(draftBase && accepted && draftBase.revision === accepted.revision && draftBase.contentHash === accepted.contentHash);
  const retained = Boolean(draftDirty.current && draftBase && (state.status !== "reopened" || !draftMatches));
  const selectSection = (nextSectionId: string) => {
    if (draftDirty.current && nextSectionId !== sectionId) { setError("请先保存或舍弃当前章节修改，再切换章节。"); return; }
    setSectionId(nextSectionId);
    setDraft(episodeForSection(script, nextSectionId));
    setDraftBase(accepted); draftDirty.current = false;
  };
  const editDraft = (next: string) => { draftDirty.current = next !== episodeForSection(draftBase?.script || null, sectionId); setDraft(next); reviewDraft.changed(JSON.stringify({ sectionId, text: next })); };
  const discardDraft = () => { draftDirty.current = false; setSectionId(""); setDraft(""); setDraftBase(null); void reviewDraft.clear(); };
  const adoptCurrent = () => { if (accepted) { draftDirty.current = false; setDraftBase(accepted); setDraft(episodeForSection(accepted.script, sectionId)); void reviewDraft.clear(); } };
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
    <p>根据已确认的故事分支编写开场和两个结局；每次观看只会经过其中一个结局。</p>
    <StageGuide next={onContinue && <Button variant="quiet" disabled={checking || failed || busy || draftDirty.current || state.status !== "accepted" || !accepted} onClick={onContinue}>继续：分镜评审</Button>}>
      {checking ? "正在核对当前版本，请稍候。" : failed ? "读取失败，请先重试；暂时不能继续或修改。" : busy ? "正在处理剧本任务，请稍候。" : state.status === "reopened" || draftDirty.current ? "先保存或明确舍弃章节修改，再继续分镜。" : state.status === "stale" ? "故事或美术设定已变化，请更新并确认剧本。" : state.status === "accepted" && accepted ? "完整剧本已确认。下一步准备分镜评审；切换页面不会自动生成镜头或媒体。" : candidate?.status === "ready" ? "阅读候选剧本，确认开场、选择和结局表达，再确认使用。" : "准备剧本任务并发送给文字创作助手。返回的剧本须先审阅，再确认使用。"}
    </StageGuide>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备剧本任务</Button>}
    {candidate?.status === "prepared" && <SpecialistTaskActions projectId={projectId} stage="script" jobId={candidate.jobId} disabled={readOnly || busy} sendDisabled={state.status === "stale"} onDelivered={recheck} />}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} stale={state.status === "stale"} busy={busy} run={run} />}
    {candidate?.status === "ready" && <><ScriptJson title="查看待审阅剧本" script={candidate.script} /><p>确认使用此剧本会确认开场和两个结局，不只确认当前显示的章节。</p></>}
    {accepted && <AcceptedReview accepted={accepted} projectId={projectId} readOnly={readOnly || state.status === "stale"} busy={busy} status={state.status} retained={retained} sectionId={sectionId} draft={draft} onSelect={selectSection} onDraft={editDraft} onReopen={() => run(() => plotloomApi.reopenScript(projectId, accepted.revision))} onSave={save} />}
    {retained && draftBase && <section aria-label="保留的未保存章节">
      <p>保留的未保存章节基于剧本 r{draftBase.revision} · {sectionId}。当前上下文已变化，保存已停用；原草稿不会自动替换为新版本。</p>
      <textarea aria-label="保留的章节草稿" className="source-outline-json" rows={12} readOnly value={draft} />
      <Button disabled>保存此章节，不覆盖其他章节</Button>
      <Button disabled={ownerReadOnly || busy || checking} onClick={discardDraft}>舍弃章节草稿</Button>
      <Button disabled={readOnly || busy || !accepted} onClick={adoptCurrent}>用当前章节替换草稿</Button>
    </section>}
    {reportJobId && <Report projectId={projectId} jobId={reportJobId} />}
    {candidate?.status === "prepared" && <details><summary>查看任务说明（手动方式）</summary><Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverScriptHandoff(projectId, candidate.jobId), result => setAssignment(result.assignment))}>恢复剧本任务</Button>{assignment && <ManualTaskAssignment key={`${projectId}:${candidate.jobId}:${assignment}`} assignment={assignment} taskName="剧本" />}</details>}
    {error && <ErrorNotice message={error} />}
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

function AcceptedReview({ accepted, projectId, readOnly, busy, status, retained, sectionId, draft, onSelect, onDraft, onReopen, onSave }: { accepted: AcceptedScriptRevision; projectId: string; readOnly: boolean; busy: boolean; status: ScriptReviewState["status"]; retained: boolean; sectionId: string; draft: string; onSelect: (sectionId: string) => void; onDraft: (draft: string) => void; onReopen: () => void; onSave: () => void }) {
  const editing = status === "reopened";
  return <section>
    <small>已确认 r{accepted.revision} · hash {accepted.contentHash.slice(0, 12)}。当前 JSON 可直接检查；上游报告始终是原始派生报告。</small>
    <ScriptJson title="查看当前已确认剧本" script={accepted.script} />
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
    {sectionId && <><textarea className="source-outline-json" disabled={disabled} rows={22} value={draft} onChange={event => onDraft(event.target.value)} /><Button variant="primary" disabled={disabled} onClick={onSave}>保存此章节，不覆盖其他章节</Button></>}
  </section>;
}

function ScriptJson({ title, script }: { title: string; script: Record<string, unknown> | null }) {
  return <details><summary>{title}</summary><pre>{JSON.stringify(script, null, 2)}</pre></details>;
}

function Report({ projectId, jobId }: { projectId: string; jobId: string }) {
  return <details><summary>打开原始只读上游报告</summary><iframe title="original derived upstream script report" className="source-outline-report" sandbox="" src={plotloomApi.scriptCandidateReportUrl(projectId, jobId)} /></details>;
}

function activeScript(candidate: ScriptCandidate | null, accepted: AcceptedScriptRevision | null): Record<string, unknown> | null {
  if (candidate?.status === "ready") return candidate.script;
  return accepted?.script || null;
}

function episodeForSection(script: Record<string, unknown> | null, sectionId: string): string {
  const bindings = Array.isArray(script?.sectionBindings) ? script.sectionBindings : [];
  const binding = bindings.find(item => typeof item === "object" && item !== null && (item as Record<string, unknown>).sectionId === sectionId) as Record<string, unknown> | undefined;
  const episodes = Array.isArray(script?.episodes) ? script.episodes : [];
  const episode = episodes.find(item => typeof item === "object" && item !== null && (item as Record<string, unknown>).ep === binding?.episode);
  return JSON.stringify(episode || {}, null, 2);
}

function heading(state: ScriptReviewState): string {
  if (state.status === "stale") return "上下文已过期";
  if (state.status === "reopened") return "剧本正在编辑";
  if (state.candidate?.status === "ready") return "待审阅";
  if (state.candidate?.status === "prepared") return "任务已准备";
  if (state.acceptedScript) return `已确认 r${state.acceptedScript.revision}`;
  return "尚无剧本候选";
}
