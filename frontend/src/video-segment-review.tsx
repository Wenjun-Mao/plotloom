import { useEffect, useRef, useState } from "react";
import type { VideoJob, VideoSegment } from "./types";
import { ApiError, plotloomApi } from "./api";
import { Button } from "./components";

function authoredUnits(job: VideoJob): number | null {
  const binding = job.snapshot.sourceTiming;
  if (!binding || typeof binding !== "object") return null;
  const units = (binding as Record<string, unknown>).durationUnits;
  return typeof units === "number" && Number.isInteger(units) ? units : null;
}

function reviewError(reason: unknown, fallback: string): string {
  if (reason instanceof ApiError) {
    if (reason.status === 409) return "镜头或选择状态已变化。请刷新镜头，重新核对原片和片段后再确认。";
    if (reason.status === 422) return "此片段目前不满足选择条件。请检查片段范围和媒体状态，刷新后重试；原片不会被改动。";
  }
  return reason instanceof Error ? reason.message : fallback;
}

export function VideoSegmentReview({ projectId, job, readOnly, onRefresh }: {
  projectId: string;
  job: VideoJob;
  readOnly: boolean;
  onRefresh: () => Promise<void>;
}) {
  const sourceUnits = authoredUnits(job);
  const requiredFrames = sourceUnits != null ? sourceUnits * 24 / 1000 : NaN;
  const availableFrames = job.observed?.frameCount ?? 0;
  const maxStart = Number.isInteger(requiredFrames) ? Math.max(0, availableFrames - requiredFrames) : 0;
  const [inFrame, setInFrame] = useState(0);
  const [proposalId, setProposalId] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeRef = useRef(true);
  const requestRef = useRef(0);
  useEffect(() => {
    activeRef.current = true;
    setInFrame(0); setProposalId(""); setReviewer(""); setNote(""); setBusy(false); setError("");
    return () => { activeRef.current = false; requestRef.current += 1; };
  }, [projectId, job.id]);
  const available = (job.segments ?? []).filter((segment) => segment.current);
  const rejected = job.reviews.at(-1)?.decision === "reject";
  const chosen: VideoSegment | undefined = available.find((segment) => segment.id === proposalId)
    ?? available[available.length - 1];
  useEffect(() => {
    const targetId = window.location.hash.slice(1);
    if (!["video-segment-review", "video-segment-preview", "video-segment-confirm"].some((part) => targetId === `${part}-${job.id}`)) return;
    const frame = requestAnimationFrame(() => document.getElementById(targetId)?.scrollIntoView({ block: "start" }));
    return () => cancelAnimationFrame(frame);
  }, [job.id, chosen?.id]);
  const timingReady = job.state === "ingested" && job.current && !rejected && sourceUnits != null
    && sourceUnits > 0 && Number.isInteger(requiredFrames)
    && availableFrames >= requiredFrames;
  const prepare = async () => {
    if (!timingReady || busy) return;
    const request = ++requestRef.current;
    setBusy(true); setError("");
    try {
      const proposal = await plotloomApi.prepareVideoSegment(
        projectId, job.id, inFrame, inFrame + requiredFrames, job.selectionRevision,
      );
      if (!activeRef.current || request !== requestRef.current) return;
      setProposalId(proposal.id);
      await onRefresh();
    } catch (reason) {
      if (activeRef.current && request === requestRef.current) setError(reviewError(reason, "播放片段准备失败"));
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  const select = async () => {
    if (!chosen || !chosen.current || rejected || busy) return;
    const request = ++requestRef.current;
    setBusy(true); setError("");
    try {
      await plotloomApi.selectVideoSegment(
        projectId, chosen.id, reviewer.trim(), note.trim(), job.selectionRevision,
      );
      if (!activeRef.current || request !== requestRef.current) return;
      await onRefresh();
    } catch (reason) {
      if (activeRef.current && request === requestRef.current) setError(reviewError(reason, "片段选择失败"));
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  const reject = async () => {
    if (busy || rejected
      || !window.confirm("拒绝此原片并撤销当前选择？原片与片段证据会保留。")) return;
    const request = ++requestRef.current;
    setBusy(true); setError("");
    try {
      await plotloomApi.reviewVideoJob(projectId, job.id, "reject", reviewer.trim(), note.trim(), job.selectionRevision);
      if (!activeRef.current || request !== requestRef.current) return;
      await onRefresh();
    } catch (reason) {
      if (activeRef.current && request === requestRef.current) setError(reviewError(reason, "原片拒绝未完成"));
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  return <section id={`video-segment-review-${job.id}`} className="video-segment-review" data-testid={`video-segment-review-${job.id}`}>
    <strong>调整片段 · 预览 · 用于故事</strong>
    <small>原稿镜头时长：{sourceUnits == null ? "来源不可用" : `${(sourceUnits / 1000).toFixed(3)} 秒`}；后端请求时长：{job.requestedSeconds} 秒；实测原片：{job.observed ? `${job.observed.durationSeconds.toFixed(3)} 秒 / ${availableFrames} 帧` : "尚无输出"}。</small>
    <small>原片保留不变。选择连续的 {Number.isInteger(requiredFrames) ? requiredFrames : "—"} 帧及同期声音；片段准备后须听看最终片段，再明确选择。此操作不自动确认创作质量。</small>
    {rejected && <small className="notice warning">此原片已拒绝；不能重新选择其片段。请选择另一候选或重新生成。原片与片段证据仍保留。</small>}
    {!timingReady && !rejected && <small className="notice warning">此候选没有足够的已核验画面与声音覆盖当前原稿时长，或原稿时长不在 24 fps 帧网格上；不能准备播放片段。</small>}
    {timingReady && <label>片段入点（帧）
      <input type="number" min={0} max={maxStart} step={1} value={inFrame} disabled={readOnly || busy}
        onChange={(event) => setInFrame(Math.max(0, Math.min(maxStart, Math.trunc(Number(event.target.value) || 0))))} />
      <small>出点（不含）：{inFrame + requiredFrames} / 原片 {availableFrames} 帧。严格按原稿时长选择连续帧，不按浏览器时间自动裁切。</small>
    </label>}
    <Button disabled={readOnly || busy || !timingReady} onClick={() => void prepare()}>生成待审片段</Button>
    <small>只生成可预览的片段，不会加入故事。确认前请听看片段首尾。</small>
    {available.length > 0 && <label>待审片段
      <select value={chosen?.id ?? ""} disabled={readOnly || busy} onChange={(event) => setProposalId(event.target.value)}>
        {available.map((item) => <option key={item.id} value={item.id}>{item.inFrame}–{item.outFrame} 帧{item.selected ? " · 已选择" : " · 待审"}</option>)}
      </select>
    </label>}
    {chosen && <div className="segment-preview-step" id={`video-segment-preview-${job.id}`}>
      <video key={chosen.id} controls preload="metadata" src={plotloomApi.videoSegmentPreviewUrl(projectId, chosen.id)}
        data-testid={`video-segment-preview-${chosen.id}`}
        onPlay={(event) => document.querySelectorAll<HTMLVideoElement>("[data-testid^='video-job-player-'], [data-testid^='video-segment-preview-']").forEach((video) => { if (video !== event.currentTarget) video.pause(); })} />
      <small>{chosen.selected ? "已选择片段 · 正用于故事" : "待审片段 · 尚未用于故事"}；{chosen.inFrame}–{chosen.outFrame} 帧。请检查对白、动作、字幕和首尾声音是否完整。</small>
    </div>}
    <details className="review-annotations"><summary>审核记录（可选）</summary>
      <label>审核人（可选）<input value={reviewer} disabled={readOnly || busy || rejected} onChange={(event) => setReviewer(event.target.value)} /></label>
      <label>说明（可选）<textarea value={note} disabled={readOnly || busy || rejected} onChange={(event) => setNote(event.target.value)} /></label>
    </details>
    {chosen && <div className="segment-confirm-step" id={`video-segment-confirm-${job.id}`}>
      <small>确认只影响当前镜头的已核验片段；不会改动原片。</small>
      <Button disabled={readOnly || busy || rejected || !chosen.current} onClick={() => void select()}>确认用于故事</Button>
    </div>}
    <Button variant="danger" disabled={readOnly || busy || rejected || !job.current} onClick={() => void reject()}>拒绝此原片并撤销选择</Button>
    {error && <small className="notice warning" role="status">{error}</small>}
  </section>;
}
