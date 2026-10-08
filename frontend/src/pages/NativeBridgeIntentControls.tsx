import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import type { ProductionBridgeState } from "../types";

export function NativeBridgeIntentControls({ projectId, state, disabled, localEdits, run }: {
  projectId: string; state: ProductionBridgeState; disabled: boolean; localEdits: boolean;
  run: (operation: () => Promise<ProductionBridgeState>) => void;
}) {
  const job = state.intentJob?.transport === "codex_native" ? state.intentJob : undefined;
  const available = state.nativeIntentGeneration.status === "available";
  const proposal = state.proposal;
  const unresolved = state.intentJob && (["queued", "dispatched", "outcome_unknown"].includes(state.intentJob.status)
    || job?.status === "cancelled" && !job.responseHash && state.nativeIntentTask?.state !== "prepared");
  const action = (kind: "send" | "check" | "cancel") => {
    if (job) run(() => plotloomApi.nativeBridgeIntentAction(projectId, job.id, kind));
  };
  return <section className="bridge-intent-controls" aria-label="Codex 戏剧意图任务">
    {state.status !== "accepted" && <>
      <p>Codex 文字助手为冻结提案生成整包戏剧意图建议。准备后须单独发送；交付后仍需你审阅并保存整包。</p>
      <Button variant="primary" disabled={disabled || localEdits || !available || !proposal || state.status === "stale" || !!unresolved} onClick={() => {
        if (proposal) run(() => plotloomApi.prepareNativeBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }));
      }}>准备 Codex 戏剧意图任务</Button>
      {!available && <p className="action-prerequisite">尚未配置 Codex 文字助手，请在“生成助手设置”填写聊天 ID。你也可以填写作者意图并保存整包。</p>}
    </>}
    {job && <>
      <p role="status">{job.status === "queued" ? "任务已冻结，尚未发送" : job.status === "dispatched" ? "已尝试发送，等待检查助手交付" : job.status === "outcome_unknown" ? "发送结果不确定；请检查同一任务，请勿重复发送" : job.status === "ready" ? "建议已进入待审阅提案，尚未由作者确认" : job.status === "cancelled" ? "任务已取消，后续交付不会进入提案" : job.status === "stale" ? "冻结来源或投产目标已变化，结果未采用" : "任务失败，请检查记录"}</p>
      <small>冻结提案 r{job.proposalRevision} · 任务 {job.id}。重新打开项目可继续检查原任务、阅读原报告。取消不会中止助手执行或解除占用。</small>
      {job.status === "queued" && state.nativeIntentTask?.state === "prepared" && <Button disabled={disabled || localEdits || !available || state.status === "stale"} onClick={() => action("send")}>发送给 Codex 文字助手</Button>}
      {["dispatched", "outcome_unknown", "cancelled", "stale"].includes(job.status) && !job.responseHash && <Button disabled={disabled} onClick={() => action("check")}>检查原任务交付</Button>}
      {["queued", "dispatched", "outcome_unknown"].includes(job.status) && <Button disabled={disabled} onClick={() => action("cancel")}>取消 Codex 意图任务</Button>}
      {job.errorMessage && ["outcome_unknown", "failed"].includes(job.status) && <ErrorNotice message={job.errorMessage} />}
      {!!state.nativeIntentTask?.limitations.length && <details open><summary>助手交付的限制说明</summary><ul>{state.nativeIntentTask.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul></details>}
      {job.responseHash && <details><summary>阅读 Codex 戏剧意图原始报告（只读）</summary>
        <p>报告保留冻结来源；阅读不代表当前提案已确认。请核对当前提案，并单独保存戏剧意图整包。</p>
        <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title="Codex 戏剧意图原始报告（只读）" className="source-outline-report" url={plotloomApi.nativeBridgeIntentReportUrl(projectId, job.id)} />
      </details>}
    </>}
  </section>;
}
