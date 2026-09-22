import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import type { AcceptedScriptRevision, ScriptCandidate, ScriptReviewState } from "../types";

type ProjectSession = { projectId: string; epoch: number };

/** F4 reviews one upstream JSON authority and permits only bound episode replacement. */
export function ScriptPanel({ projectId, readOnly, onInitialLoadSettled }: { projectId: string; readOnly: boolean; onInitialLoadSettled?: () => void }) {
  const [state, setState] = useState<ScriptReviewState>();
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sectionId, setSectionId] = useState("");
  const [draft, setDraft] = useState("");
  const activeProject = useRef<ProjectSession>({ projectId, epoch: 0 });
  if (activeProject.current.projectId !== projectId) {
    activeProject.current = { projectId, epoch: activeProject.current.epoch + 1 };
  }
  const owns = (session: ProjectSession) => activeProject.current === session;
  const load = useCallback(async (session = activeProject.current) => {
    try {
      const next = await plotloomApi.getScript(session.projectId);
      if (owns(session)) setState(next);
    } catch (reason) {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "Unable to load script.");
    }
  }, [projectId]);
  useEffect(() => {
    const session = activeProject.current;
    setState(undefined); setAssignment(""); setError(""); setBusy(false); setSectionId(""); setDraft("");
    void load(session).finally(() => { if (owns(session)) onInitialLoadSettled?.(); });
    return () => {
      if (owns(session)) activeProject.current = { projectId: session.projectId, epoch: session.epoch + 1 };
    };
  }, [projectId, load, onInitialLoadSettled]);
  useEffect(() => {
    // A selection belongs to one accepted revision and one editor mode. It is
    // never safe to carry it across reopening or an async project refresh.
    setSectionId(""); setDraft("");
  }, [projectId, state?.acceptedScript?.revision, state?.status]);

  const run = <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeProject.current;
    setBusy(true); setError("");
    void operation().then(async result => {
      if (!owns(session)) return;
      onSuccess?.(result);
      await load(session);
    }).catch(reason => {
      if (owns(session)) setError(reason instanceof Error ? reason.message : "Script operation failed.");
    }).finally(() => {
      // Ownership remains held through response settlement; invalidation on
      // unmount/project switch makes this a deliberate no-op afterwards.
      if (owns(session)) setBusy(false);
    });
  };
  const prepare = () => run(() => plotloomApi.prepareScriptCandidate(projectId), result => setAssignment(result.assignment));
  if (!state) return null;

  const { candidate, acceptedScript: accepted } = state;
  const script = activeScript(candidate, accepted);
  const selectSection = (nextSectionId: string) => {
    setSectionId(nextSectionId);
    setDraft(episodeForSection(script, nextSectionId));
  };
  const save = () => {
    if (!accepted) return;
    try {
      const episode = JSON.parse(draft) as Record<string, unknown>;
      run(() => plotloomApi.saveScriptSection(projectId, {
        expectedScriptRevision: accepted.revision,
        binding: accepted.binding,
        sectionId,
        episode,
      }));
    } catch {
      setError("章节必须是有效 JSON。");
    }
  };
  const reportJobId = candidate?.status === "ready" ? candidate.jobId : accepted?.candidateJobId;
  return <article id="script" className="panel cast-panel" data-testid="script-review">
    <header><span>剧本</span><strong>{heading(state)}</strong></header>
    <p>完整 pilot 的三个稳定章节各绑定一个已冻结的上游 episode。script.json 是创作权威；分镜评审仅消费这条已接受的 seam。</p>
    <div className="notice warning">这是非 episode pilot。hook/cliff 与跨互斥结局的 aggregate duration 不构成产品节奏或悬念批准；上游 gate 仍作结构检查，冻结的章节和完整路径时长上限仍然适用。</div>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!candidate && state.status !== "reopened" && <Button variant="primary" disabled={readOnly || busy} onClick={prepare}>准备并复制 script specialist handoff</Button>}
    {candidate && <CandidateActions candidate={candidate} projectId={projectId} readOnly={readOnly} busy={busy} run={run} />}
    {candidate?.status === "ready" && <ScriptJson title="查看待接受 script.json" script={candidate.script} />}
    {accepted && <AcceptedReview accepted={accepted} projectId={projectId} readOnly={readOnly} busy={busy} status={state.status} sectionId={sectionId} draft={draft} onSelect={selectSection} onDraft={setDraft} onReopen={() => run(() => plotloomApi.reopenScript(projectId, accepted.revision))} onSave={save} />}
    {reportJobId && <Report projectId={projectId} jobId={reportJobId} />}
    {assignment && <label>复制给 specialist 的冻结任务<textarea readOnly value={assignment} rows={5} /></label>}
    {error && <ErrorNotice message={error} />}
  </article>;
}

function CandidateActions({ candidate, projectId, readOnly, busy, run }: { candidate: ScriptCandidate; projectId: string; readOnly: boolean; busy: boolean; run: <Result>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => void }) {
  if (candidate.status === "prepared") return <div className="button-row">
    <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.recoverScriptHandoff(projectId, candidate.jobId))}>重新复制冻结 handoff</Button>
    <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.refreshScriptCandidate(projectId, candidate.jobId))}>刷新 specialist delivery</Button>
    <Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelScriptCandidate(projectId, candidate.jobId))}>取消 handoff</Button>
  </div>;
  if (candidate.status === "ready") return <div className="button-row">
    <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.acceptScriptCandidate(projectId, { jobId: candidate.jobId, expectedScriptRevision: candidate.expectedScriptRevision, binding: candidate.binding, script: candidate.script || {} }))}>显式接受完整 pilot 剧本</Button>
    <Button variant="danger" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelScriptCandidate(projectId, candidate.jobId))}>拒绝并取消此剧本</Button>
  </div>;
  return null;
}

function AcceptedReview({ accepted, projectId, readOnly, busy, status, sectionId, draft, onSelect, onDraft, onReopen, onSave }: { accepted: AcceptedScriptRevision; projectId: string; readOnly: boolean; busy: boolean; status: ScriptReviewState["status"]; sectionId: string; draft: string; onSelect: (sectionId: string) => void; onDraft: (draft: string) => void; onReopen: () => void; onSave: () => void }) {
  const editing = status === "reopened";
  return <section>
    <small>已接受 r{accepted.revision} · hash {accepted.contentHash.slice(0, 12)}。当前 JSON 可直接检查；上游报告始终是原始派生报告。</small>
    <ScriptJson title="查看当前已接受 script.json" script={accepted.script} />
    {!editing && <Button variant="quiet" disabled={readOnly || busy} onClick={onReopen}>重新打开剧本</Button>}
    {editing && <SectionEditor accepted={accepted} disabled={readOnly || busy} sectionId={sectionId} draft={draft} onSelect={onSelect} onDraft={onDraft} onSave={onSave} />}
  </section>;
}

function SectionEditor({ accepted, disabled, sectionId, draft, onSelect, onDraft, onSave }: { accepted: AcceptedScriptRevision; disabled: boolean; sectionId: string; draft: string; onSelect: (sectionId: string) => void; onDraft: (draft: string) => void; onSave: () => void }) {
  return <section>
    <label>编辑章节<select disabled={disabled} value={sectionId} onChange={event => onSelect(event.target.value)}>
      <option value="">选择稳定章节</option>
      {accepted.binding.sectionBindings.map(item => <option key={item.sectionId} value={item.sectionId}>{item.sectionId} · episode {item.episode}</option>)}
    </select></label>
    {sectionId && <><textarea className="source-outline-json" disabled={disabled} rows={22} value={draft} onChange={event => onDraft(event.target.value)} /><Button variant="primary" disabled={disabled} onClick={onSave}>保存此章节，不覆盖其他章节</Button></>}
  </section>;
}

function ScriptJson({ title, script }: { title: string; script: Record<string, unknown> | null }) {
  return <details><summary>{title}</summary><pre>{JSON.stringify(script, null, 2)}</pre></details>;
}

function Report({ projectId, jobId }: { projectId: string; jobId: string }) {
  return <details><summary>打开原始只读上游报告</summary><iframe title="original derived upstream script report" className="source-outline-report" sandbox="" src={plotloomApi.scriptCandidateReportUrl(projectId, jobId)} /></details>;
}

function activeScript(candidate: ScriptCandidate | null, accepted: AcceptedScriptRevision | null): Record<string, unknown> | null {
  if (candidate?.status === "ready") return candidate.script;
  return accepted?.script || null;
}

function episodeForSection(script: Record<string, unknown> | null, sectionId: string): string {
  const bindings = Array.isArray(script?.sectionBindings) ? script.sectionBindings : [];
  const binding = bindings.find(item => typeof item === "object" && item !== null && (item as Record<string, unknown>).sectionId === sectionId) as Record<string, unknown> | undefined;
  const episodes = Array.isArray(script?.episodes) ? script.episodes : [];
  const episode = episodes.find(item => typeof item === "object" && item !== null && (item as Record<string, unknown>).ep === binding?.episode);
  return JSON.stringify(episode || {}, null, 2);
}

function heading(state: ScriptReviewState): string {
  if (state.status === "stale") return "上下文已过期";
  if (state.acceptedScript) return `已接受 r${state.acceptedScript.revision}`;
  if (state.candidate?.status === "ready") return "可审核";
  if (state.candidate?.status === "prepared") return "等待 specialist";
  return "尚无剧本候选";
}
