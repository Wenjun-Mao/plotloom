import { useEffect, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { AcceptedCastRevision, CastReviewState } from "../types";
import { CastEditor, type CastDirectionChange } from "./CastEditor";
import { CastInferenceNotes } from "./CastInferenceNotes";
import { castTextPresentation } from "./cast-text-presentation";
import { hasValidCastDesign } from "./cast-design-validation";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";

type CastPanelProps = {
  projectId: string; readOnly: boolean; state: CastReviewState | undefined; loadError: string;
  onState: (state: CastReviewState) => void; onRefresh: (expectedOwner?: number) => Promise<boolean>;
  onInvalidate: () => void; onTransitionComplete: () => void;
};

export function CastPanel({ projectId, readOnly: ownerReadOnly, state, loadError, onState, onRefresh, onInvalidate, onTransitionComplete }: CastPanelProps) {
  const ownerDisabled = ownerReadOnly || Boolean(loadError);
  const [assignment, setAssignment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editedCast, setEditedCast] = useState<Record<string, unknown>>({});
  const draftDirty = useRef(false);
  const draftBasis = useRef("");
  useEffect(() => { draftDirty.current = false; setEditedCast({}); }, [projectId]);
  const basis = state?.candidate?.status === "ready" ? `cast:${state.candidate.jobId}` : state?.acceptedCast ? `cast:${state.acceptedCast.revision}:${state.acceptedCast.contentHash}:${state.status}` : "";
  const reviewDraft = useReviewEditorDraft(projectId, "cast", basis, text => {
    const recovered = JSON.parse(text) as Record<string, unknown>;
    if (!Array.isArray(recovered?.characters)) throw new Error("角色草稿格式无效，请复制内容后重新填写。");
    draftDirty.current = true; draftBasis.current = basis; setEditedCast(recovered);
  }, ownerDisabled || busy, () => { draftDirty.current = false; draftBasis.current = ""; setEditedCast(structuredClone(state?.candidate?.cast ?? state?.acceptedCast?.cast ?? {})); });
  const readOnly = ownerDisabled || reviewDraft.stale;
  const operationOwner = useRef(0); const active = useRef(true); const projectRef = useRef(projectId);
  projectRef.current = projectId;
  useEffect(() => { active.current = true; return () => { active.current = false; operationOwner.current += 1; }; }, []);
  useEffect(() => {
    const editable = state?.candidate?.status === "ready" ? state.candidate.cast : state?.status === "reopened" ? state.acceptedCast?.cast : undefined;
    if (editable && (!draftDirty.current || (!reviewDraft.stale && draftBasis.current !== basis))) {
      draftDirty.current = false; draftBasis.current = basis; setEditedCast(structuredClone(editable));
    }
  }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedCast?.revision, state?.status, basis, reviewDraft.stale]);

  const isCurrent = (capturedProject: string, capturedOwner: number) => active.current && projectRef.current === capturedProject && operationOwner.current === capturedOwner;
  const act = <T,>(operation: () => Promise<T>, applyResult?: (result: T) => void, invalidatesSession = false, refreshAfterFailure = false) => {
    const capturedProject = projectRef.current; const capturedOwner = ++operationOwner.current;
    if (invalidatesSession) onInvalidate();
    setBusy(true); setError("");
    void operation().then(async (result) => {
      if (!isCurrent(capturedProject, capturedOwner)) return;
      if (isCastState(result)) { if (result.status === "accepted") { draftDirty.current = false; await reviewDraft.clear(); } onState(result); }
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
  if (!state) return <article className="panel cast-panel" data-testid="cast-review">
    <header><span>角色设定</span><strong>{loadError ? "无法读取角色设定" : "正在读取角色设定"}</strong></header>
    {loadError ? <><ErrorNotice message={loadError} /><Button variant="quiet" onClick={() => void onRefresh()}>重试加载角色设定</Button></> : <Spinner label="正在读取角色设定" />}
  </article>;

  const candidate = state.candidate; const accepted = state.acceptedCast;
  const taskLabel = loadError ? "无法刷新角色设定" : state.status === "stale" ? "上下文已过期" : state.status === "reopened" ? "角色设定正在编辑" : candidate?.status === "ready" ? "待审核角色设定" : candidate?.status === "prepared" ? "角色任务已准备" : accepted ? `已接受角色设定 r${accepted.revision}` : "尚无角色提案";
  const castCharacters = charactersOf(editedCast);
  const canConfirm = hasValidCastDesign(castCharacters);
  const updateDirection: CastDirectionChange = (index, group, key, value) => {
    const next = { ...editedCast, characters: charactersOf(editedCast).map((character, candidateIndex) => candidateIndex === index ? { ...character, [group]: { ...(group === "reviewNotes" ? { sourceNotes: "", performanceGuidance: "" } : {}), ...record(character[group]), [key]: value } } : character) };
    draftDirty.current = true; draftBasis.current = basis; setEditedCast(next); reviewDraft.changed(JSON.stringify(next));
  };
  const saveAccepted = () => canConfirm && state.status !== "stale" && act(() => plotloomApi.acceptCastCandidate(projectId, {
    jobId: candidate!.jobId, expectedCastRevision: candidate!.expectedCastRevision, binding: candidate!.binding, cast: editedCast,
    consumerMappings: castCharacters.map((character) => ({ castCharacterId: String(character.id), consumerCharacterId: String(character.id) })),
  }), undefined, true);

  return <article className="panel cast-panel" data-testid="cast-review">
    {reviewDraft.notice}
    <header className="cast-panel-heading"><div><span className="eyebrow">角色设定</span><h2>{taskLabel}</h2></div><span className={`reference-state ${state.status === "stale" ? "historical" : state.status === "accepted" ? "selected" : "candidate"}`}>{loadError ? "无法刷新" : state.status === "stale" ? "需更新" : state.status === "accepted" ? "已确认" : state.status === "reopened" ? "编辑中" : candidate?.status === "ready" ? "待审核" : candidate?.status === "prepared" ? "待发送" : "待准备"}</span></header>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {accepted && <AcceptedCastSummary accepted={accepted} current={!loadError && state.status === "accepted"} onEdit={() => act(() => plotloomApi.reopenCast(projectId, accepted.revision), undefined, true)} disabled={readOnly || busy || state.status === "reopened"} />}
    {!candidate && state.status !== "reopened" && <section className="cast-next-action"><div><strong>创建新角色提案</strong><small>先准备任务，再发送给文字创作助手。结果需要你审核确认。</small></div><Button variant="quiet" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.prepareCastCandidate(projectId), (result) => setAssignment(result.assignment))}>创建新角色提案</Button></section>}
    {candidate && <>
      <details className="cast-technical"><summary>查看提案来源与技术详情</summary><small>冻结来源与章节：r{candidate.binding.sourceRevision} · r{candidate.binding.outlineRevision} · {candidate.binding.sectionIds.join(" · ")}</small>{candidate.status === "ready" && <><pre>{JSON.stringify(candidate.cast, null, 2)}</pre>{candidate.reportAvailable && <iframe title="只读上游角色报告" className="source-outline-report" sandbox="" src={plotloomApi.castCandidateReportUrl(projectId, candidate.jobId)} />}</>}</details>
      {candidate.status === "prepared" && <><SpecialistTaskActions projectId={projectId} stage="characters" jobId={candidate.jobId} disabled={readOnly || busy} sendDisabled={state.status === "stale"} onDelivered={() => onRefresh()} /><Button variant="danger" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelCastCandidate(projectId, candidate.jobId))}>取消此任务</Button></>}
      {candidate.status === "ready" && <><CastEditor characters={castCharacters} disabled={readOnly || busy || state.status === "stale"} onChange={updateDirection} /><Button variant="primary" disabled={readOnly || busy || state.status === "stale" || !canConfirm} onClick={saveAccepted}>接受这份角色设定</Button></>}
    </>}
    {accepted && state.status === "reopened" && <><CastEditor characters={castCharacters} disabled={readOnly || busy} onChange={updateDirection} editing /><div className="button-row"><Button variant="primary" disabled={readOnly || busy || !canConfirm} onClick={() => canConfirm && act(() => plotloomApi.saveReopenedCast(projectId, { expectedCastRevision: accepted.revision, binding: accepted.binding, cast: editedCast, consumerMappings: accepted.consumerMappings }), undefined, true)}>保存角色修改</Button><Button variant="quiet" disabled={readOnly || busy} onClick={() => act(() => plotloomApi.cancelReopenedCast(projectId, accepted.revision), undefined, true, true)}>取消编辑</Button></div><small>取消会丢弃未保存的文本，并仅在上游上下文仍当前时恢复 r{accepted.revision} 的既有授权。</small></>}
    {assignment && <details className="cast-assignment"><summary>查看任务说明（手动方式）</summary><textarea readOnly rows={5} value={assignment} /></details>}
    {(error || loadError) && <ErrorNotice message={error || loadError} />}
    {loadError && <Button variant="quiet" onClick={() => void onRefresh()}>重试加载角色设定</Button>}
  </article>;
}

function AcceptedCastSummary({ accepted, current, onEdit, disabled }: { accepted: AcceptedCastRevision; current: boolean; onEdit: () => void; disabled: boolean }) {
  const characters = charactersOf(accepted.cast);
return <section className="accepted-cast-summary"><div className="accepted-cast-summary-heading"><div><strong>{current ? "当前角色" : "保留的已接受角色"}</strong><small>{current ? "这是可复用的已接受文本；图像选择在下方单独进行。" : "旧版本仍可查看；请先处理当前任务，不能把保留结果当作本次已确认。"}</small></div><Button variant="primary" disabled={disabled} onClick={onEdit}>编辑角色设定</Button></div><div className="accepted-cast-grid">{characters.map((character, index) => <article key={String(character.id || index)}><h3>{String(character.name || character.id || `角色 ${index + 1}`)}</h3><dl><CastValue label="性格特点" value={Array.isArray(record(character.persona).personality) ? (record(character.persona).personality as string[]).map((value) => castTextPresentation(value).text).join("、") : undefined} /><CastValue label="气质与举止" value={castTextPresentation(record(character.persona).temperament).text} /><CastValue label="外观" value={castTextPresentation(record(character.persona).appearance).text} /><CastValue label="声音方向" value={castTextPresentation(record(character.voice).timbre).text} /><CastValue label="图像风格" value={record(character.image).style} /></dl><CastInferenceNotes character={character} /></article>)}</div><details className="cast-technical"><summary>查看版本与技术详情</summary><small>已接受版本 r{accepted.revision} · 内容标识 {accepted.contentHash} · 已保留既有角色映射。</small></details></section>;
}

function CastValue({ label, value }: { label: string; value: unknown }) { return <div><dt>{label}</dt><dd>{typeof value === "string" && value ? value : "未提供"}</dd></div>; }

function charactersOf(cast: Record<string, unknown>): Array<Record<string, unknown>> { return Array.isArray(cast.characters) ? cast.characters.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : []; }
function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function isCastState(value: unknown): value is CastReviewState { return typeof value === "object" && value !== null && "status" in value && "acceptedCast" in value; }
