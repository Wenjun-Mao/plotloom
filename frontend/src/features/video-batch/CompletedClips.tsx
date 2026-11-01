import { useEffect, useRef, useState } from "react";
import { Button, Field } from "../../components";
import { plotloomApi } from "../../api";
import type { VideoJob } from "../../types";
import type { Batch } from "./contracts";
import { batchApi } from "./api";

type Publication = { receiptHash: string; sourceHash: string; gameUrl: string; downloadUrl: string; operator?: { kind: "codex_task"; taskId: string }; nativeSelections?: Record<string, { jobId: string; revision: number }>; slots: Record<string, { jobId?: string; sha256: string }> };
type Snapshot = { shot?: { id: string; sceneId: string; title: string }; request?: { seed: number } };
const snapshot = (job: VideoJob) => job.snapshot as Snapshot;

/** Completion polling never prepares, submits, selects or reviews a take. */
export function CompletedClips({ projectId, disabled, onBatch, onOperator }: { projectId: string; disabled: boolean; onBatch: (batch: Batch) => void; onOperator: (operator: Publication["operator"]) => void }) {
  const [jobs, setJobs] = useState<VideoJob[]>([]), [error, setError] = useState(""), [readError, setReadError] = useState("");
  const [publication, setPublication] = useState<Publication | null>(null);
  const [editing, setEditing] = useState<VideoJob | null>(null), [seconds, setSeconds] = useState("10");
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const identity = useRef(projectId); identity.current = projectId;
  useEffect(() => {
    let publicationAvailable = false;
    const abort = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    setJobs([]); setEditing(null); setPublication(null); setMessage(""); setError(""); setReadError(""); setBusy(false); onOperator(undefined);
    const read = async () => {
      try {
        const value = await plotloomApi.getVideoJobs(projectId, abort.signal);
        if (!abort.signal.aborted) { setJobs(value.jobs); setReadError(""); }
      } catch (failure) { if (!abort.signal.aborted) setReadError(`读取已完成原片失败：${String(failure)}`); }
      if (!abort.signal.aborted) {
        if (publicationAvailable) await readPublication();
        timer = setTimeout(read, 5000);
      }
    };
    void read();
    const readPublication = async () => { await fetch(`/api/v2/projects/${encodeURIComponent(projectId)}/prototype-publication`, { signal: abort.signal }).then(async response => {
      if (response.ok) { const value = await response.json() as Publication; if (!abort.signal.aborted) { publicationAvailable = true; setPublication(value); onOperator(value.operator || undefined); } }
    }).catch(() => {}); };
    void readPublication();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [projectId]);
  async function regenerate() {
    if (!editing || busy || disabled) return;
    const owner = projectId, shotId = snapshot(editing).shot?.id;
    if (!shotId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const review = await plotloomApi.getStoryboardReview(owner);
      const current = await plotloomApi.getVideoJobs(owner);
      const visual = await plotloomApi.getVisualWorkbench(owner);
      if (!review.activeApproval) throw new Error("请先确认当前分镜，再准备新候选。");
      const selected = current.jobs.find(job => snapshot(job).shot?.id === shotId);
      if (!selected) throw new Error("原片已变化，请重新读取。");
      const profileId = "minimax_h3_quality8_landscape_832x480_v2";
      const value = await batchApi.command(owner, "setup", { profileId, aspectPolicy: "contain_pad", maxJobs: null, maxRequestedSeconds: null, automaticRetryLimit: 0,
        shotIds: [shotId], singleRequest: { approvalId: review.activeApproval.id, shotId, storyboardRevision: review.head.revision,
          expectedSelectionRevision: visual.selectionRevision, idempotencyKey: crypto.randomUUID(), requestedDurationSeconds: Number(seconds),
          profileId, resolution: "832x480", audio: true, aspectPolicy: "contain_pad", allowLetterbox: true,
          playbackIntent: "whole_take", automaticRetryLimit: 0, seed: snapshot(editing).request?.seed } });
      if (identity.current !== owner) return;
      onBatch(value); setEditing(null); setMessage("新候选清单已准备。请核对下方来源与指令，再明确开始生成；当前选择与已发布游戏保持原样。");
    } catch (failure) { if (identity.current === owner) setError(`准备结果待核实；不会自动重发。${String(failure)}`); }
    finally { if (identity.current === owner) setBusy(false); }
  }
  async function apply(job: VideoJob) {
    if (!publication || busy || disabled) return;
    const owner = projectId; setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch(`/api/v2/projects/${encodeURIComponent(owner)}/prototype-apply`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expectedReceiptHash: publication.receiptHash, expectedSourceHash: publication.sourceHash, jobId: job.id,
          ...(publication.operator ? { operator: publication.operator } : {}) }) });
      const value = await response.json();
      if (!response.ok) throw new Error(typeof value.detail === "string" ? value.detail : JSON.stringify(value.detail));
      if (identity.current === owner) { setPublication(value); setMessage("已应用并重建下载包。请在同一游戏地址继续；旧路线与结局档案会保留。"); }
    } catch (failure) { if (identity.current === owner) setError(`尚未应用；请核对当前发布版本。${String(failure)}`); }
    finally { if (identity.current === owner) setBusy(false); }
  }
  const completed = jobs.filter(job => job.state === "ingested" && job.outputHash);
  return <section className="completed-clips" aria-label="已完成原片"><h3>已完成原片 · {completed.length}</h3>
    <p>原片完成后会出现在这里；其他镜头未完成时也能播放、拖动进度。观看不改变选择。</p>
    {publication?.operator && <p>当前操作记录为 Codex 任务 {publication.operator.taskId}，不表示主人亲自审阅。</p>}
    {readError && <p role="alert">{readError}</p>}{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {publication && <p><a href={publication.gameUrl} target="_blank" rel="noreferrer">打开当前 V2 游戏</a> · <a href={publication.downloadUrl}>下载当前 V2</a></p>}
    <div className="video-batch-gallery">{completed.map((job, index) => { const shot = snapshot(job).shot;
      const published = shot && publication?.slots[shot.id]?.sha256 === job.outputHash;
      const chosen = job.selected || (shot && publication?.nativeSelections?.[shot.id]?.jobId === job.id);
      return <article key={job.id} data-job-id={job.id}><h4>{shot?.sceneId} / {shot?.id} / 原片 {index + 1}</h4>
        <p>{shot?.title} · {chosen ? job.current ? "当前选择" : "保留选择（来源已变化）" : "候选"}{published ? " · 已发布 V2" : ""} · {job.observed?.durationSeconds.toFixed(2)} 秒</p>
        <video controls playsInline preload="none" aria-label={`${shot?.id} / ${job.id}`} src={`/api/v2/projects/${encodeURIComponent(projectId)}/video-jobs/${encodeURIComponent(job.id)}/media`} />
        <Button disabled={disabled || busy} onClick={() => { setEditing(job); setSeconds(String(Math.min(15, Math.max(5, job.requestedSeconds)))); }}>重新生成…</Button>
        {publication && !published && <Button disabled={disabled || busy || !job.current} onClick={() => void apply(job)}>应用到 V2 并重建</Button>}
        <small>{job.id}{!job.current ? " · 来源已变化，原片仍保留" : ""}</small></article>;
    })}</div>
    {editing && <section className="form-card" aria-label="重新生成当前镜头"><h4>重新生成 · {snapshot(editing).shot?.id}</h4>
      <p>生成的是新候选；当前原片不被拒绝或取消选择。需要修改作者方向时，先打开本镜头来源并保存、确认当前分镜，再返回这里准备候选。</p>
      <a href={`?project=${encodeURIComponent(projectId)}&stage=storyboard&entity=${encodeURIComponent(`shot:${snapshot(editing).shot?.id}`)}#shot-original`}>编辑这个镜头的来源方向</a>
      <Field label="新原片请求秒数"><input type="number" min="5" max="15" step="1" value={seconds} disabled={busy} onChange={event => setSeconds(event.target.value)} /></Field>
      <p>Quality 8 · 832×480 · 原生音频 · 完整原片播放。新指令仍需起草、独立检查与制作授权。</p>
      <Button disabled={disabled || busy || !Number.isInteger(Number(seconds)) || Number(seconds) < 5 || Number(seconds) > 15} onClick={() => void regenerate()}>准备新候选</Button>
      <Button disabled={busy} onClick={() => setEditing(null)}>关闭</Button>
    </section>}
  </section>;
}
