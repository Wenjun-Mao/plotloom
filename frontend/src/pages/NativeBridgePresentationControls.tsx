import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import type { ProductionBridgeState } from "../types";

export function NativeBridgePresentationControls({ projectId, state, disabled, localEdits, occupied, run }: {
  projectId: string; state: ProductionBridgeState; disabled: boolean; localEdits: boolean; occupied: boolean;
  run: (operation: () => Promise<ProductionBridgeState>) => void;
}) {
  const job = state.presentationJob, proposal = state.proposal;
  const available = state.nativePresentationGeneration?.status === "available";
  const action = (kind: "send" | "check" | "cancel") => {
    if (job) run(() => plotloomApi.nativeBridgePresentationAction(projectId, job.id, kind));
  };
  return <section className="bridge-intent-controls" aria-label="Codex 呈现方式任务">
    {state.status !== "accepted" && <>
      <p>让文字助手建议每段内容的呈现方式与忠实画面描述。建议可修改，确认保存后才会采用。</p>
      <Button variant="primary" disabled={disabled || localEdits || occupied || !available || !proposal || state.status === "stale"} onClick={() => {
        if (proposal) run(() => plotloomApi.prepareNativeBridgePresentation(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }));
      }}>准备呈现方式建议</Button>
      {!available && <small>未配置文字助手。可在「生成助手设置」配置，或直接填写下方呈现方式。</small>}
    </>}
    {job && <>
      <p role="status">{job.status === "queued" ? "呈现方式任务已准备，尚未发送。" : job.status === "dispatched" ? "已发送，等待助手交付。" : job.status === "outcome_unknown" ? "发送结果不确定，请检查原任务，不要重复发送。" : job.status === "ready" ? "助手建议已返回，尚不代表呈现方式已确认。" : job.status === "stale" ? "任务对应的提案已变化；原报告保留，建议不再适用于当前提案。" : job.status === "cancelled" ? "任务已取消；取消不会中止助手执行，晚到交付仅保留作证据。" : "任务失败，请查看错误说明。"}</p>
      {job.status === "queued" && state.nativePresentationTask?.state === "prepared" && <Button disabled={disabled || localEdits || !available || state.status === "stale"} onClick={() => action("send")}>发送呈现方式任务</Button>}
      {["dispatched", "outcome_unknown", "cancelled", "stale"].includes(job.status) && !job.responseHash && <Button disabled={disabled} onClick={() => action("check")}>检查呈现方式交付</Button>}
      {["queued", "dispatched", "outcome_unknown"].includes(job.status) && <Button disabled={disabled} onClick={() => action("cancel")}>取消呈现方式任务</Button>}
      {job.errorMessage && <ErrorNotice message={job.errorMessage} />}
      {!!state.nativePresentationTask?.limitations.length && <details><summary>助手建议的限制说明</summary><ul>{state.nativePresentationTask.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul></details>}
      {job.responseHash && <details className="bridge-intent-report"><summary>阅读呈现方式原始报告（只读）</summary>
        <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title="呈现方式原始报告（只读）" className="source-outline-report" url={plotloomApi.nativeBridgePresentationReportUrl(projectId, job.id)} />
      </details>}
    </>}
  </section>;
}
