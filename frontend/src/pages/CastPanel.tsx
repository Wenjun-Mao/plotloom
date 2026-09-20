import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { CastReviewState } from "../types";

export function CastPanel({ projectId, readOnly, state, loadError, onState, onRefresh, onInvalidate, onTransitionComplete }: { projectId: string; readOnly: boolean; state: CastReviewState | undefined; loadError: string; onState: (state: CastReviewState) => void; onRefresh: (expectedOwner?: number) => Promise<boolean>; onInvalidate: () => void; onTransitionComplete: () => void }) {
  const [assignment, setAssignment] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [editedCast, setEditedCast] = useState<Record<string, unknown>>({});
  const operationOwner = useRef(0); const active = useRef(true); const projectRef = useRef(projectId);
  projectRef.current = projectId;
  useEffect(() => { active.current = true; return () => { active.current = false; operationOwner.current += 1; }; }, []);
  useEffect(() => { const editable = state?.candidate?.status === "ready" ? state.candidate.cast : state?.status === "reopened" ? state.acceptedCast?.cast : undefined; if (editable) setEditedCast(structuredClone(editable)); }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedCast?.revision, state?.status]);
  const isCurrent = (capturedProject: string, capturedOwner: number) => active.current && projectRef.current === capturedProject && operationOwner.current === capturedOwner;
  const act = <T,>(operation: () => Promise<T>, applyResult?: (result: T) => void, invalidatesSession = false) => {
    const capturedProject = projectRef.current; const capturedOwner = ++operationOwner.current;
    if (invalidatesSession) onInvalidate();
    setBusy(true); setError("");
    void operation().then(async (result) => {
      if (!isCurrent(capturedProject, capturedOwner)) return;
      if (isCastState(result)) onState(result);
      else { applyResult?.(result); await onRefresh(); }
    }).catch((reason: unknown) => { if (isCurrent(capturedProject, capturedOwner)) setError(reason instanceof Error ? reason.message : "角色操作失败。"); }).finally(() => { if (isCurrent(capturedProject, capturedOwner)) { if (invalidatesSession) onTransitionComplete(); setBusy(false); } });
  };
  if (!state) return null;
  const candidate = state.candidate; const accepted = state.acceptedCast;
  const castCharacters = Array.isArray(editedCast.characters) ? editedCast.characters as Array<Record<string, unknown>> : [];
  const updateDirection = (index: number, group: "persona" | "voice", key: "motivation" | "appearance" | "timbre", value: string) => setEditedCast(current => ({ ...current, characters: castCharacters.map((character, candidateIndex) => candidateIndex === index ? { ...character, [group]: { ...(character[group] as Record<string, unknown> || {}), [key]: value } } : character) }));
  return <article className="panel cast-panel" data-testid="cast-review">
    <header><span>05 · F2A character proposal</span><strong>{state.status === "stale" ? "上下文已过期" : accepted ? `已接受 r${accepted.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无角色候选"}</strong></header>
    <p>共享角色只在此处接受一次，绑定当前来源、大纲和稳定章节。上游报告是只读、未审核候选；文字方向不是声音或身份一致性的证明。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.prepareCastCandidate(projectId), (result) => setAssignment(result.assignment))}>准备并复制 specialist handoff</Button>}
    {candidate && <><small>冻结 source r{candidate.binding.sourceRevision} · outline r{candidate.binding.outlineRevision} · sections {candidate.binding.sectionIds.join(" · ")}</small>
      {candidate.status === "prepared" && <><Button disabled={readOnly || busy} onClick={() => act(() => plotloomApi.refreshCastCandidate(projectId, candidate.jobId))}>刷新 specialist delivery</Button><Button variant="danger" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelCastCandidate(projectId, candidate.jobId))}>取消 handoff</Button></>}
      {candidate.status === "ready" && <><details><summary>查看上游 cast.json</summary><pre>{JSON.stringify(candidate.cast, null, 2)}</pre></details>{candidate.reportAvailable && <details><summary>打开只读上游报告</summary><iframe title="derived upstream cast report" className="source-outline-report" sandbox="" src={plotloomApi.castCandidateReportUrl(projectId, candidate.jobId)} /></details>}
        <section className="cast-forms"><strong>角色动机、外观与声音方向（作者可编辑）</strong>{castCharacters.map((character, index) => <fieldset key={String(character.id || index)}><legend>{String(character.name || character.id || `角色 ${index + 1}`)}</legend><label>动机<textarea disabled={readOnly || busy} value={String((character.persona as Record<string, unknown> | undefined)?.motivation || "")} onChange={event => updateDirection(index, "persona", "motivation", event.target.value)} /></label><label>外观<textarea disabled={readOnly || busy} value={String((character.persona as Record<string, unknown> | undefined)?.appearance || "")} onChange={event => updateDirection(index, "persona", "appearance", event.target.value)} /></label><label>声音方向<textarea disabled={readOnly || busy} value={String((character.voice as Record<string, unknown> | undefined)?.timbre || "")} onChange={event => updateDirection(index, "voice", "timbre", event.target.value)} /></label></fieldset>)}</section>
        <Button variant="primary" disabled={readOnly || busy || castCharacters.length === 0} onClick={() => act(() => plotloomApi.acceptCastCandidate(projectId, { jobId: candidate.jobId, expectedCastRevision: candidate.expectedCastRevision, binding: candidate.binding, cast: editedCast, consumerMappings: castCharacters.map(character => ({ castCharacterId: String(character.id), consumerCharacterId: String(character.id) })) }), undefined, true)}>显式接受此角色提案</Button></>}
    </>}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；为 F2B 的既有角色参考/媒体消费者保留明确 ID 映射。</small><Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenCast(projectId, accepted.revision), undefined, true)}>重新打开角色提案</Button></>}
    {accepted && state.status === "reopened" && <><section className="cast-forms"><strong>重新打开后编辑并保存</strong>{castCharacters.map((character, index) => <fieldset key={String(character.id || index)}><legend>{String(character.name || character.id || `角色 ${index + 1}`)}</legend><label>动机<textarea disabled={readOnly || busy} value={String((character.persona as Record<string, unknown>)?.motivation || "")} onChange={event => updateDirection(index, "persona", "motivation", event.target.value)} /></label><label>外观<textarea disabled={readOnly || busy} value={String((character.persona as Record<string, unknown>)?.appearance || "")} onChange={event => updateDirection(index, "persona", "appearance", event.target.value)} /></label><label>声音方向<textarea disabled={readOnly || busy} value={String((character.voice as Record<string, unknown>)?.timbre || "")} onChange={event => updateDirection(index, "voice", "timbre", event.target.value)} /></label></fieldset>)}</section><Button variant="primary" disabled={readOnly || busy || castCharacters.length === 0} onClick={() => act(() => plotloomApi.saveReopenedCast(projectId, { expectedCastRevision: accepted.revision, binding: accepted.binding, cast: editedCast, consumerMappings: accepted.consumerMappings }), undefined, true)}>保存重新打开的角色</Button></>}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}{(error || loadError) && <ErrorNotice message={error || loadError} />}
  </article>;
}

function isCastState(value: unknown): value is CastReviewState { return typeof value === "object" && value !== null && "status" in value && "acceptedCast" in value; }
