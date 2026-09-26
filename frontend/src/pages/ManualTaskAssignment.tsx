import { useEffect, useRef, useState } from "react";
import { Button } from "../components";

/** Preparation returns a manual task only; copying it is a separate user action. */
export function ManualTaskAssignment({ assignment, taskName }: { assignment: string; taskName: string }) {
  const [copyState, setCopyState] = useState<"idle" | "copying" | "copied" | "failed">("idle");
  const owner = useRef<object | null>(null);
  useEffect(() => {
    const session = {};
    owner.current = session;
    setCopyState("idle");
    return () => { if (owner.current === session) owner.current = null; };
  }, [assignment]);
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

  return <section aria-label={`${taskName}任务`}>
    <p>任务已准备好；复制不会发送或启动生成。执行结果返回后仍需由你审阅确认。</p>
    <Button disabled={copyState === "copying"} onClick={() => void copy()}>{copyState === "copying" ? "正在复制…" : "复制完整任务"}</Button>
    {copyState === "copied" && <p role="status">已复制完整任务，可直接粘贴执行。</p>}
    {copyState === "failed" && <p role="alert">复制失败。请点击下方任务文本全选后手动复制。</p>}
    <label>完整任务（可复制）<textarea aria-label={`${taskName}完整任务`} readOnly value={assignment} rows={8} onFocus={(event) => event.currentTarget.select()} /></label>
  </section>;
}
