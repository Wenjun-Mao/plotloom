import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../../api";
import { Button, ErrorNotice, Field } from "../../../components";
import type { ApprovalDecision } from "../../../types";
import type { ProjectDraftQuiescence } from "../../authoring/projectDraftQuiescence";
import { physicalFields, type LiteralSource, type MessagePresentation, type PhysicalPresentation, type ShotPresentationState } from "./shot-presentation";

const labels: Record<keyof PhysicalPresentation, string> = {
  action: "实际动作", composition: "构图与首帧", visualIntent: "视觉意图", motionIntent: "动态意图", cameraMovement: "镜头运动",
};
const pointerKey = (source: LiteralSource) => `${source.shotId}:${source.index}`;
type ReviewDraft = { physical: PhysicalPresentation; literalSources: LiteralSource[]; messagePresentation: MessagePresentation; reason: string };
function initialDraft(state: ShotPresentationState, shotId: string): ReviewDraft {
  return { physical: physicalFields(state.decision?.effectiveShot ?? state.source.shot),
    literalSources: state.decision?.review.literalSources ?? state.source.literalOptions.filter(item => item.shotId === shotId).map(({ shotId, index }) => ({ shotId, index })),
    messagePresentation: state.decision?.review.messagePresentation ?? "source", reason: state.decision?.review.reason ?? "" };
}

export function ShotPresentationReview({ projectId, shotId, approval, storyboardRevision, readOnly, onLoaded, onSaved, quiescence }: {
  projectId: string; shotId: string; approval?: ApprovalDecision; storyboardRevision?: number;
  readOnly: boolean; onLoaded: (revision: number) => void; onSaved: () => Promise<void>;
  quiescence?: ProjectDraftQuiescence;
}) {
  const [state, setState] = useState<ShotPresentationState>();
  const [physical, setPhysical] = useState<PhysicalPresentation>();
  const [literals, setLiterals] = useState<LiteralSource[]>([]);
  const [mode, setMode] = useState<MessagePresentation>("source");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draftStale, setDraftStale] = useState(false);
  const [bufferFailed, setBufferFailed] = useState(false);
  const stamp = useRef<{ sourceHash: string; revision: number } | undefined>(undefined);
  const storageKey = `plotloom:shot-presentation:${projectId}:${shotId}`;
  const applyDraft = (draft: ReviewDraft) => {
    setPhysical(draft.physical); setLiterals(draft.literalSources); setMode(draft.messagePresentation); setReason(draft.reason); setConfirmed(false);
  };
  useEffect(() => {
    let cancelled = false;
    setState(undefined); setPhysical(undefined); setConfirmed(false); setError("");
    void plotloomApi.getShotPresentation(projectId, shotId).then(next => {
      if (cancelled) return;
      setState(next); onLoaded(next.revision);
      stamp.current = { sourceHash: next.source.sourceHash, revision: next.revision };
      let draft = initialDraft(next, shotId);
      try {
        const saved = window.sessionStorage.getItem(storageKey);
        const cache = saved ? JSON.parse(saved) as { sourceHash: string; revision: number; draft: ReviewDraft } : undefined;
        if (cache && cache.draft && Object.keys(labels).every(field => typeof cache.draft.physical?.[field as keyof PhysicalPresentation] === "string") &&
          Array.isArray(cache.draft.literalSources) && cache.draft.literalSources.every(item => typeof item.shotId === "string" && Number.isInteger(item.index)) &&
          ["source", "popped_out_draft", "popped_out_send"].includes(cache.draft.messagePresentation) && typeof cache.draft.reason === "string") {
          draft = cache.draft; stamp.current = { sourceHash: cache.sourceHash, revision: cache.revision };
          setDraftStale(cache.sourceHash !== next.source.sourceHash || cache.revision !== next.revision);
        }
      } catch { setBufferFailed(true); }
      applyDraft(draft);
    }).catch(error => { if (!cancelled) setError(error instanceof Error ? error.message : "无法读取镜头呈现"); });
    return () => { cancelled = true; };
  }, [projectId, shotId]);
  const draft = physical ? { physical, literalSources: literals, messagePresentation: mode, reason } : undefined;
  const fingerprint = JSON.stringify(draft);
  const dirty = !!state && !!draft && (draftStale || fingerprint !== JSON.stringify(initialDraft(state, shotId)));
  useEffect(() => {
    if (!state || !draft || !stamp.current) return;
    try {
      if (dirty) window.sessionStorage.setItem(storageKey, JSON.stringify({ ...stamp.current, draft }));
      else window.sessionStorage.removeItem(storageKey);
      setBufferFailed(false);
    } catch { setBufferFailed(true); }
  }, [dirty, fingerprint, state, storageKey]);
  useEffect(() => {
    if (!quiescence) return;
    return quiescence.register(projectId, `shot_presentation:${shotId}`, async () => !dirty && !busy, { retainOnUnmount: dirty || busy });
  }, [quiescence, projectId, shotId, dirty, busy]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const valid = !!state && !!physical && !!approval && !!storyboardRevision && !draftStale && reason.trim() &&
    physical.action.trim() && physical.composition.trim() && physical.cameraMovement.trim() && (mode === "source" || literals.length > 0);
  const save = async () => {
    if (!state || !physical || !approval || !storyboardRevision || !confirmed || !valid) return;
    setBusy(true); setError("");
    try {
      const next = await plotloomApi.reviewShotPresentation(projectId, shotId, {
        expectedRevision: state.revision, sourceHash: state.source.sourceHash,
        approvalId: approval.id, storyboardRevision, physical, literalSources: literals,
        messagePresentation: mode, reason, reviewed: true,
      });
      stamp.current = { sourceHash: next.source.sourceHash, revision: next.revision };
      setState(next); setConfirmed(false); setDraftStale(false); onLoaded(next.revision); await onSaved();
    } catch (error) { setError(error instanceof Error ? error.message : "呈现审阅保存失败"); }
    finally { setBusy(false); }
  };
  return <details className="workbench-support" data-testid="shot-presentation-review"><summary>镜头呈现调整{state?.decision ? ` · r${state.revision}` : ""}</summary>
    <p>保留原始剧本与已批准分镜。这里明确审阅此镜头的画面调整；保存后重新审核其关键帧，其他镜头不受影响。</p>
    {state && physical && <fieldset disabled={readOnly || busy}>
      {!state.current && <p role="alert">来源已有变化，请重新核对后保存。</p>}
      {draftStale && <p role="alert">保留的草稿基于较早来源或呈现版本，不能直接保存。请检查后载入当前呈现。</p>}
      {bufferFailed && <p role="alert">会话草稿暂时无法保存，请保持本页打开并保存审阅。</p>}
      {dirty && <Button variant="quiet" onClick={() => { stamp.current = { sourceHash: state.source.sourceHash, revision: state.revision }; setDraftStale(false); applyDraft(initialDraft(state, shotId)); }}>放弃草稿，载入当前呈现</Button>}
      <details><summary>原始动作与构图</summary><blockquote>{state.source.shot.action}</blockquote><blockquote>{state.source.shot.composition}</blockquote></details>
      {(Object.keys(labels) as Array<keyof PhysicalPresentation>).map(field => <Field key={field} label={labels[field]}>
        <textarea aria-label={`呈现调整 ${labels[field]}`} value={physical[field]} onChange={event => { setPhysical({ ...physical, [field]: event.target.value }); setConfirmed(false); }} />
      </Field>)}
      <Field label="消息呈现"><select aria-label="消息呈现" value={mode} onChange={event => { setMode(event.target.value as MessagePresentation); setConfirmed(false); }}>
        <option value="source">保持来源中的呈现</option><option value="popped_out_draft">弹出预览：完整未发送草稿，正在撰写或检查</option><option value="popped_out_send">弹出预览：独立发送动作与清楚的已发送状态</option>
      </select></Field>
      {mode !== "source" && <p>首帧已显示完整未发送文字；手机上不生成可读文字。草稿镜头不发送，发送镜头必须表现发送和已发送状态。</p>}
      <strong>准确画面文字（从本镜头或紧邻前镜头选择）</strong>
      {state.source.literalOptions.map(option => <label key={pointerKey(option)}><input type="checkbox" checked={literals.some(item => pointerKey(item) === pointerKey(option))} onChange={event => {
        setLiterals(event.target.checked ? [...literals, { shotId: option.shotId, index: option.index }] : literals.filter(item => pointerKey(item) !== pointerKey(option))); setConfirmed(false);
      }} />{option.text} · {option.shotId}<small>来源 {option.sourceContentHash.slice(0, 12)}</small></label>)}
      <Field label="调整理由"><textarea aria-label="呈现调整理由" value={reason} onChange={event => { setReason(event.target.value); setConfirmed(false); }} /></Field>
      <label><input type="checkbox" checked={confirmed} disabled={!valid} onChange={event => setConfirmed(event.target.checked)} />我已核对来源与调整：故事含义保留，文字准确且不发声，草稿与发送状态明确。</label>
      <Button disabled={!valid || !confirmed || busy} onClick={() => void save()}>保存此镜头的呈现审阅</Button>
    </fieldset>}
    {error && <ErrorNotice message={error} />}
  </details>;
}
