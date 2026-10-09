import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import type { BranchTaskState, SectionMap, SourceTopology } from "../types";

const branchMessage = (reason: unknown) => reason instanceof Error ? reason.message : "剧情分支建议操作失败，请重试。";

export function BranchSuggestionPanel({ projectId, basis, disabled, cancelDisabled, dirty, onAdopt, onPlan }: { projectId: string; basis: string; disabled: boolean; cancelDisabled: boolean; dirty: boolean; onAdopt: (draft: SectionMap) => void; onPlan: (topology: SourceTopology) => void }) {
  const [state, setState] = useState<BranchTaskState>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const epoch = useRef(0);
  const pending = useRef<object | null>(null);
  const dirtyNow = useRef(dirty); dirtyNow.current = dirty;
  useEffect(() => () => { pending.current = null; }, [projectId]);
  useEffect(() => {
    const owner = ++epoch.current;
    setState(undefined); setBusy(pending.current !== null); setError("");
    void plotloomApi.getBranchSuggestions(projectId).then(value => { if (owner === epoch.current) setState(value); }).catch(reason => { if (owner === epoch.current) setError(branchMessage(reason)); });
    return () => { epoch.current++; };
  }, [projectId, basis]);
  useEffect(() => { if (state?.plannedTopology) onPlan(state.plannedTopology); }, [state?.plannedTopology?.topologyHash]);
  const run = async (operation: () => Promise<BranchTaskState>) => {
    if (busy || pending.current) return;
    const ticket = {}; pending.current = ticket;
    const owner = epoch.current; setBusy(true); setError("");
    try {
      const value = await operation();
      if (pending.current !== ticket) return;
      if (owner === epoch.current) setState(value);
      else {
        // A same-project basis read may precede this mutation's commit. Read
        // again afterward instead of reviving an obsolete task projection.
        const current = epoch.current;
        const refreshed = await plotloomApi.getBranchSuggestions(projectId);
        if (pending.current === ticket && current === epoch.current) setState(refreshed);
      }
    } catch (reason) { if (pending.current === ticket) setError(branchMessage(reason)); }
    finally { if (pending.current === ticket) { pending.current = null; setBusy(false); } }
  };
  const adopt = async () => {
    if (disabled || dirty || busy || !state?.candidate) return;
    const owner = epoch.current; setBusy(true); setError("");
    try {
      const draft = await plotloomApi.getBranchDraft(projectId, state.candidate.jobId);
      if (owner === epoch.current) {
        if (dirtyNow.current) setError("读取建议期间已有本地修改，已保留当前草稿。请保存或放弃后重试。");
        else onAdopt(draft);
      }
    } catch (reason) { if (owner === epoch.current) setError(branchMessage(reason)); }
    finally { if (owner === epoch.current) setBusy(false); }
  };
  const candidate = state?.candidate;
  const suggestion = candidate?.suggestion;
  const stale = Boolean(state?.staleReasons.length);
  return <section className="branch-suggestion" aria-label="助手剧情分支建议">
    <h3>从已确认大纲准备完整建议</h3><p>助手按简报规划的结构填入所有剧情节点、播放问题、选项、后续剧情和汇合衔接。你可以审阅、调整，再明确确认。</p>
    {state?.plannedTopology && <p className="action-prerequisite">已规划 {state.plannedTopology.nodes.length} 个剧情节点 · {state.plannedTopology.nodes.filter(node => node.kind === "decision").length} 个选择点 · {state.plannedTopology.nodes.filter(node => node.kind === "ending").length} 个不同结局 · {state.plannedTopology.nodes.filter(node => node.kind === "join").length} 个汇合节点</p>}
    {state?.infeasibleReason && <ErrorNotice message={state.infeasibleReason} />}
    {!state && !error && <p role="status">正在读取建议任务…</p>}
    {state && (!candidate || candidate.status === "cancelled") && <Button variant="primary" busy={busy} disabled={disabled || busy || Boolean(state.infeasibleReason)} onClick={() => void run(() => plotloomApi.prepareBranchSuggestions(projectId))}>准备剧情分支建议</Button>}
    {candidate?.status === "prepared" && <SpecialistTaskActions key={candidate.jobId} projectId={projectId} stage="branches" jobId={candidate.jobId} disabled={disabled || busy} sendDisabled={stale} onDelivered={() => run(() => plotloomApi.getBranchSuggestions(projectId))} />}
    {stale && <p className="notice warning">{state?.staleReasons.join("；")}</p>}
    {candidate?.status === "ready" && candidate.reportAvailable && <details>
      <summary>打开分支建议报告（静态阅读）</summary>
      <p className="action-prerequisite">报告对应这份未确认的建议。阅读不会带入、保存、确认或应用路线；报告内脚本和网络内容受隔离限制。</p>
      <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title="分支建议报告静态阅读" className="source-outline-report" url={plotloomApi.branchCandidateReportUrl(projectId, candidate.jobId)} />
    </details>}
    {suggestion && <div className="branch-suggestion-preview">
      {suggestion.nodes.map((node, index) => <section key={node.id}><h4>剧情节点 {index + 1}：{node.title}</h4><p>{node.summary}</p></section>)}
      {suggestion.choices.map(choice => <section key={choice.nodeId}><h4>播放时显示的问题：{choice.question}</h4><div className="field-grid two">{choice.options.map((option, index) => {
        const target = state?.plannedTopology?.edges.find(edge => edge.id === option.id)?.targetNodeId;
        return <section key={option.id}><h4>选项 {String.fromCharCode(65 + index)}：{option.label}</h4><p>{option.consequence}</p><strong>进入：{suggestion.nodes.find(node => node.id === target)?.title}</strong></section>;
      })}</div></section>)}
      {suggestion.joins.map(join => <p key={join.id}>汇合衔接：{join.reconciliation}</p>)}
      {suggestion.clarifications.map((note, index) => <p className="notice warning" key={index}>待确认说明：{note}</p>)}
      <Button variant="primary" busy={busy} disabled={disabled || busy || dirty || stale} onClick={() => void adopt()}>带入可编辑草稿</Button>
      {dirty && <p className="action-prerequisite">已有未保存修改。请先保存或明确放弃当前草稿，再带入建议。</p>}
      <p className="action-prerequisite">带入只更新本地草稿；随后需确认保存并应用到故事路线。</p>
    </div>}
    {candidate && candidate.status !== "cancelled" && <><Button variant="quiet" disabled={cancelDisabled || busy} onClick={() => void run(() => plotloomApi.cancelBranchSuggestions(projectId, candidate.jobId))}>放弃此建议任务</Button><p className="action-prerequisite">放弃仅取消这份建议，不修改故事或草稿，也不会解除助手占用。</p></>}
    {disabled && <p className="action-prerequisite">请先确认当前大纲、保存来源修改，并确保项目可编辑。</p>}
    {error && <><ErrorNotice message={error} /><Button variant="quiet" disabled={busy} onClick={() => void run(() => plotloomApi.getBranchSuggestions(projectId))}>重试读取建议</Button></>}
  </section>;
}
