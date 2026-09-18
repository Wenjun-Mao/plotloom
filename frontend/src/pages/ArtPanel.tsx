import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { ArtCandidate, ArtReviewState } from "../types";

type EditorProps = { disabled: boolean; draft: string; setDraft: (value: string) => void };

/** F3A remains text-first: image work and asset currentness are deliberately F3B/F5. */
export function ArtPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ArtReviewState>();
  const [assignment, setAssignment] = useState("");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeProjectId = useRef(projectId);
  const load = useCallback(() => {
    const owner = projectId;
    void plotloomApi.getArt(owner).then(next => {
      if (activeProjectId.current === owner) setState(next);
    }).catch(error => {
      if (activeProjectId.current === owner) setError(error.message);
    });
  }, [projectId]);
  useEffect(() => {
    activeProjectId.current = projectId;
    setState(undefined); setAssignment(""); setDraft(""); setError(""); setBusy(false);
    load();
  }, [projectId, load]);
  useEffect(() => {
    // The accepted revision is the current project-owned record. Reopen changes
    // only whether it is editable; it must never be the sole way to inspect it.
    const art = state?.candidate?.status === "ready" ? state.candidate.art : state?.acceptedArt?.art;
    if (art) setDraft(JSON.stringify(art, null, 2));
  }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedArt?.revision, state?.status]);
  const act = (operation: () => Promise<unknown>) => {
    const owner = projectId;
    setBusy(true); setError("");
    void operation().then(() => { if (activeProjectId.current === owner) load(); }).catch(error => {
      if (activeProjectId.current === owner) setError(error.message);
    }).finally(() => { if (activeProjectId.current === owner) setBusy(false); });
  };
  const parsed = () => { try { return JSON.parse(draft) as Record<string, unknown>; } catch { setError("art.json 必须是有效 JSON。"); return undefined; } };
  if (!state) return null;
  const { candidate, acceptedArt: accepted } = state;
  const heading = state.status === "stale" ? "上下文已过期" : accepted ? `已接受 r${accepted.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无美术候选";
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : accepted?.candidateJobId;
  const prepare = () => { const owner = projectId; setBusy(true); void plotloomApi.prepareArtCandidate(owner).then(result => { if (activeProjectId.current === owner) { setAssignment(result.assignment); load(); } }).catch(error => { if (activeProjectId.current === owner) setError(error.message); }).finally(() => { if (activeProjectId.current === owner) setBusy(false); }); };
  const recover = () => candidate && act(async () => {
    const result = await plotloomApi.recoverArtHandoff(projectId, candidate.jobId);
    if (activeProjectId.current === projectId) setAssignment(result.assignment);
  });
  const accept = () => { const art = parsed(); if (art && candidate) act(() => plotloomApi.acceptArtCandidate(projectId, { jobId: candidate.jobId, expectedArtRevision: candidate.expectedArtRevision, binding: candidate.binding, art })); };
  const save = () => { const art = parsed(); if (art && accepted) act(() => plotloomApi.saveReopenedArt(projectId, { expectedArtRevision: accepted.revision, binding: accepted.binding, art })); };
  return <article className="panel cast-panel" data-testid="art-review">
    <header><span>06 · F3A novel-art proposal</span><strong>{heading}</strong></header>
    <p>共享地点、道具与可核对锚点在此处以文本先行审阅。此阶段不生成图片、不声称资产已存在或当前；F3B 将另行验证环境/道具参考。继承的 cinematic realism 与上游 semi-realistic painterly 预设差异会显式保留给 F3B。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备并复制 art specialist handoff</Button>}
    {candidate && <CandidateReview candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} draft={draft} setDraft={setDraft} recover={recover} refresh={() => act(() => plotloomApi.refreshArtCandidate(projectId, candidate.jobId))} cancel={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))} accept={accept} />}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；文本与报告可审阅，但尚无图片或选择资产。</small>{state.status !== "reopened" && <Editor disabled draft={draft} setDraft={setDraft} />}{reportJobId && <Report projectId={projectId} jobId={reportJobId} />}<Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
    {accepted && state.status === "reopened" && <><Editor disabled={readOnly || busy} draft={draft} setDraft={setDraft} /><Button variant="primary" disabled={readOnly || busy} onClick={save}>保存重新打开的美术</Button></>}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}
    {error && <ErrorNotice message={error} />}
  </article>;
}

function CandidateReview({ candidate, projectId, readOnly, busy, draft, setDraft, recover, refresh, cancel, accept }: { candidate: ArtCandidate; projectId: string; readOnly: boolean; busy: boolean; draft: string; setDraft: (value: string) => void; recover: () => void; refresh: () => void; cancel: () => void; accept: () => void }) {
  return <><small>冻结 source r{candidate.binding.sourceRevision} · cast r{candidate.binding.castRevision} · sections {candidate.binding.sectionIds.join(" · ")}</small>
    {candidate.status === "prepared" && <><Button disabled={readOnly || busy} onClick={recover}>重新复制冻结 handoff</Button><Button disabled={readOnly || busy} onClick={refresh}>刷新 specialist delivery</Button><Button variant="danger" disabled={readOnly || busy} onClick={cancel}>取消 handoff</Button></>}
    {candidate.status === "ready" && <><Editor disabled={readOnly || busy} draft={draft} setDraft={setDraft} />{candidate.reportAvailable && <Report projectId={projectId} jobId={candidate.jobId} />}<Button variant="primary" disabled={readOnly || busy} onClick={accept}>显式接受此美术提案</Button><Button variant="danger" disabled={readOnly || busy} onClick={cancel}>拒绝并取消此美术提案</Button></>}
  </>;
}

function Editor({ disabled, draft, setDraft }: EditorProps) {
  return <details open><summary>查看/编辑 art.json（稳定地点和道具 ID 不可替换）</summary><textarea className="source-outline-json" disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} rows={24} /></details>;
}

function Report({ projectId, jobId }: { projectId: string; jobId: string }) {
  return <details><summary>打开只读上游报告</summary><iframe title="derived upstream art report" className="source-outline-report" sandbox="" src={plotloomApi.artCandidateReportUrl(projectId, jobId)} /></details>;
}
