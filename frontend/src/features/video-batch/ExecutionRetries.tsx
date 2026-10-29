import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { Button, ErrorNotice } from "../../components";
import type { VideoJob } from "../../types";
import { GenerationRetryStatus } from "../generation-retry/GenerationRetryStatus";
import { ManualExecutionRetry, exhaustedExecution, type FailedExecution } from "../generation-retry/ManualExecutionRetry";
import type { Batch } from "./contracts";
export function BatchExecutionRetries({ projectId, batch, disabled, onRetry, onObserve }: {
  projectId: string; batch: Batch; disabled: boolean;
  onRetry: (body: FailedExecution & { commandId: string; expectedRevision: number }) => Promise<void>;
  onObserve: () => Promise<void>;
}) {
  const key = JSON.stringify([projectId, batch.id, batch.revision, batch.execution.jobs]);
  const owner = useRef(key); owner.current = key;
  const [read, setRead] = useState<{ key: string; jobs?: VideoJob[]; error?: string }>();
  const jobs = read?.key === key ? read.jobs : undefined;
  const active = !["cancelled", "stale", "approved"].includes(batch.state);
  async function readJobs() {
    if (!Object.keys(batch.execution.jobs || {}).length) { setRead({ key, jobs: [] }); return; }
    try {
      const value = await plotloomApi.getVideoJobs(projectId);
      if (owner.current === key) setRead({ key, jobs: value.jobs });
    } catch (failure) {
      if (owner.current === key) setRead({ key, error: "视频任务状态尚未核实；不会显示旧任务的重试操作。" });
      throw failure;
    }
  }
  useEffect(() => { void readJobs().catch(() => {}); }, [key]);
  const observe = async () => { await onObserve(); await readJobs(); };
  const action = (status: NonNullable<Batch["execution"]["draft"]>["retry"], label: string, native = true) => status && <section key={label} aria-label={`${label}执行状态`}>
    <p>{label}</p><GenerationRetryStatus status={status} />
    {active && <ManualExecutionRetry identity={`${key}:${label}`} status={status} native={native} disabled={disabled}
      onRetry={body => onRetry({ ...body, expectedRevision: batch.revision })} onObserve={observe} />}
  </section>;
  return <>
    {action(batch.execution.draft?.retry, "供应商指令起草")}
    {action(batch.execution.fidelity?.retry, "指令保真检查")}
    {Object.entries(batch.execution.jobs || {}).map(([shotId, jobId]) => {
      const job = jobs?.find(item => item.id === jobId && item.projectId === projectId);
      if (!job?.retry || job.retry.currentJobId !== jobId) return null;
      const label = batch.manifest.targets.find(target => target.shotId === shotId)?.title || "镜头视频";
      // An old predecessor, a cancelled job or a stale input is never a retry target.
      const retryable = ["failed", "outcome_unknown"].includes(job.state) && !job.cancelRequestedAt
        && job.lifecycleStatus === "active" && job.inputStatus === "current" && exhaustedExecution(job.retry, false);
      return <section key={shotId} aria-label={`${label}视频执行状态`}><p>{label}</p><GenerationRetryStatus status={job.retry} />
        {active && retryable && <ManualExecutionRetry identity={`${key}:${shotId}`} status={job.retry} native={false} disabled={disabled}
          onRetry={body => onRetry({ ...body, expectedRevision: batch.revision })} onObserve={observe} />}
      </section>;
    })}
    {read?.key === key && read.error && <><ErrorNotice message={read.error} /><Button disabled={disabled} onClick={() => void readJobs().catch(() => {})}>重新读取视频任务状态</Button></>}
  </>;
}
