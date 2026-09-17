import { useEffect, useState } from "react";
import { ApiError, plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { SourceMaterial, SourceOutlineReviewState } from "../types";

const blankSource: SourceMaterial = {
  kind: "synopsis",
  title: "",
  text: "",
  attribution: "",
  rightsDeclaration: "",
  adaptationIntent: "",
  inventedAdditions: null,
};

function sourceMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 409) return `当前版本已变化：${error.message}。请刷新后再决定。`;
  return error instanceof Error ? error.message : "来源与大纲操作失败。";
}

export function SourceOutlinePage({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<SourceOutlineReviewState>();
  const [draft, setDraft] = useState<SourceMaterial>(blankSource);
  const [assignment, setAssignment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const next = await plotloomApi.getSourceOutline(projectId);
      setState(next);
      setDraft(next.source?.material || blankSource);
    } catch (loadError) { setError(sourceMessage(loadError)); }
  };

  useEffect(() => { void load(); }, [projectId]); // The project route owns refreshes.

  const mutate = async (operation: () => Promise<SourceOutlineReviewState>) => {
    setBusy(true); setError("");
    try {
      const next = await operation();
      setState(next); setDraft(next.source?.material || blankSource);
    } catch (mutationError) { setError(sourceMessage(mutationError)); }
    finally { setBusy(false); }
  };

  if (!state) return <section className="page"><Spinner />{error && <ErrorNotice message={error} />}</section>;
  const candidate = state.candidate;
  const accepted = state.acceptedOutline;
  const canSave = !readOnly && !busy && Boolean(draft.title.trim() && draft.text.trim() && draft.attribution.trim() && draft.rightsDeclaration.trim() && draft.adaptationIntent.trim());

  return <section className="page source-outline-page">
    <header className="page-header"><div><span>F1A · Project-owned review</span><h1>来源与小说大纲</h1><p>来源、候选和已接受大纲互相独立。权利声明按作者填写保存，不构成平台的法律确认。</p></div><Button variant="quiet" disabled={busy} onClick={() => void load()}>刷新</Button></header>
    {error && <ErrorNotice message={error} />}
    <div className="source-outline-grid">
      <article className="panel source-outline-source" data-testid="source-outline-source">
        <header><span>01 · Accepted source</span><strong>{state.source ? `来源 r${state.source.revision}` : "尚未保存来源"}</strong></header>
        <label>来源类型<select disabled={readOnly || busy} value={draft.kind} onChange={(event) => setDraft({ ...draft, kind: event.target.value as SourceMaterial["kind"] })}><option value="synopsis">梗概（发展为来源故事）</option><option value="imported_text">导入文字 / treatment</option><option value="existing_work">既有作品改编</option></select></label>
        <label>标题<input disabled={readOnly || busy} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
        <label>来源正文或 treatment<textarea disabled={readOnly || busy} value={draft.text} onChange={(event) => setDraft({ ...draft, text: event.target.value })} rows={10} /></label>
        <label>归属 / 署名声明<textarea disabled={readOnly || busy} value={draft.attribution} onChange={(event) => setDraft({ ...draft, attribution: event.target.value })} rows={3} /></label>
        <label>使用权或许可声明<textarea disabled={readOnly || busy} value={draft.rightsDeclaration} onChange={(event) => setDraft({ ...draft, rightsDeclaration: event.target.value })} rows={3} /></label>
        <label>改编意图<textarea disabled={readOnly || busy} value={draft.adaptationIntent} onChange={(event) => setDraft({ ...draft, adaptationIntent: event.target.value })} rows={3} /></label>
        <label>允许的原创补充（可选）<textarea disabled={readOnly || busy} value={draft.inventedAdditions || ""} onChange={(event) => setDraft({ ...draft, inventedAdditions: event.target.value || null })} rows={3} /></label>
        <Button variant="primary" disabled={!canSave} onClick={() => void mutate(() => plotloomApi.saveSourceMaterial(projectId, state.source?.revision || 0, draft))}>{busy ? "正在保存…" : "保存接受的来源"}</Button>
      </article>

      <article className="panel source-outline-candidate" data-testid="source-outline-candidate">
        <header><span>02 · Candidate only</span><strong>{candidate ? `${candidate.status === "ready" ? "可审核" : "等待 specialist"} · ${candidate.jobId.slice(0, 11)}` : "尚无候选"}</strong></header>
        <p>候选只能来自当前接受的来源和大纲版本；它不会自动替换已接受内容。</p>
        {!candidate && <Button variant="primary" disabled={readOnly || busy || !state.source} onClick={() => {
          setBusy(true); setError("");
          void plotloomApi.prepareOutlineCandidate(projectId).then((prepared) => {
            setAssignment(prepared.assignment); return load();
          }).catch((prepareError) => setError(sourceMessage(prepareError))).finally(() => setBusy(false));
        }}>{busy ? "正在准备…" : "准备 specialist handoff"}</Button>}
        {candidate && <>
          <small>冻结来源 r{candidate.sourceRevision} · 目标已接受大纲 r{candidate.expectedOutlineRevision}</small>
          {candidate.status === "prepared" && <Button disabled={readOnly || busy} onClick={() => {
            setBusy(true); setError("");
            void plotloomApi.refreshOutlineCandidate(projectId, candidate.jobId).then(load).catch((refreshError) => setError(sourceMessage(refreshError))).finally(() => setBusy(false));
          }}>{busy ? "正在检查…" : "刷新 specialist delivery"}</Button>}
          {candidate.status === "ready" && <><details><summary>查看上游 outline.json</summary><pre>{JSON.stringify(candidate.outline, null, 2)}</pre></details>{candidate.reportAvailable && <iframe title="derived upstream outline report" className="source-outline-report" sandbox="" src={plotloomApi.outlineCandidateReportUrl(projectId, candidate.jobId)} />}</>}
          {candidate.status === "ready" && state.source && <Button variant="primary" disabled={readOnly || busy} onClick={() => void mutate(() => plotloomApi.acceptOutlineCandidate(projectId, { jobId: candidate.jobId, expectedSourceRevision: state.source!.revision, expectedOutlineRevision: accepted?.revision || 0 }))}>显式接受此候选</Button>}
        </>}
        {assignment && <label>复制给 specialist 的冻结任务<textarea aria-label="specialist assignment" readOnly value={assignment} rows={6} /></label>}
      </article>

      <article className="panel source-outline-accepted" data-testid="source-outline-accepted">
        <header><span>03 · Accepted outline</span><strong>{accepted ? `已接受 r${accepted.revision}` : "尚未接受"}</strong></header>
        <p>当前状态：{state.outlineStatus === "accepted" ? "已接受" : state.outlineStatus === "reopened" ? "已重新打开，需新的候选" : state.outlineStatus === "candidate_ready" ? "候选可审核" : "缺失"}</p>
        {accepted ? <><small>基于来源 r{accepted.sourceRevision} · 候选 {accepted.candidateJobId.slice(0, 11)}</small><details><summary>查看接受的原始 outline.json</summary><pre>{JSON.stringify(accepted.outline, null, 2)}</pre></details><Button variant="quiet" disabled={readOnly || busy || state.outlineStatus === "reopened"} onClick={() => void mutate(() => plotloomApi.reopenOutline(projectId, accepted.revision))}>重新打开，不替换内容</Button></> : <p className="muted">接受操作会新建不可变的大纲 revision；此处绝不从候选静默同步。</p>}
      </article>
    </div>
  </section>;
}
