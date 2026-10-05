import { useEffect, useRef, useState } from "react";
import { Button, ErrorNotice, Spinner } from "../../components";
import { SpecialistApiError, specialistsApi, type SpecialistStage, type SpecialistTask } from "./api";

const labels = { prepared: "任务已准备，尚未发送", queued: "已发送，等待助手返回结果", outcome_unknown: "发送结果不确定，正在核对交付；请勿重复发送", completed: "结果已交付，请审核" };
const transient = (error: unknown) => error instanceof TypeError || error instanceof SpecialistApiError && [408, 429, 500, 502, 503, 504].includes(error.status);

export function SpecialistTaskActions({ projectId, stage, jobId, disabled, sendDisabled = false, onDelivered }: { projectId: string; stage: SpecialistStage; jobId: string; disabled: boolean; sendDisabled?: boolean; onDelivered: () => unknown }) {
  const [task, setTask] = useState<SpecialistTask>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recovering, setRecovering] = useState(false);
  const [failures, setFailures] = useState(0);
  const [lastCheck, setLastCheck] = useState("");
  const reload = useRef<() => Promise<void>>(async () => {});
  const [visible, setVisible] = useState(document.visibilityState !== "hidden");
  const callback = useRef(onDelivered); callback.current = onDelivered;
  const generation = useRef(0);
  const operation = useRef(false);
  const pending = task && ["queued", "outcome_unknown"].includes(task.state);
  useEffect(() => {
    const changed = () => setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", changed);
    return () => document.removeEventListener("visibilitychange", changed);
  }, []);
  useEffect(() => {
    const owner = ++generation.current;
    setTask(undefined); setError(""); setBusy(false); setRecovering(false); setFailures(0); setLastCheck(""); operation.current = false;
    const load = async () => {
      if (operation.current) return;
      operation.current = true;
      try {
        const value = await specialistsApi.status(projectId, stage, jobId);
        if (generation.current === owner) {
          setTask(value); setError(""); setRecovering(false); setFailures(0); setLastCheck(new Date().toLocaleTimeString());
          if (value.state === "completed") await callback.current();
        }
      } catch (reason) { if (generation.current === owner) { setError(String(reason)); setRecovering(transient(reason)); setFailures(value => value + 1); } }
      finally { if (generation.current === owner) operation.current = false; }
    };
    reload.current = load;
    void load(); window.addEventListener("plotloom-specialists-changed", load);
    return () => { generation.current++; window.removeEventListener("plotloom-specialists-changed", load); };
  }, [projectId, stage, jobId]);
  const act = async (send = false) => {
    if (disabled || operation.current || (send && sendDisabled)) return;
    const owner = generation.current; operation.current = true; setBusy(true); setError(""); setRecovering(false);
    try {
      const result = await (send ? specialistsApi.send : specialistsApi.check)(projectId, stage, jobId);
      if (owner !== generation.current) return;
      setTask(current => ({ ...current, ...result })); setFailures(0);
      if (!send) setLastCheck(new Date().toLocaleTimeString());
      if (result.state === "completed") await callback.current();
    } catch (reason) {
      if (owner !== generation.current) return;
      const retry = !send && transient(reason);
      setRecovering(retry); setFailures(value => value + 1);
      setError(`${reason instanceof Error ? reason.message : "任务读取失败。"}${retry ? " 暂时无法读取，将自动重试；原任务仍保留。" : " 请检查助手交付与当前版本，修正后立即检查或刷新；请勿重复发送。"}`);
      // A failed send is never retried. Read only its durable reservation/receipt.
      if (send) { const result = await specialistsApi.status(projectId, stage, jobId).catch(() => undefined); if (owner === generation.current && result) setTask(result); }
    } finally { if (owner === generation.current) { operation.current = false; setBusy(false); } }
  };
  useEffect(() => {
    if (disabled || busy || !visible || error && !recovering || !pending && !(recovering && !task)) return;
    const timer = window.setTimeout(() => { if (task) void act(); else void reload.current(); }, Math.min(3000 * 2 ** Math.min(failures, 4), 30000));
    return () => window.clearTimeout(timer);
  });
  useEffect(() => {
    if (visible && pending && !busy && (!error || recovering)) void act();
  }, [visible]); // Returning to a visible page checks this exact task, never sends.
  return <section className="specialist-task-actions" aria-label="助手任务">
    <strong>{task ? labels[task.state] : error ? "无法读取任务状态" : "正在读取任务状态…"}</strong>
    {pending && (error && !recovering ? <p role="status">自动检查已暂停，请处理错误后立即检查。</p> : <Spinner label={recovering ? "等待重试读取" : visible ? "自动检查交付中" : "页面隐藏，返回后继续检查"} />)}
    {lastCheck && <p className="action-prerequisite">最近成功检查：<time>{lastCheck}</time></p>}
    {task && !task.configured && task.state === "prepared" && <p>请先打开侧栏的「生成助手设置」，填写文字创作助手的聊天 ID。</p>}
    <div className="button-row">{task?.state === "prepared" && <Button variant="primary" busy={busy} disabled={disabled || sendDisabled || busy || !task.configured} onClick={() => void act(true)}>{busy ? "正在处理任务…" : "发送给文字创作助手"}</Button>}
      {task?.state !== "completed" && <Button variant="quiet" busy={busy} disabled={disabled || busy || !task} onClick={() => void act()}>{busy ? "正在检查…" : "立即检查"}</Button>}
      {!task && error && <Button variant="quiet" disabled={disabled || busy} onClick={() => void reload.current()}>重试读取任务状态</Button>}</div>
    {sendDisabled && <small>来源上下文已变化，请更新当前提案后再发送。</small>}
    <small>排队回执不代表助手已开始执行。交付后仍需你审核确认；取消提案不会中止助手执行。</small>
    {error && <ErrorNotice message={error} />}
  </section>;
}
