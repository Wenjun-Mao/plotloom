import { useEffect } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { SpecialistTaskActions } from "../features/specialists/SpecialistTaskActions";
import type { SectionMap, SourceTopology } from "../types";
import { useBranchSuggestions } from "../features/branches/useBranchSuggestions";
import type { BranchTaskReadObservation } from "../app/workspace/recommendedWorkflow";

export function BranchSuggestionPanel({ projectId, basis, disabled, cancelDisabled, dirty, onAdopt, onPlan, onTaskRead }: { projectId: string; basis: string; disabled: boolean; cancelDisabled: boolean; dirty: boolean; onAdopt: (draft: SectionMap) => void; onPlan: (topology: SourceTopology) => void; onTaskRead?: (projectId: string, observation: BranchTaskReadObservation) => void }) {
  const { state, busy, mutationPending, error, refresh, adopt, mutate, retryDisabled } = useBranchSuggestions(projectId, basis, dirty, onAdopt);
  useEffect(() => { if (state?.plannedTopology) onPlan(state.plannedTopology); }, [state?.plannedTopology?.topologyHash]);
  useEffect(() => {
    if (!onTaskRead) return;
    onTaskRead(projectId, { basis, ...(state
      ? { status: "ready" as const, value: state }
      : error ? { status: "failed" as const, value: null } : { status: "loading" as const, value: null }) });
  }, [projectId, basis, state, error, onTaskRead]);
  const candidate = state?.candidate;
  const suggestion = candidate?.suggestion;
  const stale = Boolean(state?.staleReasons.length);
  return <section className="branch-suggestion" aria-label="助手剧情分支建议">
    <h3>从已确认大纲准备完整建议</h3><p>助手按简报规划的结构填入所有剧情节点、播放问题、选项、后续剧情和汇合衔接。你可以审阅、调整，再明确确认。</p>
    {state?.plannedTopology && <p className="action-prerequisite">已规划 {state.plannedTopology.nodes.length} 个剧情节点 · {state.plannedTopology.nodes.filter(node => node.kind === "decision").length} 个选择点 · {state.plannedTopology.nodes.filter(node => node.kind === "ending").length} 个不同结局 · {state.plannedTopology.nodes.filter(node => node.kind === "join").length} 个汇合节点</p>}
    {state?.infeasibleReason && <ErrorNotice message={state.infeasibleReason} />}
    {mutationPending && <p role="status">正在更新建议任务，请稍候。切换页面不会再次发送。</p>}
    {!state && !error && <p role="status">正在读取建议任务…</p>}
    {state && (!candidate || candidate.status === "cancelled") && <Button variant="primary" busy={busy} disabled={disabled || busy || Boolean(state.infeasibleReason)} onClick={() => void mutate(() => plotloomApi.prepareBranchSuggestions(projectId))}>准备剧情分支建议</Button>}
    {candidate?.status === "prepared" && <SpecialistTaskActions key={candidate.jobId} projectId={projectId} stage="branches" jobId={candidate.jobId} disabled={disabled || busy} sendDisabled={stale} onDelivered={refresh} />}
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
    {candidate && candidate.status !== "cancelled" && <><Button variant="quiet" disabled={cancelDisabled || busy} onClick={() => void mutate(() => plotloomApi.cancelBranchSuggestions(projectId, candidate.jobId))}>放弃此建议任务</Button><p className="action-prerequisite">放弃仅取消这份建议，不修改故事或草稿，也不会解除助手占用。</p></>}
    {disabled && <p className="action-prerequisite">请先确认当前大纲、保存来源修改，并确保项目可编辑。</p>}
    {error && <><ErrorNotice message={error} /><Button variant="quiet" disabled={retryDisabled} onClick={refresh}>重试读取建议</Button></>}
  </section>;
}
