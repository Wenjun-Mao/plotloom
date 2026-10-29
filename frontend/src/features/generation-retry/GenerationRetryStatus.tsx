import type { GenerationRetryStatus as RetryStatus } from "./contracts";

export function GenerationRetryStatus({ status }: { status?: RetryStatus | null }) {
  if (!status) return null;
  const automaticUsed = status.automaticRetriesUsed ?? status.retryCount;
  const manualUsed = Math.max(0, status.retryCount - automaticUsed);
  return <section aria-label="本次任务自动重试状态">
    <p>{status.automaticRetryLimit == null ? "此任务未冻结自动重试额度；不会新增重试授权。"
      : `本次已冻结自动重试 ${status.automaticRetryLimit} 次，已用 ${automaticUsed} 次；首次尝试不计入。`}</p>
    {manualUsed > 0 && <p>另有 {manualUsed} 次手动重试，均保留先前任务。</p>}
    {status.state === "retry_pending" && <p>确认本地执行已停止后，后端才会处理已授权的重试；核对状态不会重新提交。</p>}
    {status.state === "exhausted" && <p>此任务的自动重试次数已用尽。请查看失败原因，修正问题或在剩余权限与预算内手动重试。</p>}
    {status.state === "stopped" && <p>此任务已停止，不再自动重试。</p>}
    {status.possiblePriorCost && <p>先前远程执行的结果可能仍不确定，可能已产生费用；本地停止不代表远程已取消，也不代表费用已退回。</p>}
    <details><summary>当前尝试与先前任务（技术详情）</summary>
      <p>当前任务：{status.currentJobId ?? "尚无"}；当前尝试：{status.currentAttemptId ?? "尚无"}。</p>
      {!!status.predecessorJobIds.length && <p>先前任务：{status.predecessorJobIds.join("、")}</p>}
    </details>
  </section>;
}
