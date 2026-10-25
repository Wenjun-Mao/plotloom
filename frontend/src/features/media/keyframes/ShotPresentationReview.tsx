import { useReviewEditorDraft } from "../../authoring/ReviewDraftContext";
import { useEffect, useState } from "react";
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
  const applyDraft = (draft: ReviewDraft) => {
    setPhysical(draft.physical); setLiterals(draft.literalSources); setMode(draft.messagePresentation); setReason(draft.reason); setConfirmed(false);
  };
  useEffect(() => {
    let cancelled = false;
    setState(undefined); setPhysical(undefined); setConfirmed(false); setError("");
    void plotloomApi.getShotPresentation(projectId, shotId).then(next => {
      if (cancelled) return;
      setState(next); onLoaded(next.revision);
      const draft = initialDraft(next, shotId);
      applyDraft(draft);
    }).catch(error => { if (!cancelled) setError(error instanceof Error ? error.message : "无法读取镜头呈现"); });
    return () => { cancelled = true; };
  }, [projectId, shotId]);
  const draft = physical ? { physical, literalSources: literals, messagePresentation: mode, reason } : undefined;
  const fingerprint = JSON.stringify(draft);
  const dirty = !!state && !!draft && fingerprint !== JSON.stringify(initialDraft(state, shotId));
  const working = useReviewEditorDraft(projectId, "shot_presentation", state ? `shot:${state.source.sourceHash}:${state.revision}` : "", text => {
    const restored = JSON.parse(text) as ReviewDraft;
    if (!restored || !Object.keys(labels).every(field => typeof restored.physical?.[field as keyof PhysicalPresentation] === "string")
      || !Array.isArray(restored.literalSources) || typeof restored.reason !== "string") throw new Error("镜头呈现草稿格式无法匹配。");
    applyDraft(restored);
  }, readOnly || busy, undefined, shotId);
  useEffect(() => {
    if (dirty && draft) working.changed(JSON.stringify(draft));
  }, [dirty, fingerprint, state?.source.sourceHash, state?.revision]);
  const valid = !!state && !!physical && !!approval && !!storyboardRevision && !working.stale && reason.trim() &&
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
      const retired = await working.clear();
      if (!retired) setError("呈现修改已应用；工作输入的清理尚未核实，请保留或复制当前内容。");
      setState(next); setConfirmed(false);  onLoaded(next.revision); await onSaved();
    } catch (error) { setError(error instanceof Error ? error.message : "呈现审阅保存失败"); }
    finally { setBusy(false); }
  };
  return <details className="workbench-support" data-testid="shot-presentation-review"><summary>镜头呈现调整{state?.decision ? ` · r${state.revision}` : ""}</summary>
    <p>保留原始剧本与已批准分镜。这里明确审阅此镜头的画面调整；保存后重新审核其关键帧，其他镜头不受影响。</p>
    {state && physical && <fieldset disabled={readOnly || working.stale || busy}>
      {!state.current && <p role="alert">来源已有变化，请重新核对后保存。</p>}
      {dirty && <Button variant="quiet" onClick={() => void working.clear().then(cleared => { if (cleared) applyDraft(initialDraft(state, shotId)); })}>放弃草稿，载入当前呈现</Button>}
      <details><summary>原始动作与构图</summary><blockquote>{state.source.shot.action}</blockquote><blockquote>{state.source.shot.composition}</blockquote></details>
      {(Object.keys(labels) as Array<keyof PhysicalPresentation>).map(field => <Field key={field} label={labels[field]} required={["action", "composition", "cameraMovement"].includes(field)}>
        <textarea aria-required={["action", "composition", "cameraMovement"].includes(field) || undefined} aria-label={`呈现调整 ${labels[field]}`} value={physical[field]} onChange={event => { setPhysical({ ...physical, [field]: event.target.value }); setConfirmed(false); }} />
      </Field>)}
      <Field label="消息呈现"><select aria-label="消息呈现" value={mode} onChange={event => { setMode(event.target.value as MessagePresentation); setConfirmed(false); }}>
        <option value="source">保持来源中的呈现</option><option value="popped_out_draft">弹出预览：完整未发送草稿，正在撰写或检查</option><option value="popped_out_send">弹出预览：独立发送动作与清楚的已发送状态</option>
      </select></Field>
      {mode !== "source" && <p>首帧已显示完整未发送文字；手机上不生成可读文字。草稿镜头不发送，发送镜头必须表现发送和已发送状态。</p>}
      <strong>准确画面文字（从本镜头或紧邻前镜头选择）</strong>
      {state.source.literalOptions.map(option => <label key={pointerKey(option)}><input type="checkbox" checked={literals.some(item => pointerKey(item) === pointerKey(option))} onChange={event => {
        setLiterals(event.target.checked ? [...literals, { shotId: option.shotId, index: option.index }] : literals.filter(item => pointerKey(item) !== pointerKey(option))); setConfirmed(false);
      }} />{option.text} · {option.shotId}<small>来源 {option.sourceContentHash.slice(0, 12)}</small></label>)}
      <Field label="调整理由" required><textarea aria-required="true" aria-label="呈现调整理由" value={reason} onChange={event => { setReason(event.target.value); setConfirmed(false); }} /></Field>
      <label><input type="checkbox" checked={confirmed} disabled={!valid} onChange={event => setConfirmed(event.target.checked)} />我已核对来源与调整：故事含义保留，文字准确且不发声，草稿与发送状态明确。</label>
      <Button disabled={!valid || !confirmed || busy} onClick={() => void save()}>保存此镜头的呈现审阅</Button>
    </fieldset>}
    {working.notice}{error && <ErrorNotice message={error} />}
  </details>;
}
