import { useEffect, useRef, useState } from "react";
import type { VideoJob, VideoSegment } from "./types";
import { plotloomApi } from "./api";
import { Button } from "./components";

function authoredUnits(job: VideoJob): number | null {
  const binding = job.snapshot.sourceTiming;
  if (!binding || typeof binding !== "object") return null;
  const units = (binding as Record<string, unknown>).durationUnits;
  return typeof units === "number" && Number.isInteger(units) ? units : null;
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
  useEffect(() => {
    const targetId = `video-segment-review-${job.id}`;
    if (window.location.hash === `#${targetId}`) {
      document.getElementById(targetId)?.scrollIntoView({ block: "start" });
    }
  }, [job.id]);
  const available = (job.segments ?? []).filter((segment) => segment.current);
  const rejected = job.reviews.at(-1)?.decision === "reject";
  const chosen: VideoSegment | undefined = available.find((segment) => segment.id === proposalId)
    ?? available[available.length - 1];
  const timingReady = job.state === "ingested" && job.current && !rejected && sourceUnits != null
    && [6_000, 8_000].includes(sourceUnits) && Number.isInteger(requiredFrames)
    && job.requestedSeconds === 8 && availableFrames >= requiredFrames;
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
      if (activeRef.current && request === requestRef.current) setError(reason instanceof Error ? reason.message : "播放片段准备失败");
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  const select = async () => {
    if (!chosen || !chosen.current || rejected || busy || !reviewer.trim() || !note.trim()) return;
    const request = ++requestRef.current;
    setBusy(true); setError("");
    try {
      await plotloomApi.selectVideoSegment(
        projectId, chosen.id, reviewer.trim(), note.trim(), job.selectionRevision,
      );
      if (!activeRef.current || request !== requestRef.current) return;
      await onRefresh();
    } catch (reason) {
      if (activeRef.current && request === requestRef.current) setError(reason instanceof Error ? reason.message : "片段选择失败");
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  const reject = async () => {
    if (busy || rejected || !reviewer.trim() || !note.trim()
      || !window.confirm("拒绝此原片并撤销当前选择？原片与片段证据会保留。")) return;
    const request = ++requestRef.current;
    setBusy(true); setError("");
    try {
      await plotloomApi.reviewVideoJob(projectId, job.id, "reject", reviewer.trim(), note.trim(), job.selectionRevision);
      if (!activeRef.current || request !== requestRef.current) return;
      await onRefresh();
    } catch (reason) {
      if (activeRef.current && request === requestRef.current) setError(reason instanceof Error ? reason.message : "原片拒绝未完成");
    } finally {
      if (activeRef.current && request === requestRef.current) setBusy(false);
    }
  };
  return <section id={`video-segment-review-${job.id}`} className="video-segment-review" data-testid={`video-segment-review-${job.id}`}>
    <strong>镜头播放时长与人工选择</strong>
    <small>原稿镜头时长：{sourceUnits == null ? "来源不可用" : `${(sourceUnits / 1000).toFixed(3)} 秒`}；后端请求时长：{job.requestedSeconds} 秒；实测原片：{job.observed ? `${job.observed.durationSeconds.toFixed(3)} 秒 / ${availableFrames} 帧` : "尚无输出"}。</small>
    <small>原片保留不变。选择连续的 {Number.isInteger(requiredFrames) ? requiredFrames : "—"} 帧及同期声音；片段准备后须听看最终片段，再明确选择。此操作不自动确认创作质量。</small>
    {rejected && <small className="notice warning">此原片已拒绝；不能重新选择其片段。请选择另一候选或重新生成。原片与片段证据仍保留。</small>}
    {!timingReady && !rejected && <small className="notice warning">此候选没有可核验的 24 fps、6/8 秒原稿与合格 8 秒原片组合；不能准备播放片段。</small>}
    {timingReady && <label>片段入点（帧）
      <input type="number" min={0} max={maxStart} step={1} value={inFrame} disabled={readOnly || busy}
        onChange={(event) => setInFrame(Math.max(0, Math.min(maxStart, Math.trunc(Number(event.target.value) || 0))))} />
      <small>出点（不含）：{inFrame + requiredFrames} / 原片 {availableFrames} 帧。六秒镜头须恰好 144 帧；不按浏览器时间自动裁切。</small>
    </label>}
    <Button disabled={readOnly || busy || !timingReady} onClick={() => void prepare()}>准备此连续片段（不选择）</Button>
    {available.length > 0 && <label>待审片段
      <select value={chosen?.id ?? ""} disabled={readOnly || busy} onChange={(event) => setProposalId(event.target.value)}>
        {available.map((item) => <option key={item.id} value={item.id}>{item.inFrame}–{item.outFrame} 帧{item.selected ? " · 已选择" : " · 待审"}</option>)}
      </select>
    </label>}
    {chosen && <>
      <video key={chosen.id} controls preload="metadata" src={plotloomApi.videoSegmentPreviewUrl(projectId, chosen.id)}
        data-testid={`video-segment-preview-${chosen.id}`}
        onPlay={(event) => document.querySelectorAll<HTMLVideoElement>("[data-testid^='video-job-player-'], [data-testid^='video-segment-preview-']").forEach((video) => { if (video !== event.currentTarget) video.pause(); })} />
      <small>已审核播放片段：{chosen.selected ? "当前已明确选择" : "尚未选择"}；{chosen.inFrame}–{chosen.outFrame} 帧。请检查对白、动作、字幕和首尾声音是否完整。</small>
    </>}
    <label>选择人<input value={reviewer} disabled={readOnly || busy || rejected} onChange={(event) => setReviewer(event.target.value)} /></label>
    <label>片段审核说明<textarea value={note} disabled={readOnly || busy || rejected} onChange={(event) => setNote(event.target.value)} /></label>
    {chosen && <Button disabled={readOnly || busy || rejected || !chosen.current || !reviewer.trim() || !note.trim()} onClick={() => void select()}>确认选择此播放片段</Button>}
    <Button variant="danger" disabled={readOnly || busy || rejected || !job.current || !reviewer.trim() || !note.trim()} onClick={() => void reject()}>拒绝此原片并撤销选择</Button>
    {error && <small className="notice warning" role="status">{error}</small>}
  </section>;
}
