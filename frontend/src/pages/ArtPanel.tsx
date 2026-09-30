import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ArtCandidate, ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal, ArtRenderStyle, ArtReviewState } from "../types";
import { ArtReferenceGallery } from "./ArtReferenceGallery";
import { ArtReport } from "./ArtReport";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";

type EditorProps = { disabled: boolean; draft: string; setDraft: (value: string) => void };
type ProjectSession = { projectId: string; epoch: number };

/** F3A owns text review; the distinct F3B study surface owns reference bytes. */
export function ArtPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ArtReviewState>();
  const [studies, setStudies] = useState<ArtReferenceProposal[]>([]);
  const [referenceDecisions, setReferenceDecisions] = useState<ArtReferenceDecision[]>([]);
  const [referenceStates, setReferenceStates] = useState<ArtReferenceDecisionState[]>([]);
  const [assignment, setAssignment] = useState("");
  const [draft, setDraft] = useState("");
  const [renderStyle, setRenderStyle] = useState<ArtRenderStyle | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeProject = useRef<ProjectSession>({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) {
    activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  }
  const ownsProject = (session: ProjectSession) => activeProject.current === session;
  const load = useCallback(async (session = activeProject.current) => {
    if (ownsProject(session)) setError("");
    try {
      const [next, referenceStudies, decisions] = await Promise.all([
        plotloomApi.getArt(session.projectId),
        plotloomApi.getArtReferenceProposals(session.projectId),
        plotloomApi.getArtReferenceDecisions(session.projectId),
      ]);
      if (ownsProject(session)) { setState(next); setStudies(referenceStudies.proposals); setReferenceDecisions(decisions.decisions); setReferenceStates(decisions.states); }
    } catch (reason) {
      if (ownsProject(session)) setError(reason instanceof Error ? reason.message : "Unable to load art studies.");
    }
  }, [projectId]);
  useEffect(() => {
    const session = activeProject.current;
    setState(undefined); setStudies([]); setReferenceDecisions([]); setReferenceStates([]); setAssignment(""); setDraft(""); setRenderStyle(""); setError(""); setBusy(false);
    void load(session);
    return () => {
      // An unmounted panel must not let an already-settled child operation
      // refresh through its captured parent callback. StrictMode immediately
      // installs a new epoch after this development cleanup.
      if (ownsProject(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 };
    };
  }, [projectId, load]);
  useEffect(() => {
    // The accepted revision is the current project-owned record. Reopen changes
    // only whether it is editable; it must never be the sole way to inspect it.
    const art = state?.candidate?.status === "ready" ? state.candidate.art : state?.acceptedArt?.art;
    if (art) setDraft(JSON.stringify(art, null, 2));
  }, [state?.candidate?.jobId, state?.candidate?.status, state?.acceptedArt?.revision, state?.status]);
  const act = <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    void operation().then(async result => { if (ownsProject(session)) { onSuccess?.(result); await load(session); } }).catch(reason => {
      if (ownsProject(session)) setError(reason instanceof Error ? reason.message : "Art operation failed.");
    }).finally(() => { if (ownsProject(session)) setBusy(false); });
  };
  const parsed = () => { try { return JSON.parse(draft) as Record<string, unknown>; } catch { setError("art.json 必须是有效 JSON。"); return undefined; } };
  if (!state) return <article id="art" className="panel cast-panel art-panel" data-testid="art-review">
    <header><span>美术参考</span><strong>{error ? "无法加载" : "正在加载"}</strong></header>
    {error ? <><ErrorNotice message={error} /><Button variant="quiet" onClick={() => void load()}>重试加载美术参考</Button></> : <Spinner />}
  </article>;
  const { candidate, acceptedArt: accepted } = state;
  const heading = state.status === "stale" ? "上下文已过期" : accepted ? `已接受 r${accepted.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "美术任务已准备" : "尚无美术候选";
  const prepare = () => { if (!renderStyle) return; const session = activeProject.current; setBusy(true); setError(""); void plotloomApi.prepareArtCandidate(session.projectId, renderStyle).then(async result => { if (ownsProject(session)) { setAssignment(result.assignment); await load(session); } }).catch(reason => { if (ownsProject(session)) setError(reason instanceof Error ? reason.message : "Art preparation failed."); }).finally(() => { if (ownsProject(session)) setBusy(false); }); };
  const accept = () => { const art = parsed(); if (art && candidate) act(() => plotloomApi.acceptArtCandidate(projectId, { jobId: candidate.jobId, expectedArtRevision: candidate.expectedArtRevision, binding: candidate.binding, art })); };
  const save = () => { const art = parsed(); if (art && accepted) act(() => plotloomApi.saveReopenedArt(projectId, { expectedArtRevision: accepted.revision, binding: accepted.binding, art })); };
  return <article id="art" className="panel cast-panel art-panel" data-testid="art-review">
    <header><span>美术参考</span><strong>{heading}</strong></header>
    <p>先由文字创作助手整理地点和道具设定，供你审核。确认设定后，再为场景和道具制作参考图片。这一步不会生成图片。</p>
    {(candidate?.binding.renderContract || accepted?.binding.renderContract) && <p>美术风格：{(candidate?.binding.renderContract || accepted?.binding.renderContract)?.preset.label}</p>}
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <><label>美术风格 *<select aria-label="美术风格" required value={renderStyle} disabled={readOnly || busy} onChange={event => setRenderStyle(event.target.value as ArtRenderStyle | "")}><option value="">请选择风格</option><option value="live-action">真人写实</option><option value="realistic">半写实厚涂</option><option value="ghibli">吉卜力动画</option></select></label><p>此选择用于新的美术任务，不会修改已接受的角色设定或图片。</p><Button variant="primary" disabled={readOnly || busy || !renderStyle} onClick={prepare}>准备美术设定任务</Button></>}
    {candidate?.status === "prepared" && state.status !== "stale" && <SpecialistTaskActions projectId={projectId} stage="art" jobId={candidate.jobId} disabled={readOnly || busy} onDelivered={() => load()} />}
    {candidate && <CandidateReview candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} stale={state.status === "stale"} draft={draft} setDraft={setDraft} cancel={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))} accept={accept} />}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；文本与报告可审阅，参考研究在下方单独显示。</small><ArtReferenceGallery projectId={projectId} art={accepted.art} acceptedRevision={accepted.revision} acceptedContentHash={accepted.contentHash} studies={studies} decisions={referenceDecisions} decisionStates={referenceStates} readOnly={readOnly} busy={busy} setAssignment={setAssignment} refresh={() => load()} />{accepted.candidateJobId && <ArtReport key={`${projectId}:${accepted.candidateJobId}`} projectId={projectId} jobId={accepted.candidateJobId} />}{state.status !== "reopened" && <Editor disabled draft={JSON.stringify(accepted.art, null, 2)} setDraft={setDraft} />}<Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
    {accepted && state.status === "reopened" && <><Editor disabled={readOnly || busy} draft={draft} setDraft={setDraft} /><Button variant="primary" disabled={readOnly || busy} onClick={save}>保存重新打开的美术</Button></>}
    {(candidate?.status === "prepared" || assignment) && <details><summary>查看任务说明（手动方式）</summary>{candidate?.status === "prepared" && <Button disabled={readOnly || busy} onClick={() => act(() => plotloomApi.recoverArtHandoff(projectId, candidate.jobId), result => setAssignment(result.assignment))}>查看美术任务说明</Button>}{assignment && <textarea aria-label="美术任务说明" readOnly value={assignment} rows={5} />}</details>}
    {error && <ErrorNotice message={error} />}
  </article>;
}

function CandidateReview({ candidate, projectId, readOnly, busy, stale, draft, setDraft, cancel, accept }: { candidate: ArtCandidate; projectId: string; readOnly: boolean; busy: boolean; stale: boolean; draft: string; setDraft: (value: string) => void; cancel: () => void; accept: () => void }) {
  return <><small>冻结 source r{candidate.binding.sourceRevision} · cast r{candidate.binding.castRevision} · sections {candidate.binding.sectionIds.join(" · ")}</small>
    {candidate.status === "prepared" && <Button variant="danger" disabled={readOnly || busy} onClick={cancel}>取消此任务</Button>}
    {candidate.status === "ready" && <>{candidate.reportAvailable && <ArtReport key={`${projectId}:${candidate.jobId}`} projectId={projectId} jobId={candidate.jobId} />}<Editor disabled={readOnly || busy || stale} draft={draft} setDraft={setDraft} /><Button variant="primary" disabled={readOnly || busy || stale} onClick={accept}>显式接受此美术提案</Button><Button variant="danger" disabled={readOnly || busy} onClick={cancel}>拒绝并取消此美术提案</Button></>}
  </>;
}

function Editor({ disabled, draft, setDraft }: EditorProps) {
  return <details className="art-json-editor"><summary>查看/编辑 art.json（稳定地点和道具 ID 不可替换）</summary><textarea className="source-outline-json" disabled={disabled} value={draft} onChange={event => setDraft(event.target.value)} rows={24} /></details>;
}
