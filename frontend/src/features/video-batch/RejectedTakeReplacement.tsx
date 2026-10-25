import { useEffect, useRef, useState } from "react";
import { useReviewEditorDraft } from "../authoring/ReviewDraftContext";
import { Button, Field } from "../../components";
import type { QaActor } from "../../components/ProjectQaContext";
import { batchApi } from "./api";
import type { Batch, Review } from "./contracts";

export function RejectedTakeReplacement({ projectId, batch, review, disabled, actor, onPending, onRead, onSuccess }: {
  projectId: string; batch: Batch; review: Review; disabled: boolean; actor: QaActor | null;
  onRead: (batch: Batch, review: Review) => void; onSuccess: (batch: Batch) => void;
  onPending: (pending: boolean) => void;
}) {
  const [shot, setShot] = useState(""); const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const pending = useRef(false); const uncertain = useRef(false);
  const rejected = review.proposals.filter(item => item.job?.reviews.at(-1)?.decision === "reject");
  const chosen = review.proposals.find(item => item.shotId === shot);
  useEffect(() => setReason(""), [shot]);
  const working = useReviewEditorDraft(projectId, "take_rejection", `${batch.id}:${review.reviewHash}:${chosen?.jobId ?? ""}:${chosen?.job?.selectionRevision ?? 0}`, setReason, disabled || busy || !chosen, undefined, chosen?.jobId || "");
  const attribution = actor ? { attribution: actor } : {};
  async function readOriginal() {
    const current = await batchApi.current(projectId);
    if (!current) throw new Error("原批次无法读取；不会重放请求。");
    if (current.id !== batch.id) {
      if (current.manifest.replacement?.batchId === batch.id) { onSuccess(current); return null; }
      throw new Error("当前批次已改变；请关闭并重新审阅，不能选择另一个前驱。");
    }
    const updated = await batchApi.review(projectId);
    onRead(current, updated); uncertain.current = false;
    return { current, updated };
  }
  async function act(operation: "reject" | "replace" | "read") {
    if (pending.current || disabled || operation === "reject" && working.stale) return;
    const clearApplied = working.clear;
    pending.current = true; setBusy(true); onPending(true); setMessage("");
    let completed = "";
    try {
      if (operation === "read") { await readOriginal(); setMessage("已核实持久状态；可继续显示的剩余操作。"); return; }
      if (uncertain.current) throw new Error("先核对原批次保存结果。");
      if (operation === "reject") {
        if (!chosen?.job || !reason.trim() || chosen.job.selected || chosen.job.reviews.at(-1)?.decision === "reject") return;
        await batchApi.reject(projectId, chosen.jobId, { decision: "reject", reviewer: "", note: reason.trim(),
          expectedSelectionRevision: chosen.job.selectionRevision, ...attribution });
        completed = "已保存此镜头的拒绝与修改原因。"; await clearApplied();
        setShot(""); setReason(""); await readOriginal(); setMessage(`${completed}尚未派发新视频。`);
        return;
      }
      const observed = await readOriginal();
      if (!observed) return;
      const { updated } = observed; let current = observed.current;
      const ids = updated.proposals.filter(item => item.job?.reviews.at(-1)?.decision === "reject").map(item => item.jobId);
      if (!ids.length || ids.length !== rejected.length || ids.some(id => !rejected.some(item => item.jobId === id)))
        throw new Error("拒绝集合已变化；请重新审阅当前镜头。");
      if (current.state !== "cancelled") {
        current = await batchApi.command(projectId, "control", { batchId: batch.id, expectedControlRevision: current.controlRevision, action: "cancel" });
        completed = "已取消原批次的新派发。"; onRead(current, updated);
      } else completed = "原批次已取消新派发。";
      const successor = await batchApi.command(projectId, "replace-rejected", { batchId: batch.id,
        expectedRevision: current.revision, rejectedJobIds: ids, setup: batch.manifest.setup, ...attribution });
      onSuccess(successor);
    } catch (error) {
      uncertain.current = true;
      setMessage(`${completed}操作结果待核实；核对持久状态后继续剩余操作，不会重放请求。${String(error)}`);
      try {
        const observed = await readOriginal();
        if (observed) setMessage(`已核实：${observed.updated.proposals.filter(item => item.job?.reviews.at(-1)?.decision === "reject").map(item => item.shotId).join("、") || "暂无镜头"}的拒绝状态已读取；${observed.current.state === "cancelled" ? "原批次已取消新派发，下一步准备后继清单" : "原批次尚未取消，下一步取消原批次并准备后继清单"}。原操作响应未确认，不会重放请求。${String(error)}`);
      } catch { /* Keep explicit read recovery available. */ }
    } finally { pending.current = false; setBusy(false); onPending(false); }
  }
  const frozen = batch.state === "approved" || !!batch.manifest.rejectedHistory?.some(item => item.jobId === chosen?.jobId);
  return <section aria-label="选择性重做镜头">
    {working.notice}
    {message && <p role="status">{message}</p>}
    {message && <Button disabled={busy || disabled} onClick={() => void act("read")}>核对原批次保存结果</Button>}
    {!frozen && <><Field label="选择要重新制作的镜头"><select value={shot} disabled={busy || disabled} onChange={event => setShot(event.target.value)}>
      <option value="">选择镜头…</option>{review.proposals.filter(item => item.job?.state === "ingested" && !item.job.selected && item.job.reviews.at(-1)?.decision !== "reject").map(item => <option key={item.shotId} value={item.shotId}>{item.title} · {item.shotId}</option>)}
    </select></Field>
    {shot && <><Field label="重做原因或期望变化"><textarea value={reason} disabled={busy || disabled || working.stale} onChange={event => { setReason(event.target.value); working.changed(event.target.value); }} /></Field>
      <p>将此原片保留为已拒绝历史；其他好镜头保留。此操作不发送新作业。</p>
      <Button disabled={busy || disabled || working.stale || !reason.trim()} onClick={() => void act("reject")}>保存拒绝与修改原因</Button></>}
    {review.proposals.map(item => item.job?.state === "ingested" && !item.job.selected && item.job.reviews.at(-1)?.decision !== "reject" && <Button key={item.shotId} disabled={busy || disabled} onClick={() => setShot(item.shotId)}>重新制作这个镜头… · {item.shotId}</Button>)}</>}
    {rejected.length > 0 && <><p>已拒绝：{rejected.map(item => item.shotId).join("、")}。仅为这些镜头创建后继清单；新方向仍须重新审阅并明确开始。</p>
      {rejected.map(item => <p key={item.jobId}>{item.shotId} · 拒绝原因：{item.job?.reviews.at(-1)?.note}</p>)}
      <Button disabled={busy || disabled || batch.state === "approved"} onClick={() => void act("replace")}>仅重做这些镜头</Button></>}
  </section>;
}
