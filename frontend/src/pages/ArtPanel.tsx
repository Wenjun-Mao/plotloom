import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ArtCandidate, ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal, ArtReviewState } from "../types";
import { ArtReferenceGallery } from "./ArtReferenceGallery";

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
    setState(undefined); setStudies([]); setReferenceDecisions([]); setReferenceStates([]); setAssignment(""); setDraft(""); setError(""); setBusy(false);
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
  const heading = state.status === "stale" ? "上下文已过期" : accepted ? `已接受 r${accepted.revision}` : candidate?.status === "ready" ? "可审核" : candidate?.status === "prepared" ? "等待 specialist" : "尚无美术候选";
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : accepted?.candidateJobId;
  const prepare = () => { const session = activeProject.current; setBusy(true); void plotloomApi.prepareArtCandidate(session.projectId).then(async result => { if (ownsProject(session)) { setAssignment(result.assignment); await load(session); } }).catch(reason => { if (ownsProject(session)) setError(reason instanceof Error ? reason.message : "Art preparation failed."); }).finally(() => { if (ownsProject(session)) setBusy(false); }); };
  const recover = () => candidate && act(
    () => plotloomApi.recoverArtHandoff(projectId, candidate.jobId),
    result => setAssignment(result.assignment),
  );
  const accept = () => { const art = parsed(); if (art && candidate) act(() => plotloomApi.acceptArtCandidate(projectId, { jobId: candidate.jobId, expectedArtRevision: candidate.expectedArtRevision, binding: candidate.binding, art })); };
  const save = () => { const art = parsed(); if (art && accepted) act(() => plotloomApi.saveReopenedArt(projectId, { expectedArtRevision: accepted.revision, binding: accepted.binding, art })); };
  return <article id="art" className="panel cast-panel art-panel" data-testid="art-review">
    <header><span>美术参考</span><strong>{heading}</strong></header>
    <p>共享地点、道具与可核对锚点在此处以文本先行审阅；它本身不生成图片。下方独立的环境与道具研究显示可复用参考字节及其当前性。继承的 cinematic realism 与上游 semi-realistic painterly 预设差异会显式保留给参考研究。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备并复制 art specialist handoff</Button>}
    {candidate && <CandidateReview candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} draft={draft} setDraft={setDraft} recover={recover} refresh={() => act(() => plotloomApi.refreshArtCandidate(projectId, candidate.jobId))} cancel={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))} accept={accept} />}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；文本与报告可审阅，参考研究在下方单独显示。</small><ArtReferenceGallery projectId={projectId} art={accepted.art} acceptedRevision={accepted.revision} acceptedContentHash={accepted.contentHash} studies={studies} decisions={referenceDecisions} decisionStates={referenceStates} readOnly={readOnly} busy={busy} setAssignment={setAssignment} refresh={() => load()} />{state.status !== "reopened" && <Editor disabled draft={draft} setDraft={setDraft} />}{reportJobId && <Report projectId={projectId} jobId={reportJobId} />}<Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
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
