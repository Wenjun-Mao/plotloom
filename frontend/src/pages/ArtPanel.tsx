import { useCallback, useEffect, useRef, useState } from "react";
import { AcceptedEvidenceNotice } from "./AcceptedEvidenceNotice";
import { plotloomApi } from "../api";
import { Button, Spinner } from "../components";
import type { AcceptedArtRevision, ArtCandidate, ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal, ArtRenderStyle, ArtReviewState } from "../types";
import { ArtReferenceGallery } from "./ArtReferenceGallery";
import { ArtReport } from "./ArtReport";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import { useReviewActivation } from "./useReviewActivation";
import { StageGuide } from "../components/StageGuide";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";
import { ReviewContextErrorNotice, ReviewContextNotice, reviewContextFailure, reviewContextNextStep, type ReviewContextFailure } from "./ReviewContextNotice";

type EditorProps = { disabled: boolean; draft: string; setDraft: (value: string) => void };
type ProjectSession = { projectId: string; epoch: number };
type ArtDraftAuthority = { kind: "candidate"; value: ArtCandidate } | { kind: "accepted"; value: AcceptedArtRevision };

function draftAuthority(state: ArtReviewState | undefined): ArtDraftAuthority | null {
  if (state?.candidate?.status === "ready") return { kind: "candidate", value: state.candidate };
  return state?.acceptedArt ? { kind: "accepted", value: state.acceptedArt } : null;
}

function authorityKey(authority: ArtDraftAuthority | null): string {
  if (!authority) return "";
  return authority.kind === "candidate" ? `candidate:${authority.value.jobId}` : `accepted:${authority.value.revision}:${authority.value.contentHash}`;
}

/** F3A owns text review; the distinct F3B study surface owns reference bytes. */
export function ArtPanel({ projectId, readOnly: ownerReadOnly, active = true, refreshToken, onContinue }: { projectId: string; readOnly: boolean; active?: boolean; refreshToken?: unknown; onContinue?: () => void }) {
  const [state, setState] = useState<ArtReviewState>();
  const [studies, setStudies] = useState<ArtReferenceProposal[]>([]);
  const [referenceDecisions, setReferenceDecisions] = useState<ArtReferenceDecision[]>([]);
  const [referenceStates, setReferenceStates] = useState<ArtReferenceDecisionState[]>([]);
  const [assignment, setAssignment] = useState("");
  const [draft, setDraft] = useState("");
  const [draftBase, setDraftBase] = useState<ArtDraftAuthority | null>(null);
  const draftDirty = useRef(false);
  const [renderStyle, setRenderStyle] = useState<ArtRenderStyle | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ReviewContextFailure>("");
  const activeProject = useRef<ProjectSession>({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) {
    activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  }
  const ownsProject = (session: ProjectSession) => activeProject.current === session;
  const load = useCallback(async (isCurrent: () => boolean) => {
    const session = activeProject.current;
    if (ownsProject(session)) setError("");
    try {
      const [next, referenceStudies, decisions] = await Promise.all([
        plotloomApi.getArt(session.projectId),
        plotloomApi.getArtReferenceProposals(session.projectId),
        plotloomApi.getArtReferenceDecisions(session.projectId),
      ]);
      if (ownsProject(session) && isCurrent()) { setState(next); setStudies(referenceStudies.proposals); setReferenceDecisions(decisions.decisions); setReferenceStates(decisions.states); return true; }
    } catch (reason) {
      if (ownsProject(session) && isCurrent()) setError(reviewContextFailure(reason, "无法读取美术参考。"));
    }
    return false;
  }, [projectId]);
  useEffect(() => {
    const session = activeProject.current;
    setState(undefined); setStudies([]); setReferenceDecisions([]); setReferenceStates([]); setAssignment(""); setDraft(""); setRenderStyle(""); setError(""); setBusy(false);
    setDraftBase(null); draftDirty.current = false;
    return () => {
      // An unmounted panel must not let an already-settled child operation
      // refresh through its captured parent callback. StrictMode immediately
      // installs a new epoch after this development cleanup.
      if (ownsProject(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 };
    };
  }, [projectId, load]);
  const { checking, failed, recheck } = useReviewActivation({ projectId, active, refreshToken, load });
  const readOnly = ownerReadOnly || checking || failed;
  const reviewDraft = useReviewEditorDraft(projectId, "art", authorityKey(draftAuthority(state)), text => {
    setDraftBase(draftAuthority(state)); draftDirty.current = true; setDraft(text);
  }, readOnly || busy, () => { draftDirty.current = false; const authority = draftAuthority(state); setDraftBase(authority); setDraft(authority?.value.art ? JSON.stringify(authority.value.art, null, 2) : ""); });
  useEffect(() => {
    // Refresh may invalidate draft authority, but only an explicit author
    // decision can discard dirty text or adopt another candidate/head.
    if (!draftDirty.current) {
      const authority = draftAuthority(state);
      setDraftBase(authority);
      if (authority?.value.art) setDraft(JSON.stringify(authority.value.art, null, 2));
    }
  }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedArt?.revision, state?.acceptedArt?.contentHash, state?.status]);
  const act = <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    void operation().then(async result => { if (ownsProject(session)) { onSuccess?.(result); await recheck(); } }).catch(reason => {
      if (ownsProject(session)) setError(reviewContextFailure(reason, "美术操作失败。"));
    }).finally(() => { if (ownsProject(session)) setBusy(false); });
  };
  const parsed = () => { try { return JSON.parse(draft) as Record<string, unknown>; } catch { setError("art.json 必须是有效 JSON。"); return undefined; } };
  if (!state) return <article id="art" className="panel cast-panel art-panel" data-testid="art-review">
    <header><span>美术参考</span><strong>{error ? "无法加载" : "正在加载"}</strong></header>
    {error ? <><ReviewContextErrorNotice error={error} projectId={projectId} /><Button variant="quiet" onClick={() => void recheck()}>重试加载美术参考</Button></> : <Spinner />}
  </article>;
  const { candidate, acceptedArt: accepted } = state;
  const currentAuthority = draftAuthority(state);
  const draftMatches = Boolean(draftBase && authorityKey(draftBase) === authorityKey(currentAuthority));
  const retained = Boolean(draftDirty.current && draftBase && (!draftMatches || state.status === "stale" || (draftBase.kind === "accepted" && state.status !== "reopened")));
  const editDraft = (next: string) => { draftDirty.current = next !== JSON.stringify(draftBase?.value.art, null, 2); setDraft(next); reviewDraft.changed(next); };
  const adoptCurrent = () => { draftDirty.current = false; setDraftBase(currentAuthority); setDraft(currentAuthority?.value.art ? JSON.stringify(currentAuthority.value.art, null, 2) : ""); void reviewDraft.clear(); };
  const heading = checking ? "正在刷新" : failed ? "无法刷新" : state.status === "stale" ? "上下文已过期" : state.status === "reopened" ? "美术设定修订轮次已打开" : candidate?.status === "ready" ? "待审核美术设定" : candidate?.status === "prepared" ? "美术任务尚未交付" : accepted ? `已确认美术设定 r${accepted.revision}` : "尚无美术候选";
  const prepare = () => { if (!renderStyle) return; const session = activeProject.current; setBusy(true); setError(""); void plotloomApi.prepareArtCandidate(session.projectId, renderStyle).then(async result => { if (ownsProject(session)) { setAssignment(result.assignment); await recheck(); } }).catch(reason => { if (ownsProject(session)) setError(reviewContextFailure(reason, "准备美术任务失败。")); }).finally(() => { if (ownsProject(session)) setBusy(false); }); };
  const accept = () => {
    if (!draftMatches || draftBase?.kind !== "candidate" || state.status === "stale") return;
    const art = parsed(); const base = draftBase.value;
    if (art) act(() => plotloomApi.acceptArtCandidate(projectId, { jobId: base.jobId, expectedArtRevision: base.expectedArtRevision, binding: base.binding, art }), () => { draftDirty.current = false; void reviewDraft.clear(); });
  };
  const save = () => {
    if (!draftMatches || draftBase?.kind !== "accepted" || state.status !== "reopened") { setError("草稿绑定已过期，请先明确舍弃草稿或采用当前版本。"); return; }
    const art = parsed(); const base = draftBase.value;
    if (art) act(() => plotloomApi.saveReopenedArt(projectId, { expectedArtRevision: base.revision, binding: base.binding, art }), () => { draftDirty.current = false; void reviewDraft.clear(); });
  };
  return <article id="art" className="panel cast-panel art-panel" data-testid="art-review">
    {reviewDraft.notice}
    <header><span>美术参考</span><strong>{heading}</strong></header>
    {failed && <Button variant="quiet" onClick={() => void recheck()}>重试加载美术参考</Button>}
    <p>先由文字创作助手整理地点和道具设定，供你审核。确认设定后，再为场景和道具制作参考图片。这一步不会生成图片。</p>
    <StageGuide next={onContinue && <Button variant="quiet" disabled={checking || failed || busy || draftDirty.current || state.acceptedReviewState.status !== "current" || !accepted} onClick={onContinue}>继续：剧本</Button>}>
      {checking ? "正在核对当前版本，请稍候。" : failed ? "读取失败，请先重试；暂时不能继续或修改。" : busy ? "正在处理美术任务，请稍候。" : retained ? "保留了基于旧版本的美术草稿。请在下方明确舍弃，或用当前版本替换草稿，再继续剧本。" : state.status === "reopened" || draftDirty.current ? "先保存或明确舍弃美术修改，再继续剧本。" : state.status === "stale" ? reviewContextNextStep(state.staleReasons[0], "请按当前审核要求重新准备并确认美术设定。") : state.status === "accepted" && accepted ? "地点与道具设定已确认。可按需制作参考图，也可继续编写剧本；进入下一步不会自动生成图片。" : "选择美术风格，准备并发送文字任务，再审核返回的地点与道具设定。"}
    </StageGuide>
    {(candidate?.binding.renderContract || accepted?.binding.renderContract) && <p>美术风格：{(candidate?.binding.renderContract || accepted?.binding.renderContract)?.preset.label}</p>}
    <ReviewContextNotice projectId={projectId} diagnostics={state.staleReasons} />
    {state.candidate && <AcceptedEvidenceNotice projectId={projectId} state={state.acceptedReviewState} />}
    {!candidate && state.status !== "reopened" && <section aria-label="准备美术设定候选">
      {accepted && <><h3>{state.status === "stale" ? "重新准备并确认美术设定" : "准备新的美术候选（可选）"}</h3><p>已确认的美术设定 r{accepted.revision} 仍保留在下方。新候选需要单独审核并确认，不会自动替换已有设定。</p></>}
      <label>美术风格 *<select aria-label="美术风格" required value={renderStyle} disabled={readOnly || busy} onChange={event => setRenderStyle(event.target.value as ArtRenderStyle | "")}><option value="">请选择风格</option><option value="live-action">真人写实</option><option value="realistic">半写实厚涂</option><option value="ghibli">吉卜力动画</option></select></label><p>此选择用于新的美术任务，不会修改已确认的角色设定或图片。</p><Button variant="primary" disabled={readOnly || busy || !renderStyle} onClick={prepare}>准备美术设定任务</Button>
    </section>}
    {candidate?.status === "prepared" && state.status !== "stale" && <SpecialistTaskActions projectId={projectId} stage="art" jobId={candidate.jobId} disabled={readOnly || busy} onDelivered={recheck} />}
    {candidate && <CandidateReview candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} stale={state.status === "stale" || !draftMatches} draft={draft} setDraft={editDraft} cancel={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))} accept={accept} />}
    {accepted && <><details><summary>查看美术版本标识</summary><code>修订版 r{accepted.revision} · sha256:{accepted.contentHash}</code></details><p>文本与原始报告可在这里审阅；参考图片在下方单独显示。</p><ArtReferenceGallery projectId={projectId} art={accepted.art} acceptedRevision={accepted.revision} acceptedContentHash={accepted.contentHash} acceptedArtCurrent={state.acceptedReviewState.status === "current"} studies={studies} decisions={referenceDecisions} decisionStates={referenceStates} readOnly={readOnly} busy={busy} setAssignment={setAssignment} refresh={recheck} />{accepted.candidateJobId && <ArtReport key={`${projectId}:${accepted.candidateJobId}`} projectId={projectId} jobId={accepted.candidateJobId} />}{state.status !== "reopened" && <Editor disabled draft={JSON.stringify(accepted.art, null, 2)} setDraft={editDraft} />}<Button variant="quiet" disabled={readOnly || busy || state.acceptedReviewState.status !== "current"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
    {accepted && state.status === "reopened" && !retained && <><Editor disabled={readOnly || busy} draft={draft} setDraft={editDraft} /><Button variant="primary" disabled={readOnly || busy || !draftMatches} onClick={save}>保存重新打开的美术</Button></>}
    {retained && draftBase && <section aria-label="保留的未保存美术草稿">
      <p>保留的未保存美术草稿基于{draftBase.kind === "accepted" ? `美术 r${draftBase.value.revision}` : "原候选"}。当前上下文已变化，保存已停用；原草稿不会自动替换为新版本。</p>
      <textarea aria-label="保留的美术草稿" className="source-outline-json" rows={12} readOnly value={draft} />
      <Button disabled>保存重新打开的美术</Button>
      <Button disabled={ownerReadOnly || busy || checking} onClick={adoptCurrent}>舍弃美术草稿</Button>
      <Button disabled={readOnly || busy || !currentAuthority} onClick={adoptCurrent}>用当前版本替换草稿</Button>
    </section>}
    {(candidate?.status === "prepared" || assignment) && <details><summary>查看任务说明（手动方式）</summary>{candidate?.status === "prepared" && <Button disabled={readOnly || busy} onClick={() => act(() => plotloomApi.recoverArtHandoff(projectId, candidate.jobId), result => setAssignment(result.assignment))}>查看美术任务说明</Button>}{assignment && <textarea aria-label="美术任务说明" readOnly value={assignment} rows={5} />}</details>}
    {error && <ReviewContextErrorNotice error={error} projectId={projectId} />}
  </article>;
}

function CandidateReview({ candidate, projectId, readOnly, busy, stale, draft, setDraft, cancel, accept }: { candidate: ArtCandidate; projectId: string; readOnly: boolean; busy: boolean; stale: boolean; draft: string; setDraft: (value: string) => void; cancel: () => void; accept: () => void }) {
  return <><small>绑定来源 r{candidate.binding.sourceRevision} · 角色 r{candidate.binding.castRevision} · 章节 {candidate.binding.sectionIds.join(" · ")}</small>
    {candidate.status === "prepared" && <Button variant="danger" disabled={readOnly || busy} onClick={cancel}>取消此任务</Button>}
    {candidate.status === "ready" && <>{candidate.reportAvailable && <ArtReport key={`${projectId}:${candidate.jobId}`} projectId={projectId} jobId={candidate.jobId} />}<Editor disabled={readOnly || busy || stale} draft={draft} setDraft={setDraft} /><Button variant="primary" disabled={readOnly || busy || stale} onClick={accept}>确认使用此美术提案</Button><Button variant="danger" disabled={readOnly || busy} onClick={cancel}>拒绝并取消此美术提案</Button></>}
  </>;
}

function Editor({ disabled, draft, setDraft }: EditorProps) {
  return <details className="art-json-editor"><summary>查看/编辑 art.json（稳定地点和道具 ID 不可替换）</summary><textarea className="source-outline-json" disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} rows={24} /></details>;
}
