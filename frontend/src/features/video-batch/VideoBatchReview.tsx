import { durationDeviationNotice } from "../../video-backends/minimax-h3-timing";
import { GenerationRetryStatus } from "../generation-retry/GenerationRetryStatus";
import { useEffect, useRef, useState } from "react";
import { Button, Spinner } from "../../components";
import { batchApi } from "./api";
import type { Batch, Review } from "./contracts";
import type { QaActor } from "../../components/ProjectQaContext";
import { ProductionBriefReview } from "./production-review";
import { RejectedTakeReplacement } from "./RejectedTakeReplacement";

export function VideoBatchReview({ projectId, batch, disabled, actor = null, onBatchRead, onReplaced, onConfirmStart, onClose, onSaved }: {
  projectId: string; batch: Batch; disabled: boolean; onConfirmStart?: () => void; onClose: () => void; onSaved: () => Promise<void>;
  actor?: QaActor | null; onBatchRead?: (batch: Batch) => void; onReplaced?: (batch: Batch) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const command = useRef(false); const active = useRef(true);
  const [review, setReview] = useState<Review | null>(null); const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false); const [retry, setRetry] = useState(0);
  const [replacementBusy, setReplacementBusy] = useState(false);
  useEffect(() => {
    active.current = true; dialog.current?.showModal(); const abort = new AbortController();
    setReview(null); setError("");
    batchApi.review(projectId, abort.signal).then(value => {
      if (abort.signal.aborted) return;
      if (value.batchId !== batch.id) throw new Error("当前视频清单已变化，请关闭并重新读取原批次；不能沿用其他清单的确认。");
      setReview(value);
    })
      .catch(failure => { if (!abort.signal.aborted) setError(String(failure)); });
    return () => { active.current = false; abort.abort(); };
  }, [projectId, batch.id, retry]);
  async function confirmPack() {
    if (!review?.ready || command.current || disabled || uncertain || replacementBusy) return;
    onConfirmStart?.();
    command.current = true; setBusy(true); setError(""); let saved = false;
    try {
      await batchApi.confirmPack(projectId, { expectedRevision: batch.revision, reviewHash: review.reviewHash,
        basis: "source-bound-selections.v1", attribution: actor ?? { kind: "unnamed_creator" } });
      saved = true;
      if (active.current) await onSaved();
    } catch (failure) { if (active.current) { setUncertain(!saved); setError(saved ? `已保存全部视频确认；刷新失败：${String(failure)}` : `保存结果待核实：${String(failure)}。请重新读取原批次，不要重复确认。`); } }
    finally { command.current = false; if (active.current) setBusy(false); }
  }
  return <dialog ref={dialog} className="autopilot-review-dialog video-batch-review" aria-labelledby="video-pack-title" onCancel={event => { event.preventDefault(); if (!busy && !replacementBusy) onClose(); }}>
    <header><div><h2 id="video-pack-title">视频素材与播放窗口</h2><p>可选观看或聆听素材。选择会记录当前来源、素材字节和播放窗口，不表示已检查或认可媒体质量。</p></div><Button autoFocus disabled={busy || replacementBusy} onClick={onClose}>关闭</Button></header>
    {!review && !error && <Spinner label="读取全部视频与逐帧窗口" />}
    {error && <p role="alert">{error}</p>}
    {uncertain && <Button onClick={async () => { const current = await batchApi.current(projectId); if (current?.id === batch.id && current.state === "approved") await onSaved(); else setError("原批次尚未报告已保存确认；保留审阅与原请求，请稍后重新读取，不会重放确认。"); }}>核对原批次保存结果</Button>}
    {!review && error && <Button onClick={() => setRetry(value => value + 1)}>重新读取原批次</Button>}
    {review && <><p>{review.readyCount}/{review.proposals.length} 个播放提案就绪 · {review.kept.length} 个既有选择保持原样 · {review.blockedCount} 项阻碍</p>
      {review.errors.map((item, index) => <p role="alert" key={index}><a href={`#batch-review-${item.shotId}`}>{item.shotId}</a> · {item.message}</p>)}
      <div className="video-batch-gallery">{review.proposals.map(item => <article key={item.shotId} id={`batch-review-${item.shotId}`}>
        <h3>{item.title} · {item.shotId}</h3>
        {batch.manifest.targets.filter(target => target.shotId === item.shotId).map(target => <ProductionBriefReview key={target.shotId} target={target} />)}
        {item.segment && <><video controls preload="none" src={`/api/v2/projects/${encodeURIComponent(projectId)}/video-segments/${encodeURIComponent(item.segmentId)}/preview`} />
          <p>播放 {item.segment.inFrame}–{item.segment.outFrame} 帧 · {((item.segment.outFrame - item.segment.inFrame) / 24).toFixed(2)} 秒 · 目标 {item.segment.authoredDurationUnits / 1000} 秒 · 24 fps · 原生音频</p></>}
        {item.segment && item.job?.observed && <small className="warning">{durationDeviationNotice(item.segment.authoredDurationUnits, item.job.observed.durationSeconds)}</small>}
        <GenerationRetryStatus status={item.job?.retry} />
        {item.error && <p role="alert">{item.error}</p>}
        <details><summary>原片与生成证据</summary><p>请求 {item.job?.requestedSeconds} 秒 · 原片与播放窗口分别审阅。</p>
          <a href={`/api/v2/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(item.jobId)}/media`} target="_blank" rel="noreferrer">打开完整原片并聆听</a>
          <pre>{JSON.stringify(item.job?.snapshot, null, 2)}</pre></details>
        <p><a href={`?project=${encodeURIComponent(projectId)}&stage=storyboard&entity=${encodeURIComponent(`shot:${item.shotId}`)}#shot-original`} onClick={onClose}>打开这个镜头的手动视频制作，调整窗口或处理拒绝</a></p>
      </article>)}</div>
      {onBatchRead && onReplaced && <RejectedTakeReplacement projectId={projectId} batch={batch} review={review} disabled={disabled || busy} actor={actor}
        onPending={setReplacementBusy} onRead={(value, updated) => { onBatchRead(value); setReview(updated); }} onSuccess={onReplaced} />}
      <footer><p>选择会保留来源、素材字节和技术播放窗口。观看、聆听及质量评价都是可选的。</p>
        <Button variant="primary" busy={busy} disabled={busy || replacementBusy || disabled || uncertain || !review.ready} onClick={() => void confirmPack()}>{busy ? "正在保存素材选择…" : "选择全部素材用于故事"}</Button></footer>
    </>}
  </dialog>;
}
