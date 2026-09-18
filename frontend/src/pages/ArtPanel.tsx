import { useEffect, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { ArtReviewState } from "../types";

/** F3A remains text-first: image work and asset currentness are deliberately F3B/F5. */
export function ArtPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ArtReviewState>(); const [assignment, setAssignment] = useState(""); const [draft, setDraft] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const load = () => void plotloomApi.getArt(projectId).then(setState).catch(error => setError(error.message));
  useEffect(load, [projectId]);
  useEffect(() => { const art = state?.candidate?.status === "ready" ? state.candidate.art : state?.status === "reopened" ? state.acceptedArt?.art : undefined; if (art) setDraft(JSON.stringify(art, null, 2)); }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedArt?.revision, state?.status]);
  const act = (operation: () => Promise<unknown>) => { setBusy(true); setError(""); void operation().then(load).catch(error => setError(error.message)).finally(() => setBusy(false)); };
  const parsed = () => { try { return JSON.parse(draft) as Record<string, unknown>; } catch { setError("art.json 必须是有效 JSON。"); return undefined; } };
  if (!state) return null;
  const candidate = state.candidate; const accepted = state.acceptedArt;
  return <article className="panel cast-panel" data-testid="art-review"><header><span>06 · F3A novel-art proposal</span><strong>{state.status === "stale" ? "上下文已过期" : accepted ? `已接受 r${accepted.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无美术候选"}</strong></header>
    <p>共享地点、道具与可核对锚点在此处以文本先行审阅。此阶段不生成图片、不声称资产已存在或当前；F3B 将另行验证环境/道具参考。继承的 cinematic realism 与上游 semi-realistic painterly 预设差异会显式保留给 F3B。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={() => { setBusy(true); void plotloomApi.prepareArtCandidate(projectId).then(result => { setAssignment(result.assignment); load(); }).catch(error => setError(error.message)).finally(() => setBusy(false)); }}>准备并复制 art specialist handoff</Button>}
    {candidate && <><small>冻结 source r{candidate.binding.sourceRevision} · cast r{candidate.binding.castRevision} · sections {candidate.binding.sectionIds.join(" · ")}</small>{candidate.status === "prepared" && <><Button disabled={readOnly || busy} onClick={() => act(() => plotloomApi.refreshArtCandidate(projectId, candidate.jobId))}>刷新 specialist delivery</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))}>取消 handoff</Button></>}{candidate.status === "ready" && <><details><summary>查看/编辑 art.json（稳定地点和道具 ID 不可替换）</summary><textarea className="source-outline-json" disabled={readOnly || busy} value={draft} onChange={event => setDraft(event.target.value)} rows={24} /></details>{candidate.reportAvailable && <details><summary>打开只读上游报告</summary><iframe title="derived upstream art report" className="source-outline-report" sandbox="" src={plotloomApi.artCandidateReportUrl(projectId, candidate.jobId)} /></details>}<Button variant="primary" disabled={readOnly || busy} onClick={() => { const art = parsed(); if (art) act(() => plotloomApi.acceptArtCandidate(projectId, { jobId: candidate.jobId, expectedArtRevision: candidate.expectedArtRevision, binding: candidate.binding, art })); }}>显式接受此美术提案</Button></>}</>}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；文本与报告可审阅，但尚无图片或选择资产。</small><Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
    {accepted && state.status === "reopened" && <><textarea className="source-outline-json" disabled={readOnly || busy} value={draft} onChange={event => setDraft(event.target.value)} rows={24} /><Button variant="primary" disabled={readOnly || busy} onClick={() => { const art = parsed(); if (art) act(() => plotloomApi.saveReopenedArt(projectId, { expectedArtRevision: accepted.revision, binding: accepted.binding, art })); }}>保存重新打开的美术</Button></>}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}{error && <ErrorNotice message={error} />}
  </article>;
}
