import { useRef, useState } from "react";
import { Button, ErrorNotice } from "../../components";
import type { GenerationRetryStatus } from "./contracts";

export type FailedExecution = { failedJobId: string; failedAttemptId?: string };
export function exhaustedExecution(status?: GenerationRetryStatus | null, native = true): FailedExecution | null {
  return status?.state === "exhausted" && status.currentJobId && (!native || status.currentAttemptId)
    ? { failedJobId: status.currentJobId, ...(native ? { failedAttemptId: status.currentAttemptId! } : {}) } : null;
}
/** One explicit intent; an uncertain acknowledgement can only be followed by a fresh owner read. */
export function ManualExecutionRetry({ identity, status, native = true, disabled, onRetry, onObserve }: {
  identity: string; status?: GenerationRetryStatus | null; native?: boolean; disabled: boolean;
  onRetry: (body: FailedExecution & { commandId: string }) => Promise<void>; onObserve: () => Promise<void>;
}) {
  const target = exhaustedExecution(status, native);
  const key = JSON.stringify([identity, target]);
  const owner = useRef(key); owner.current = key;
  const intent = useRef<{ key: string; commandId: string; active: boolean; uncertain: boolean } | undefined>(undefined);
  const [read, setRead] = useState<{ key: string; busy: boolean; uncertain: boolean; error: string; detail?: string }>();
  const state = read?.key === key ? read : undefined;
  async function retry() {
    if (!target || disabled || intent.current?.key === key && (intent.current.active || intent.current.uncertain)) return;
    const current = { key, commandId: crypto.randomUUID(), active: true, uncertain: false };
    intent.current = current; setRead({ key, busy: true, uncertain: false, error: "" });
    try {
      await onRetry({ commandId: current.commandId, ...target });
      if (owner.current !== key) return;
      // Keep the intent until its owner has been read even if an ACK did not change props yet.
      current.uncertain = true; setRead({ key, busy: false, uncertain: true, error: "请读取当前任务，核实本次手动重试结果。" });
    } catch (error) {
      if (owner.current !== key) return;
      current.uncertain = true; setRead({ key, busy: false, uncertain: true, error: "重试结果待核实；不会重复提交。请读取当前任务后再决定。", detail: error instanceof Error ? error.message : String(error) });
    } finally { current.active = false; }
  }
  async function observe() {
    if (state?.busy) return;
    setRead({ key, busy: true, uncertain: true, error: "" });
    try {
      await onObserve(); if (owner.current !== key) return;
      intent.current = undefined; setRead({ key, busy: false, uncertain: false, error: "" });
    } catch (error) { if (owner.current === key) setRead({ key, busy: false, uncertain: true, error: "当前任务仍待核实，请核对网络与服务状态后重新读取。", detail: error instanceof Error ? error.message : String(error) }); }
  }
  if (!target) return null;
  return <section aria-label="手动重试此失败任务">
    <p>自动重试已结束。可在本次剩余权限与预算内，明确使用新任务重试；先前任务与可能费用会保留。</p>
    <Button disabled={disabled || !!state?.busy || !!state?.uncertain} onClick={() => void retry()}>手动重试此任务</Button>
    {state?.uncertain && <Button disabled={state.busy} onClick={() => void observe()}>读取当前任务后再决定</Button>}
    {state?.error && <ErrorNotice message={state.error} detail={state.detail} />}
  </section>;
}
