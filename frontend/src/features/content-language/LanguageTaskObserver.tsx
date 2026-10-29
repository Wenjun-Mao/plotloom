import { ManualExecutionRetry, type FailedExecution } from "../generation-retry/ManualExecutionRetry";
import { useEffect, useRef, useState } from "react";
import { Button, ErrorNotice } from "../../components";
import { contentLanguageApi } from "./api";
import { olderLanguageObservation, languageCheckPassed, languageCheckPending, type ContentLanguageStatus } from "./contracts";
import { ContentLanguageEvidence } from "./ContentLanguageReview";
/** Observes one admitted checker; receiving its original candidate stays with its native owner. */
export function LanguageTaskObserver({ projectId, initial, disabled, onVerified, onContinue }: {
  projectId: string; initial: ContentLanguageStatus; disabled: boolean; onVerified?: () => void; onContinue?: () => void;
}) {
  const identity = `${projectId}:${initial.candidateJobId}:${initial.checkJobId}:${initial.bindingHash}:${initial.candidateHash}`;
  const owner = useRef(identity); owner.current = identity;
  const [read, setRead] = useState<{ identity: string; status: ContentLanguageStatus }>();
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const notified = useRef<string | undefined>(undefined);
  const status = read?.identity === identity && !olderLanguageObservation(initial, read.status) ? read.status : initial;
  const observe = async (cancel = false) => {
    if (!status.checkJobId || busy || disabled) return;
    const current = identity; setBusy(true); setError("");
    try {
      const result = await (cancel ? contentLanguageApi.cancel : contentLanguageApi.reconcile)(projectId, status.checkJobId);
      if (owner.current !== current) return;
      acceptRetryRead(result);
    } catch (failure) { if (owner.current === current) setError(failure instanceof Error ? failure.message : "原语言检查暂时不可读。"); }
    finally { if (owner.current === current) setBusy(false); }
  };
  useEffect(() => { if (!disabled && !busy && !error && languageCheckPending(status)) {
    const timer = setTimeout(() => void observe(), 3000); return () => clearTimeout(timer);
  } }, [identity, disabled, busy, error, status]);
  useEffect(() => {
    if (disabled || !languageCheckPassed(status) || notified.current === identity) return;
    notified.current = identity; onVerified?.();
  }, [identity, status, disabled, onVerified]);
  const acceptRetryRead = (result: ContentLanguageStatus) => {
    if (result.checkJobId !== initial.checkJobId || result.candidateJobId !== initial.candidateJobId
      || result.candidateHash !== initial.candidateHash || result.bindingHash !== initial.bindingHash) throw new Error("原检查来源不匹配，请重新读取。");
    if (owner.current === identity) setRead(previous => previous?.identity === identity && olderLanguageObservation(previous.status, result) ? previous : { identity, status: result });
  };
  const retryManual = async (body: FailedExecution & { commandId: string }) => {
    if (disabled || busy || !status.checkJobId || status.retry?.state !== "exhausted"
      || body.failedJobId !== status.retry.currentJobId || body.failedAttemptId !== status.retry.currentAttemptId) throw new Error("失败尝试已变化，请读取原检查。");
    setBusy(true);
    try { acceptRetryRead(await contentLanguageApi.retry(projectId, status.checkJobId, { ...body, failedAttemptId: body.failedAttemptId! })); }
    finally { if (owner.current === identity) setBusy(false); }
  };
  const readCurrent = async () => {
    if (!status.checkJobId) throw new Error("缺少原检查任务。");
    acceptRetryRead(await contentLanguageApi.reconcile(projectId, status.checkJobId));
  };
  return <><ContentLanguageEvidence status={status} />
    <Button disabled={disabled || busy || !status.checkJobId} onClick={() => void observe()}>核对原语言检查</Button>
    {status.state === "spawn_intent" && onContinue && <Button disabled={disabled || busy} onClick={onContinue}>继续原候选的语言检查</Button>}
    {languageCheckPending(status) && <Button disabled={disabled || busy} onClick={() => void observe(true)}>取消此语言检查</Button>}
    <ManualExecutionRetry identity={identity} status={status.retry} disabled={disabled || busy} onRetry={retryManual} onObserve={readCurrent} />
    {error && <ErrorNotice message={error} />}
  </>;
}
