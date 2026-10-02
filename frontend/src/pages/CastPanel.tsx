import { useEffect, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { AcceptedCastRevision, CastReviewState } from "../types";
import { CastEditor, type CastDirectionChange } from "./CastEditor";
import { CastInferenceNotes } from "./CastInferenceNotes";
import { castTextPresentation } from "./cast-text-presentation";
import { hasValidCastDesign } from "./cast-design-validation";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";

type CastPanelProps = {
  projectId: string; readOnly: boolean; state: CastReviewState | undefined; loadError: string;
  onState: (state: CastReviewState) => void; onRefresh: (expectedOwner?: number) => Promise<boolean>;
  onInvalidate: () => void; onTransitionComplete: () => void;
};

export function CastPanel({ projectId, readOnly, state, loadError, onState, onRefresh, onInvalidate, onTransitionComplete }: CastPanelProps) {
  const [assignment, setAssignment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editedCast, setEditedCast] = useState<Record<string, unknown>>({});
  const operationOwner = useRef(0); const active = useRef(true); const projectRef = useRef(projectId);
  projectRef.current = projectId;
  useEffect(() => { active.current = true; return () => { active.current = false; operationOwner.current += 1; }; }, []);
  useEffect(() => {
    const editable = state?.candidate?.status === "ready" ? state.candidate.cast : state?.status === "reopened" ? state.acceptedCast?.cast : undefined;
    if (editable) setEditedCast(structuredClone(editable));
  }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedCast?.revision, state?.status]);

  const isCurrent = (capturedProject: string, capturedOwner: number) => active.current && projectRef.current === capturedProject && operationOwner.current === capturedOwner;
  const act = <T,>(operation: () => Promise<T>, applyResult?: (result: T) => void, invalidatesSession = false, refreshAfterFailure = false) => {
    const capturedProject = projectRef.current; const capturedOwner = ++operationOwner.current;
    if (invalidatesSession) onInvalidate();
    setBusy(true); setError("");
    void operation().then(async (result) => {
      if (!isCurrent(capturedProject, capturedOwner)) return;
      if (isCastState(result)) onState(result);
      else { applyResult?.(result); await onRefresh(); }
    }).catch(async (reason: unknown) => {
      if (!isCurrent(capturedProject, capturedOwner)) return;
      setError(reason instanceof Error ? reason.message : "角色操作失败。");
      // A failed cancellation can mean its accepted binding changed while the
      // form was open. Re-read that durable state instead of leaving a local
      // editor that implies the prior authority can still be restored.
      if (refreshAfterFailure) await onRefresh();
    }).finally(() => {
      if (isCurrent(capturedProject, capturedOwner)) {
        if (invalidatesSession) onTransitionComplete();
        setBusy(false);
      }
    });
  };
  if (!state) return null;

  const candidate = state.candidate; const accepted = state.acceptedCast;
  const castCharacters = charactersOf(editedCast);
  const canConfirm = hasValidCastDesign(castCharacters);
  const updateDirection: CastDirectionChange = (index, group, key, value) => setEditedCast((current) => ({
    ...current,
    characters: charactersOf(current).map((character, candidateIndex) => candidateIndex === index ? { ...character, [group]: { ...(group === "reviewNotes" ? { sourceNotes: "", performanceGuidance: "" } : {}), ...record(character[group]), [key]: value } } : character),
  }));
  const saveAccepted = () => canConfirm && act(() => plotloomApi.acceptCastCandidate(projectId, {
    jobId: candidate!.jobId, expectedCastRevision: candidate!.expectedCastRevision, binding: candidate!.binding, cast: editedCast,
    consumerMappings: castCharacters.map((character) => ({ castCharacterId: String(character.id), consumerCharacterId: String(character.id) })),
  }), undefined, true);

  return <article className="panel cast-panel" data-testid="cast-review">
    <header className="cast-panel-heading"><div><span className="eyebrow">角色设定</span><h2>{accepted ? `已接受角色设定 r${accepted.revision}` : candidate?.status === "ready" ? "审核角色设定" : "角色设定"}</h2></div><span className={`reference-state ${state.status === "stale" ? "historical" : accepted ? "selected" : "candidate"}`}>{state.status === "stale" ? "上下文已过期" : accepted ? "已接受" : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "任务已准备" : "尚无提案"}</span></header>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {accepted && <AcceptedCastSummary accepted={accepted} onEdit={() => act(() => plotloomApi.reopenCast(projectId, accepted.revision), undefined, true)} disabled={readOnly || busy || state.status === "reopened"} />}
    {!candidate && state.status !== "reopened" && <section className="cast-next-action"><div><strong>创建新角色提案</strong><small>先准备任务，再发送给文字创作助手。结果需要你审核确认。</small></div><Button variant="quiet" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.prepareCastCandidate(projectId), (result) => setAssignment(result.assignment))}>创建新角色提案</Button></section>}
    {candidate && <>
      <details className="cast-technical"><summary>查看提案来源与技术详情</summary><small>冻结来源与章节：r{candidate.binding.sourceRevision} · r{candidate.binding.outlineRevision} · {candidate.binding.sectionIds.join(" · ")}</small>{candidate.status === "ready" && <><pre>{JSON.stringify(candidate.cast, null, 2)}</pre>{candidate.reportAvailable && <iframe title="只读上游角色报告" className="source-outline-report" sandbox="" src={plotloomApi.castCandidateReportUrl(projectId, candidate.jobId)} />}</>}</details>
      {candidate.status === "prepared" && <><SpecialistTaskActions projectId={projectId} stage="characters" jobId={candidate.jobId} disabled={readOnly || busy} onDelivered={() => onRefresh()} /><Button variant="danger" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelCastCandidate(projectId, candidate.jobId))}>取消此任务</Button></>}
      {candidate.status === "ready" && <><CastEditor characters={castCharacters} disabled={readOnly || busy} onChange={updateDirection} /><Button variant="primary" disabled={readOnly || busy || !canConfirm} onClick={saveAccepted}>接受这份角色设定</Button></>}
    </>}
    {accepted && state.status === "reopened" && <><CastEditor characters={castCharacters} disabled={readOnly || busy} onChange={updateDirection} editing /><div className="button-row"><Button variant="primary" disabled={readOnly || busy || !canConfirm} onClick={() => canConfirm && act(() => plotloomApi.saveReopenedCast(projectId, { expectedCastRevision: accepted.revision, binding: accepted.binding, cast: editedCast, consumerMappings: accepted.consumerMappings }), undefined, true)}>保存角色修改</Button><Button variant="quiet" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelReopenedCast(projectId, accepted.revision), undefined, true, true)}>取消编辑</Button></div><small>取消会丢弃未保存的文本，并仅在上游上下文仍当前时恢复 r{accepted.revision} 的既有授权。</small></>}
    {assignment && <details className="cast-assignment"><summary>查看任务说明（手动方式）</summary><textarea readOnly rows={5} value={assignment} /></details>}
    {(error || loadError) && <ErrorNotice message={error || loadError} />}
  </article>;
}

function AcceptedCastSummary({ accepted, onEdit, disabled }: { accepted: AcceptedCastRevision; onEdit: () => void; disabled: boolean }) {
  const characters = charactersOf(accepted.cast);
return <section className="accepted-cast-summary"><div className="accepted-cast-summary-heading"><div><strong>当前角色</strong><small>这是可复用的已接受文本；图像选择在下方单独进行。</small></div><Button variant="primary" disabled={disabled} onClick={onEdit}>编辑角色设定</Button></div><div className="accepted-cast-grid">{characters.map((character, index) => <article key={String(character.id || index)}><h3>{String(character.name || character.id || `角色 ${index + 1}`)}</h3><dl><CastValue label="性格特点" value={Array.isArray(record(character.persona).personality) ? (record(character.persona).personality as string[]).map((value) => castTextPresentation(value).text).join("、") : undefined} /><CastValue label="气质与举止" value={castTextPresentation(record(character.persona).temperament).text} /><CastValue label="外观" value={castTextPresentation(record(character.persona).appearance).text} /><CastValue label="声音方向" value={castTextPresentation(record(character.voice).timbre).text} /><CastValue label="图像风格" value={record(character.image).style} /></dl><CastInferenceNotes character={character} /></article>)}</div><details className="cast-technical"><summary>查看版本与技术详情</summary><small>已接受版本 r{accepted.revision} · 内容标识 {accepted.contentHash} · 已保留既有角色映射。</small></details></section>;
}

function CastValue({ label, value }: { label: string; value: unknown }) { return <div><dt>{label}</dt><dd>{typeof value === "string" && value ? value : "未提供"}</dd></div>; }

function charactersOf(cast: Record<string, unknown>): Array<Record<string, unknown>> { return Array.isArray(cast.characters) ? cast.characters.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : []; }
function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function isCastState(value: unknown): value is CastReviewState { return typeof value === "object" && value !== null && "status" in value && "acceptedCast" in value; }
