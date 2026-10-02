import { useEffect, useRef, useState } from "react";
import { Button, ErrorNotice } from "../../components";
import { specialistsApi, type SpecialistStage, type SpecialistTask } from "./api";

const labels = { prepared: "任务已准备，尚未发送", queued: "已发送，等待结果", outcome_unknown: "发送结果不确定，请勿重复发送", completed: "结果已交付，请审核" };

export function SpecialistTaskActions({ projectId, stage, jobId, disabled, sendDisabled = false, onDelivered }: { projectId: string; stage: SpecialistStage; jobId: string; disabled: boolean; sendDisabled?: boolean; onDelivered: () => unknown }) {
  const [task, setTask] = useState<SpecialistTask>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const callback = useRef(onDelivered); callback.current = onDelivered;
  const generation = useRef(0);
  const operation = useRef(false);
  useEffect(() => {
    const owner = ++generation.current;
    setTask(undefined); setError(""); setBusy(false); operation.current = false;
    const load = () => { void specialistsApi.status(projectId, stage, jobId).then(value => { if (generation.current === owner) setTask(value); }).catch(reason => { if (generation.current === owner) setError(String(reason)); }); };
    load(); window.addEventListener("plotloom-specialists-changed", load);
    return () => { generation.current++; window.removeEventListener("plotloom-specialists-changed", load); };
  }, [projectId, stage, jobId]);
  const act = async (send = false) => {
    if (disabled || operation.current || (send && sendDisabled)) return;
    const owner = generation.current; operation.current = true; setBusy(true); setError("");
    try {
      const result = await (send ? specialistsApi.send : specialistsApi.check)(projectId, stage, jobId);
      if (owner !== generation.current) return;
      setTask(current => ({ ...current, ...result }));
      if (result.state === "completed") await callback.current();
    } catch (reason) {
      if (owner !== generation.current) return;
      setError(reason instanceof Error ? reason.message : "任务操作失败。");
      // Read the durable receipt after failed send; never offer an automatic retry.
      if (send) { const result = await specialistsApi.status(projectId, stage, jobId).catch(() => undefined); if (owner === generation.current && result) setTask(result); }
    } finally { if (owner === generation.current) { operation.current = false; setBusy(false); } }
  };
  useEffect(() => {
    if (disabled || busy || error || !task || !["queued", "outcome_unknown"].includes(task.state)) return;
    const timer = window.setTimeout(() => { void act(); }, 3000);
    return () => window.clearTimeout(timer);
  });
  return <section aria-label="助手任务"><p role="status">{task ? labels[task.state] : "正在读取任务状态…"}</p>
    {task && !task.configured && task.state === "prepared" && <p>请先打开侧栏的「生成助手设置」，填写文字创作助手的聊天 ID。</p>}
    <div className="button-row">{task?.state === "prepared" && <Button variant="primary" disabled={disabled || sendDisabled || busy || !task.configured} onClick={() => void act(true)}>发送给文字创作助手</Button>}
      <Button disabled={disabled || busy || !task} onClick={() => void act()}>检查任务结果</Button></div>
    <small>页面打开时会自动检查已发送任务。交付后仍需你审核确认；取消提案不会中止助手执行。</small>
    {error && <ErrorNotice message={error} />}
  </section>;
}
