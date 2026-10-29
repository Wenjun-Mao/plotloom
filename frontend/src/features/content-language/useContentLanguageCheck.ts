import { useEffect, useRef, useState } from "react";
import type { FailedExecution } from "../generation-retry/ManualExecutionRetry";
import { automaticRetryCount } from "../generation-retry/AutomaticRetryCount";
import { contentLanguageApi } from "./api";
import { candidateIdentity, olderLanguageObservation, languageCheckPassed, languageCheckPending, type ContentLanguageStage, type ContentLanguageStatus } from "./contracts";

type Options = { projectId: string; stage: ContentLanguageStage; jobId?: string; candidate?: Record<string, unknown> | null;
  original?: Record<string, unknown> | null; basis?: string; disabled?: boolean; initial?: ContentLanguageStatus | null };
/** Only an exact complete-candidate result can authorize this editor snapshot. Reads never admit work. */
export function useContentLanguageCheck({ projectId, stage, jobId, candidate, original, basis = "", disabled = false, initial }: Options) {
  const text = candidateIdentity(candidate), unchanged = candidate === undefined || text === candidateIdentity(original);
  const settingsKey = JSON.stringify([projectId, stage, jobId, text, basis]);
  const key = JSON.stringify([settingsKey, disabled]);
  const identity = useRef({ key }); if (identity.current.key !== key) identity.current = { key };
  const owner = identity.current;
  const [read, setRead] = useState<{ owner: typeof owner; value?: ContentLanguageStatus; exact?: boolean; error?: string }>();
  const [allowance, setAllowance] = useState<{ key: string; value: string }>();
  const retryValue = allowance?.key === settingsKey ? allowance.value : "1";
  const [pending, setPending] = useState<object | null>(null);
  const flight = useRef<object | null>(null);
  const current = read?.owner === owner ? read : undefined, status = current?.value;
  const enabled = !!jobId && !disabled && candidate !== null;
  const owns = () => identity.current === owner;
  const receive = (value: ContentLanguageStatus, expectedCheck?: string, exact = false) => {
    if (!owns()) return;
    if (value.candidateJobId !== jobId || expectedCheck && value.checkJobId !== expectedCheck) throw new Error("语言检查返回了不同的候选或原检查任务，未采用结果。");
    if (expectedCheck && status && (value.candidateHash !== status.candidateHash || value.bindingHash !== status.bindingHash)) throw new Error("当前检查来源不匹配，结果未采用。");
    setRead(previous => previous?.owner === owner && olderLanguageObservation(previous.value, value) ? previous : { owner, value, exact });
  };
  const perform = async (operation: () => Promise<ContentLanguageStatus>, expectedCheck?: string, exact = current?.exact ?? false) => {
    if (!enabled || flight.current === owner) return;
    flight.current = owner; setPending(owner);
    try { receive(await operation(), expectedCheck, exact); }
    catch (error) { if (owns()) setRead({ owner, value: status, error: `语言检查结果待核实；原候选仍保留，尚不能采用。${error instanceof Error ? error.message : String(error)}` }); }
    finally { if (flight.current === owner) flight.current = null; if (owns()) setPending(null); }
  };
  useEffect(() => {
    setRead(undefined); setPending(null);
    if (!enabled || !unchanged) return;
    const abort = new AbortController();
    void contentLanguageApi.status(projectId, stage, jobId!, abort.signal).then(value => {
      if (!abort.signal.aborted && owns()) receive(value, undefined, candidate === undefined);
    }).catch(error => { if (!abort.signal.aborted && owns()) setRead({ owner, error: error instanceof Error ? error.message : "无法读取内容语言检查。" }); });
    return () => { abort.abort(); };
  }, [owner]);
  useEffect(() => {
    if (!enabled || !status?.checkJobId || !languageCheckPending(status) || pending === owner || document.visibilityState === "hidden") return;
    const timer = setTimeout(() => void perform(() => contentLanguageApi.reconcile(projectId, status.checkJobId!), status.checkJobId!), 3000);
    return () => clearTimeout(timer);
  }, [owner, status, pending]);
  const visibleStatus = status || (unchanged && initial?.candidateJobId === jobId ? initial : undefined);
  const frozen = !!visibleStatus?.checkJobId;
  const retryLimit = frozen ? visibleStatus?.retry?.automaticRetryLimit ?? undefined : automaticRetryCount(retryValue);
  const observeExisting = frozen && (languageCheckPending(visibleStatus) || current?.exact || ["failed", "settled"].includes(visibleStatus?.state || ""));
  const acceptCurrent = (value: ContentLanguageStatus) => {
    if (!visibleStatus?.checkJobId || value.checkJobId !== visibleStatus.checkJobId
      || value.candidateHash !== visibleStatus.candidateHash || value.bindingHash !== visibleStatus.bindingHash) throw new Error("检查来源或任务标识已变化，请读取当前候选。");
    receive(value, visibleStatus.checkJobId, current?.exact ?? false);
  };
  const observeCurrent = async () => {
    if (!enabled || !visibleStatus?.checkJobId) throw new Error("请先读取当前检查。");
    const value = await contentLanguageApi.reconcile(projectId, visibleStatus.checkJobId);
    if (owns()) acceptCurrent(value);
  };
  const retryManual = async (body: FailedExecution & { commandId: string }) => {
    if (!enabled || flight.current === owner || visibleStatus?.retry?.state !== "exhausted" || !visibleStatus.checkJobId
      || body.failedJobId !== visibleStatus.retry.currentJobId || body.failedAttemptId !== visibleStatus.retry.currentAttemptId) throw new Error("失败任务已变化，请先读取当前检查。");
    flight.current = owner; setPending(owner);
    try {
      const value = await contentLanguageApi.retry(projectId, visibleStatus.checkJobId, { ...body, failedAttemptId: body.failedAttemptId! });
      if (owns()) acceptCurrent(value);
    } finally { if (flight.current === owner) flight.current = null; if (owns()) setPending(null); }
  };
  return { identity: settingsKey, retryManual, observeCurrent, status: visibleStatus, ready: enabled && !!current?.exact && !current.error && languageCheckPassed(status), busy: pending === owner,
    error: current?.error || "", edited: !unchanged, exact: !!current?.exact,
    retryValue, setRetryValue: (value: string) => { if (!frozen) setAllowance({ key: settingsKey, value }); }, retryFrozen: frozen,
    retryValid: frozen || retryLimit !== undefined, observeExisting,
    check: () => !frozen && retryLimit === undefined ? Promise.resolve() : perform(() => observeExisting
      ? contentLanguageApi.reconcile(projectId, visibleStatus!.checkJobId!)
      : contentLanguageApi.check(projectId, stage, jobId!, candidate ?? undefined, retryLimit),
      observeExisting ? visibleStatus!.checkJobId! : undefined, observeExisting ? current?.exact ?? false : true),
    canContinue: visibleStatus?.state === "spawn_intent" && visibleStatus.retry?.state !== "retry_pending",
    continuePrepared: () => visibleStatus?.state === "spawn_intent" && visibleStatus.checkJobId && visibleStatus.retry?.state !== "retry_pending"
      ? perform(() => contentLanguageApi.check(projectId, stage, jobId!, current?.exact ? candidate ?? undefined : undefined, retryLimit), visibleStatus.checkJobId) : Promise.resolve(),
    cancel: () => visibleStatus?.checkJobId ? perform(() => contentLanguageApi.cancel(projectId, visibleStatus.checkJobId!), visibleStatus.checkJobId) : Promise.resolve(),
    disabled: !enabled || unchanged && !status };
}
