import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button } from "../components";

/** Keyed by project/job: late clipboard or GET results belong to that task only. */
export function OutlineAssignment({ projectId, jobId }: { projectId: string; jobId: string }) {
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [copyState, setCopyState] = useState<"idle" | "copying" | "copied" | "failed">("idle");
  const [attempt, setAttempt] = useState(0);
  const owner = useRef<object | null>(null);
  useEffect(() => {
    const session = {};
    owner.current = session;
    setError("");
    void plotloomApi.getOutlineAssignment(projectId, jobId).then((result) => {
      if (owner.current === session) setAssignment(result.assignment);
    }).catch(() => {
      if (owner.current === session) setError("无法读取完整任务。请重试；不要重复准备任务。");
    });
    return () => { owner.current = null; };
  }, [projectId, jobId, attempt]);

  const copy = async () => {
    const session = owner.current;
    setCopyState("copying");
    try {
      await navigator.clipboard.writeText(assignment);
      if (owner.current === session) setCopyState("copied");
    } catch {
      if (owner.current === session) setCopyState("failed");
    }
  };

  return <section aria-label="大纲任务交接">
    <p>复制完整任务，粘贴给同机 Codex 执行。准备或复制不会启动生成；大纲返回后仍由你审核确认。</p>
    {error ? <><p role="alert">{error}</p><Button onClick={() => setAttempt((value) => value + 1)}>重试读取任务</Button></> : !assignment ? <p role="status">正在读取完整任务…</p> : <>
      <Button disabled={copyState === "copying"} onClick={() => void copy()}>复制完整任务</Button>
      {copyState === "copied" && <p role="status">已复制完整任务，可直接粘贴执行。</p>}
      {copyState === "failed" && <p role="alert">复制失败。请点击下方任务文本全选后手动复制。</p>}
      <label>完整任务<textarea aria-label="specialist assignment" readOnly value={assignment} rows={8} onFocus={(event) => event.currentTarget.select()} /></label>
    </>}
  </section>;
}
