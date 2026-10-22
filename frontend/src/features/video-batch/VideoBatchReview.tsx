import { useEffect, useRef, useState } from "react";
import { Button, Field, Spinner } from "../../components";
import { batchApi } from "./api";
import type { Batch, Review } from "./contracts";
import type { QaActor } from "../../components/ProjectQaContext";
import { RejectedTakeReplacement } from "./RejectedTakeReplacement";

export function VideoBatchReview({ projectId, batch, disabled, actor = null, onBatchRead, onReplaced, onConfirmStart, onClose, onSaved }: {
  projectId: string; batch: Batch; disabled: boolean; onConfirmStart?: () => void; onClose: () => void; onSaved: () => Promise<void>;
  actor?: QaActor | null; onBatchRead?: (batch: Batch) => void; onReplaced?: (batch: Batch) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const command = useRef(false); const active = useRef(true);
  const [review, setReview] = useState<Review | null>(null); const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const [note, setNote] = useState(""); const [busy, setBusy] = useState(false); const [retry, setRetry] = useState(0);
  const [failedMedia, setFailedMedia] = useState<Record<string, boolean>>({});
  const [replacementBusy, setReplacementBusy] = useState(false);
  const [visual, setVisual] = useState(""); const [audio, setAudio] = useState(""); const [evidence, setEvidence] = useState("");
  const inspectionReady = !actor || !!(visual.trim() && audio.trim() && evidence.trim());
  useEffect(() => {
    active.current = true; dialog.current?.showModal(); const abort = new AbortController();
    setReview(null); setError("");
    batchApi.review(projectId, abort.signal).then(value => { if (!abort.signal.aborted) setReview(value); })
      .catch(failure => { if (!abort.signal.aborted) setError(String(failure)); });
    return () => { active.current = false; abort.abort(); };
  }, [projectId, batch.id, retry]);
  async function confirmPack() {
    if (!review?.ready || command.current || disabled || uncertain || !inspectionReady || replacementBusy) return;
    onConfirmStart?.();
    command.current = true; setBusy(true); setError(""); let saved = false;
    try {
      await batchApi.confirmPack(projectId, { expectedRevision: batch.revision, reviewHash: review.reviewHash, basis: "whole-pack-video-native-audio.v1", note,
        ...(actor ? { attribution: actor, inspection: { clips: true, nativeAudio: true, intent: true, windows: true,
          visualObservation: visual.trim(), audioObservation: audio.trim(), evidenceRefs: evidence.split("\n").map(value => value.trim()).filter(Boolean) } } : {}) });
      saved = true;
      if (active.current) await onSaved();
    } catch (failure) { if (active.current) { setUncertain(!saved); setError(saved ? `已保存全部视频确认；刷新失败：${String(failure)}` : `保存结果待核实：${String(failure)}。请重新读取原批次，不要重复确认。`); } }
    finally { command.current = false; if (active.current) setBusy(false); }
  }
  return <dialog ref={dialog} className="autopilot-review-dialog video-batch-review" aria-labelledby="video-pack-title" onCancel={event => { event.preventDefault(); if (!busy && !replacementBusy) onClose(); }}>
    <header><div><h2 id="video-pack-title">审阅全部视频</h2><p>查看全部播放片段并聆听原生音频。一次确认所有显示的视频、意图与播放窗口；不会自动替你作出创作判断。</p></div><Button autoFocus disabled={busy || replacementBusy} onClick={onClose}>关闭审阅</Button></header>
    {!review && !error && <Spinner label="读取全部视频与逐帧窗口" />}
    {error && <p role="alert">{error}</p>}
    {uncertain && <Button onClick={async () => { const current = await batchApi.current(projectId); if (current?.state === "approved") await onSaved(); else setError("原批次尚未报告已保存确认；保留审阅与原请求，请稍后重新读取，不会重放确认。"); }}>核对原批次保存结果</Button>}
    {!review && error && <Button onClick={() => setRetry(value => value + 1)}>重新读取原批次</Button>}
    {review && <><p>{review.readyCount}/{review.proposals.length} 个播放提案就绪 · {review.kept.length} 个既有选择保持原样 · {review.blockedCount} 项阻碍</p>
      {review.errors.map((item, index) => <p role="alert" key={index}><a href={`#batch-review-${item.shotId}`}>{item.shotId}</a> · {item.message}</p>)}
      <div className="video-batch-gallery">{review.proposals.map(item => <article key={item.shotId} id={`batch-review-${item.shotId}`}>
        <h3>{item.title} · {item.shotId}</h3>
        {item.segment && <><video controls preload="none" src={`/api/v2/projects/${encodeURIComponent(projectId)}/video-segments/${encodeURIComponent(item.segmentId)}/preview`}
          onError={() => setFailedMedia(value => ({ ...value, [item.shotId]: true }))} onLoadedMetadata={() => setFailedMedia(value => ({ ...value, [item.shotId]: false }))} />
          <p>播放 {item.segment.inFrame}–{item.segment.outFrame} 帧 · {item.segment.authoredDurationUnits / 1000} 秒 · 24 fps · 原生音频</p></>}
        {item.error && <p role="alert">{item.error}</p>}
        <details><summary>原片与生成证据</summary><p>请求 {item.job?.requestedSeconds} 秒 · 原片与播放窗口分别审阅。</p>
          <a href={`/api/v2/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(item.jobId)}/media`} target="_blank" rel="noreferrer">打开完整原片并聆听</a>
          <pre>{JSON.stringify(item.job?.snapshot, null, 2)}</pre></details>
        <p><a href={`?project=${encodeURIComponent(projectId)}&stage=storyboard&entity=${encodeURIComponent(`shot:${item.shotId}`)}#shot-original`} onClick={onClose}>打开这个镜头的手动视频制作，调整窗口或处理拒绝</a></p>
      </article>)}</div>
      {onBatchRead && onReplaced && <RejectedTakeReplacement projectId={projectId} batch={batch} review={review} disabled={disabled || busy} actor={actor}
        onPending={setReplacementBusy} onRead={(value, updated) => { onBatchRead(value); setReview(updated); }} onSuccess={onReplaced} />}
      <Field label="整包备注（可选）"><textarea disabled={busy || disabled} value={note} onChange={event => setNote(event.target.value)} /></Field>
      {actor && <section aria-label="代理 QA 实际观察"><p>代理 QA 需记录实际检查与证据。若未能聆听，明确记录技术音轨检查和未聆听的限制。</p>
        <Field label="实际画面与播放窗口观察"><textarea disabled={busy || disabled} value={visual} onChange={event => setVisual(event.target.value)} /></Field>
        <Field label="实际原生音频检查与限制"><textarea disabled={busy || disabled} value={audio} onChange={event => setAudio(event.target.value)} /></Field>
        <Field label="检查证据（每行一项）"><textarea disabled={busy || disabled} value={evidence} onChange={event => setEvidence(event.target.value)} /></Field>
      </section>}
      {Object.values(failedMedia).some(Boolean) && <p role="alert">有视频无法读取，整包确认已暂停。请重新读取并处理原任务。</p>}
      <footer><p>点击即确认全部显示视频及原生音频符合已显示意图，逐帧播放窗口可用于故事。打开审阅和生成完成均不构成确认。</p>
        <Button variant="primary" busy={busy} disabled={busy || replacementBusy || disabled || uncertain || !review.ready || !inspectionReady || Object.values(failedMedia).some(Boolean)} onClick={() => void confirmPack()}>{busy ? "正在保存全部视频确认…" : "确认全部视频并用于故事"}</Button></footer>
    </>}
  </dialog>;
}
