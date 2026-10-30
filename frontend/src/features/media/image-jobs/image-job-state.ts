import type { ImageJob } from "../../../types";

/** Integrity refusals require operator inspection; observation cannot repair them. */
export function imageJobAutomaticallyObservable(job: ImageJob): boolean {
  return job.current && job.state === "exported" && !job.deliveries.some(
    delivery => delivery.diagnosticCode === "package_conflict" || delivery.diagnosticCode === "request_integrity",
  );
}

/** Persisted terminal state supersedes transient feedback from a previous send. */
export function imageJobNotice(job: ImageJob, actionNotice?: string): string | undefined {
  if (job.state === "delivered") return "交付已完成；候选仍需审核选择，不会自动用于故事。";
  if (job.state === "cancelled") return "任务已取消；取消不会中止助手执行或解除占用，已有交付记录保留。";
  return actionNotice;
}
