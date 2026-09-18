import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { ArtCandidate, ArtReferenceProposal, ArtReviewState } from "../types";

type EditorProps = { disabled: boolean; draft: string; setDraft: (value: string) => void };
type ProjectSession = { projectId: string; epoch: number };

/** F3A owns text review; the distinct F3B study surface owns reference bytes. */
export function ArtPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ArtReviewState>();
  const [studies, setStudies] = useState<ArtReferenceProposal[]>([]);
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
    try {
      const [next, referenceStudies] = await Promise.all([
        plotloomApi.getArt(session.projectId),
        plotloomApi.getArtReferenceProposals(session.projectId),
      ]);
      if (ownsProject(session)) { setState(next); setStudies(referenceStudies.proposals); }
    } catch (reason) {
      if (ownsProject(session)) setError(reason instanceof Error ? reason.message : "Unable to load art studies.");
    }
  }, [projectId]);
  useEffect(() => {
    const session = activeProject.current;
    setState(undefined); setStudies([]); setAssignment(""); setDraft(""); setError(""); setBusy(false);
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
  if (!state) return null;
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
  return <article className="panel cast-panel" data-testid="art-review">
    <header><span>06 · F3A novel-art proposal</span><strong>{heading}</strong></header>
    <p>F3A 的共享地点、道具与可核对锚点在此处以文本先行审阅；它本身不生成图片。下方独立的 F3B 环境/道具研究显示可复用参考字节及其当前性。继承的 cinematic realism 与上游 semi-realistic painterly 预设差异会显式保留给 F3B。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备并复制 art specialist handoff</Button>}
    {candidate && <CandidateReview candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} draft={draft} setDraft={setDraft} recover={recover} refresh={() => act(() => plotloomApi.refreshArtCandidate(projectId, candidate.jobId))} cancel={() => act(() => plotloomApi.cancelArtCandidate(projectId, candidate.jobId))} accept={accept} />}
    {accepted && <><small>已接受 hash {accepted.contentHash.slice(0, 12)}；文本与报告可审阅，F3B 参考研究在下方单独显示。</small><ArtReferenceStudies projectId={projectId} art={accepted.art} acceptedRevision={accepted.revision} acceptedContentHash={accepted.contentHash} studies={studies} readOnly={readOnly} busy={busy} setAssignment={setAssignment} refresh={load} reportError={setError} />{state.status !== "reopened" && <Editor disabled draft={draft} setDraft={setDraft} />}{reportJobId && <Report projectId={projectId} jobId={reportJobId} />}<Button variant="quiet" disabled={readOnly || busy || state.status === "reopened"} onClick={() => act(() => plotloomApi.reopenArt(projectId, accepted.revision))}>重新打开美术提案</Button></>}
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

function ArtReferenceStudies({ projectId, art, acceptedRevision, acceptedContentHash, studies, readOnly, busy, setAssignment, refresh, reportError }: {
  projectId: string; art: Record<string, unknown>; studies: ArtReferenceProposal[]; readOnly: boolean; busy: boolean;
  acceptedRevision: number; acceptedContentHash: string; setAssignment: (value: string) => void;
  refresh: (session?: ProjectSession) => Promise<void>; reportError: (value: string) => void;
}) {
  const [direction, setDirection] = useState("Cinematic realism: grounded materials, natural lens behavior, no people or hands unless the accepted subject explicitly requires them.");
  const sessionKey = `${projectId}:${acceptedRevision}:${acceptedContentHash}`;
  const activeSession = useRef({ key: sessionKey, epoch: 0 });
  if (activeSession.current.key !== sessionKey) activeSession.current = { key: sessionKey, epoch: activeSession.current.epoch + 1 };
  const ownsSession = (session: { key: string; epoch: number }) => activeSession.current === session;
  useEffect(() => {
    const session = activeSession.current;
    return () => {
      // This component owns the reference-operation callback. Invalidate it
      // before its parent can be unmounted or replaced by another art visit.
      if (ownsSession(session)) activeSession.current = { key: session.key, epoch: session.epoch + 1 };
    };
  }, [sessionKey]);
  const [busySession, setBusySession] = useState<{ key: string; epoch: number }>();
  const studyBusy = busy || busySession === activeSession.current;
  const subjects = (["scene", "prop"] as const).flatMap(subjectType => {
    const items = art[subjectType === "scene" ? "scenes" : "props"];
    return Array.isArray(items) ? items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && typeof item.id === "string").map(item => ({ subjectType, subjectId: item.id as string, name: String(item.name || item.id) })) : [];
  });
  const latest = (subjectType: "scene" | "prop", subjectId: string) => studies.find(study => study.subjectType === subjectType && study.subjectId === subjectId);
  const act = async <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeSession.current;
    setBusySession(session); reportError("");
    try {
      const result = await operation();
      if (!ownsSession(session)) return;
      onSuccess?.(result);
      await refresh();
    } catch (reason) {
      if (ownsSession(session)) reportError(reason instanceof Error ? reason.message : "Art reference operation failed.");
    } finally {
      if (ownsSession(session)) setBusySession(undefined);
    }
  };
  return <section className="art-reference-studies" data-testid="art-reference-studies">
    <header><span>F3B · 环境 / 道具参考研究</span><strong>accepted art → candidate only</strong></header>
    <p>上游的 painterly preset 保留在 art.json；此处的 creator overlay 明确要求 cinematic realism，不会改写上游含义或接受的美术。研究是可复用的 managed asset，但不等于镜头、选择或人类创意批准。</p>
    <label>渲染方向 overlay<textarea data-testid="art-reference-direction" disabled={readOnly || studyBusy} rows={3} value={direction} onChange={event => setDirection(event.target.value)} /></label>
    <div className="media-candidate-grid">
      {subjects.map(subject => {
        const study = latest(subject.subjectType, subject.subjectId);
        const candidates = study?.deliveries.flatMap(delivery => delivery.candidates) || [];
        const status = artReferenceStudyStatus(study);
        return <article className="media-candidate" key={`${subject.subjectType}:${subject.subjectId}`} data-testid={`art-reference-${subject.subjectType}-${subject.subjectId}`}>
          <strong>{subject.subjectType} · {subject.name}</strong><small>{subject.subjectId} · {status}</small>
          {candidates.map(candidate => candidate.asset ? <figure key={candidate.id}><img src={plotloomApi.managedAssetUrl(projectId, candidate.asset.id)} alt={`${subject.name} reference study`} /><figcaption>{candidate.outputFilename} · {candidate.outputHash.slice(0, 12)}</figcaption></figure> : null)}
          {(!study || !study.current) && <Button disabled={readOnly || studyBusy || !direction.trim()} onClick={() => void act(() => plotloomApi.prepareArtReferenceProposal(projectId, { subjectType: subject.subjectType, subjectId: subject.subjectId, renderDirection: direction.trim() }))}>准备研究</Button>}
          {study && <div className="button-row">{study.current && <Button disabled={readOnly || studyBusy} onClick={() => void act(() => plotloomApi.copyArtReferenceProposal(projectId, study.id), copied => setAssignment(copied.assignment))}>复制 ImageGen 任务</Button>}{study.state !== "cancelled" && <Button disabled={readOnly || studyBusy} onClick={() => void act(() => plotloomApi.refreshArtReferenceProposal(projectId, study.id))}>刷新 delivery</Button>}{(study.state === "prepared" || study.state === "exported") && <Button variant="danger" disabled={readOnly || studyBusy} onClick={() => void act(() => plotloomApi.cancelArtReferenceProposal(projectId, study.id, "Operator cancelled the F3B reference-study handoff."))}>取消 handoff</Button>}</div>}
        </article>;
      })}
    </div>
  </section>;
}

function artReferenceStudyStatus(study: ArtReferenceProposal | undefined): string {
  if (!study) return "missing";
  if (study.state === "cancelled") return "cancelled";
  if (!study.current) return "changed / stale";
  if (study.state === "delivered") return "current";
  return "awaiting delivery";
}
