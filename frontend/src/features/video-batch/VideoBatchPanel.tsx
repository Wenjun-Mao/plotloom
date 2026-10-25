import { useEffect, useRef, useState } from "react";
import { useReviewEditorDraft } from "../authoring/ReviewDraftContext";
import { humanReviewLabel } from "../../human-review-attribution";
import { Button, Field, Panel } from "../../components";
import { plotloomApi } from "../../api";
import type { VideoBackend } from "../../types";
import { useCompletionReveal, revealWorkspaceTarget } from "../../app/workspace/completionReveal";
import { MiniMaxH3ProfileField, MiniMaxH3QualityField, h3Profiles } from "../../video-backends/minimax-h3";
import { AggregateBudget, budgetSummary, parseBudget, type BudgetInput } from "../../components/AggregateBudget";
import { batchApi } from "./api";
import type { Batch, Direction } from "./contracts";
import { VideoBatchReview } from "./VideoBatchReview";
import { ProjectQaContext, useProjectQa } from "../../components/ProjectQaContext";
import { WorkflowTiming } from "../../components/WorkflowTiming";
import "./video-batch.css";
const labels: Record<string, string> = { setup: "清单待准备英文方向", drafting: "助手正在准备完整英文方向", ready: "请审阅英文方向与最终提示词", running: "正在制作全部缺失视频", paused: "已暂停新派发", cancelled: "已取消新派发", blocked: "需要处理原任务", stale: "来源已变化，未发送工作已暂停", awaiting_review: "全部视频等待你审阅", approved: "全部视频已保存人工确认" };

export function VideoBatchPanel({ projectId, disabled, dirty, onChanged, onStory }: {
  projectId?: string; disabled: boolean; dirty: boolean; onChanged?: () => Promise<void>; onStory?: () => void;
}) {
  const [batch, setBatch] = useState<Batch | null>(null); const [backend, setBackend] = useState<VideoBackend | null>(null);
  const qa = useProjectQa(projectId);
  const statusLabel = batch?.state === "approved" && batch.execution.reviewAttribution?.kind === "agent_operated_qa"
    ? "全部视频已保存代理 QA 确认" : batch ? labels[batch.state] || batch.state : "";
  const [setupMode, setSetupMode] = useState(false);
  const readIdentity = useRef<string | undefined>(undefined);
  const [profile, setProfile] = useState(""); const [aspect, setAspect] = useState("reject_mismatch");
  const [maxJobs, setMaxJobs] = useState<BudgetInput>(null); const [maxSeconds, setMaxSeconds] = useState<BudgetInput>(null);
  const jobLimit = parseBudget(maxJobs, 1); const secondsLimit = parseBudget(maxSeconds, 5);
  function resetBudgets() { setMaxJobs(null); setMaxSeconds(null); }
  const [error, setError] = useState(""); const [busy, setBusy] = useState(""); const [review, setReview] = useState(false);
  const [ready, setReady] = useState(false); const [epoch, setEpoch] = useState(0);
  const [edits, setEdits] = useState<Record<string, Direction[]>>({}); const command = useRef(false);
  const identity = useRef(projectId); identity.current = projectId;
  const completion = useCompletionReveal(`${projectId}:${batch?.id || ""}`, dirty);
  const previous = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (batch?.state === "awaiting_review" && previous.current !== batch.state) {
      completion.reveal("video-batch-next-action"); void onChanged?.();
    }
    previous.current = batch?.state;
  }, [batch?.state]);
  useEffect(() => {
    if (readIdentity.current !== projectId) { readIdentity.current = projectId; setBatch(null); setReady(false); setReview(false); setEdits({}); setSetupMode(false); resetBudgets(); }
    if (!projectId) return;
    const abort = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await batchApi.current(projectId, abort.signal);
        if (abort.signal.aborted) return;
        setBatch(old => old && value?.id === old.id && old.revision > value.revision ? old : value);
        setReady(true); setError("");
      } catch (failure) { if (!abort.signal.aborted) { setReady(false); setError(`读取批次失败；不会重发任务。${String(failure)}`); } }
      if (!abort.signal.aborted) timer = setTimeout(refresh, 5000);
    };
    void refresh();
    void plotloomApi.getVideoBackend(abort.signal).then(value => { if (!abort.signal.aborted) { setBackend(value); setProfile(current => value.profiles?.some(profile => profile.id === current) ? current : value.defaultProfileId || value.profiles?.[0]?.id || ""); } }).catch(() => {});
    return () => { abort.abort(); clearTimeout(timer); };
  }, [projectId, epoch]);
  const working = useReviewEditorDraft(projectId || "", "video_directions", batch ? `${batch.id}:${batch.manifestHash}` : "unverified", text => {
    const retained = JSON.parse(text) as Record<string, Direction[]>;
    if (!batch || !retained || typeof retained !== "object" || Array.isArray(retained)) throw new Error("英文方向草稿无法读取。");
    for (const [shotId, fields] of Object.entries(retained)) {
      const target = batch.manifest.targets.find(item => item.shotId === shotId && item.mode === "generate");
      if (!target || !Array.isArray(fields) || fields.some(field => typeof field.english !== "string" || !target.sources.some(source => source.path === field.path))) throw new Error("英文方向草稿无法匹配当前清单。");
    }
    setEdits(retained);
  }, disabled || !!busy || !ready || !batch, undefined, batch?.id || "");
  async function execute(label: string, name: string, body: unknown, foreground = false) {
    if (!projectId || command.current) return;
    const clearApplied = working.clear;
    command.current = true; setBusy(label); setError("");
    if (foreground) completion.arm(); else completion.clear();
    try {
      const value = await batchApi.command(projectId, name, body);
      if (identity.current !== projectId) return;
      setBatch(value); setReady(true);
      if (name === "directions") { await clearApplied(); setEdits({}); }
      if (name === "setup") setSetupMode(false);
    } catch (failure) {
      if (identity.current === projectId) { setReady(false); setError(`操作结果待核实，正在读取原批次；不会重放请求。${String(failure)}`); setEpoch(value => value + 1); }
    } finally { command.current = false; if (identity.current === projectId) setBusy(""); }
  }
  const controlLocked = disabled || !!busy || !ready;
  const locked = controlLocked || dirty || working.stale;
  const edited = Object.keys(edits).length > 0;
  return <Panel className="video-batch-panel form-card" id="video-batch-production"><h2>批量制作视频</h2>
    <p>覆盖全部路线的唯一制作镜头。保留已有可用视频，只为真正缺失项制作；全部生成后由你一次审阅视频与原生音频。</p>
    <ProjectQaContext qa={qa} />{working.notice}
    {error && <p role="alert">{error}<Button variant="quiet" onClick={() => setEpoch(value => value + 1)}>重新读取原批次</Button></p>}
    {busy && <p role="status" aria-live="polite">{busy}；请勿重复提交。</p>}
    {dirty && <p role="status">先保存当前修改，再准备或开始批次。</p>}
    {(!batch || setupMode) && <><div className="field-grid two">
      <MiniMaxH3QualityField profiles={h3Profiles(backend)} value={profile} onChange={setProfile} disabled={locked} />
      <MiniMaxH3ProfileField profiles={h3Profiles(backend)} value={profile} onChange={setProfile} disabled={locked} />
      <Field label="输入首尾帧的比例处理"><select value={aspect} disabled={locked} onChange={event => setAspect(event.target.value)}>
        <option value="reject_mismatch">比例不符则阻止</option><option value="contain_pad">明确允许网关填边</option><option value="cover_center_crop">明确允许网关居中裁剪</option></select></Field>
      <AggregateBudget label="最多新视频任务" value={maxJobs} minimum={1} disabled={locked} onChange={setMaxJobs} />
      <AggregateBudget label="最多请求源秒数" value={maxSeconds} minimum={5} disabled={locked} onChange={setMaxSeconds} />
    </div><p>总预算默认不限；可分别设置任务与源秒上限。默认串行，每个缺失镜头最多尝试一次。此处只准备清单；不会发送 H3 作业。无可靠货币估价，以下按任务及请求秒数计量。</p>
      <Button variant="primary" disabled={locked || !backend?.enabled || !profile || jobLimit === undefined || secondsLimit === undefined} onClick={() => { if (jobLimit !== undefined && secondsLimit !== undefined) void execute("正在核对全部路线与已有任务", "setup", { profileId: profile, aspectPolicy: aspect, maxJobs: jobLimit, maxRequestedSeconds: secondsLimit }); }}>批量生成缺失视频</Button>
      {!backend?.enabled && <p>H3 后端尚未配置或不可用；可继续使用手动制作查看已有任务。</p>}</>}
    {batch && !setupMode && <><h3>{statusLabel}</h3>
      <WorkflowTiming timing={batch.timing} kind="batch" verified={ready} />
      {batch.manifest.replacement && <p>重做后继清单 · 新作业 {batch.manifest.newJobs} 项；复用镜头保留原始完成事实。</p>}
      {batch.rejectedTakes?.map(item => <p key={item.jobId}>上次拒绝 · {item.shotId}：{item.reason}。请在当前英文方向中明确需要的变化。</p>)}
      {batch.execution.reviewAttribution?.kind === "agent_operated_qa" && <p role="status">{humanReviewLabel({ reviewer: "", attribution: batch.execution.reviewAttribution })} · 一次性测试批次</p>}
      <p>{batch.manifest.scopeShotIds.length} 个唯一镜头 · 保留 {batch.manifest.kept.length} 个已选视频 · {batch.manifest.targets.filter(item => item.mode === "reuse").length} 个复用候选 · 计划新作业 {batch.manifest.newJobs} 项 · 请求 {batch.manifest.requestedSeconds} 源秒</p>
      <p>规格 {batch.manifest.setup.profileId} · 原生音频 · 比例处理 {batch.manifest.setup.aspectPolicy} · 任务上限 {budgetSummary(batch.manifest.setup.maxJobs, "项")} / 源秒上限 {budgetSummary(batch.manifest.setup.maxRequestedSeconds, "秒")} · 最多同时 1 项</p>
      {batch.execution.error && <p role="alert">{batch.execution.error}</p>}
      {batch.manifest.blockers.map((item, index) => <p role="alert" key={index}>{item.shotId} · {item.message}</p>)}
      <details><summary>审阅全部英文方向、源时长与编译提示词</summary>
        {batch.manifest.targets.map(target => <article key={target.shotId}><h4>{target.title} · {target.shotId}</h4>
          <p>作者播放 {target.authoredDurationUnits / 1000} 秒（{target.authoredDurationUnits * 24 / 1000} 帧）；请求源 {target.requestedSeconds} 秒 / {target.requestedFrames} 帧 · {target.mode}</p>
          <p>本项冻结规格 {target.args.profile_id} · 比例处理 {target.args.aspect_policy}；复用或跟踪的原任务保持其原始设置。</p>
          <p>种子 {target.args.seed} · 首尾帧及意图来源均冻结于本清单；完整编译提示词保留下方的作者对白与画面文字。</p>
          {target.sources.map(source => <Field key={source.path} label={`${source.label} · ${source.path}`}><p>{source.text}</p>
            <textarea value={(edits[target.shotId] || target.directions?.fields || []).find(field => field.path === source.path)?.english || ""}
              disabled={locked || !["setup", "ready"].includes(batch.state) || target.mode !== "generate"}
              onChange={event => { const fields = edits[target.shotId] || target.directions?.fields || target.sources.map(item => ({ path: item.path, english: "" }));
                const next = { ...edits, [target.shotId]: fields.map(field => field.path === source.path ? { ...field, english: event.target.value } : field) }; setEdits(next); working.changed(JSON.stringify(next)); }} /></Field>)}
          <pre>{target.compiledPrompt || "英文方向尚未准备；不会生成视频。"}</pre></article>)}
      </details>
      {edited && <Button disabled={locked} onClick={() => void execute("正在保存英文方向并重新编译完整清单", "directions", { expectedRevision: batch.revision,
        draft: { version: "video-directions.draft.v1", targets: batch.manifest.targets.filter(item => item.mode === "generate").map(item => ({ shotId: item.shotId, sourceHash: item.sourceHash, fields: edits[item.shotId] || item.directions?.fields || [] })) } })}>保存英文方向并更新提示词</Button>}
      <section id="video-batch-next-action" aria-label="视频制作下一步">
      <p role="status">{statusLabel}{batch.progress && ` · 播放提案就绪 ${batch.progress.ready}/${batch.progress.total} · 失败 ${batch.progress.failed} · 不确定或阻碍 ${batch.progress.blocked}`}</p><div className="button-row">
        {["cancelled", "approved"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => { resetBudgets(); setSetupMode(true); }}>准备新的缺失视频清单</Button>}
        {batch.state === "setup" && <Button disabled={locked || !!batch.manifest.blockers.length} onClick={() => void execute("正在准备完整英文方向任务", "draft", { expectedRevision: batch.revision })}>用助手准备全部英文方向</Button>}
        {batch.state === "ready" && <Button variant="primary" disabled={locked || edited || qa.blocked} onClick={() => void execute("正在冻结已审阅清单并开始制作", "start", { expectedRevision: batch.revision, manifestHash: batch.manifestHash, basis: "whole-batch-english.v1", ...(qa.actor ? { attribution: qa.actor } : {}) }, true)}>开始批量制作</Button>}
        {["running", "drafting"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => void execute("正在暂停新派发", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "pause" })}>暂停新派发</Button>}
        {["paused", "blocked"].includes(batch.state) && <Button disabled={locked} onClick={() => void execute("正在核对原清单并恢复", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "resume" }, true)}>继续原批次</Button>}
        {!["approved", "cancelled"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => void execute("正在取消本地新派发", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "cancel" })}>取消新派发</Button>}
        {batch.state === "awaiting_review" && <Button variant="primary" disabled={locked} onClick={() => setReview(true)}>审阅全部视频</Button>}
        {["cancelled", "blocked"].includes(batch.state) && !!Object.keys(batch.execution.segments || {}).length && <Button disabled={locked} onClick={() => setReview(true)}>审阅已完成视频与重做镜头</Button>}
        {batch.state === "approved" && <Button variant="primary" onClick={onStory}>已保存 · 查看故事播放</Button>}
        <Button variant="quiet" onClick={() => { const target = document.getElementById("video-batch-next-action"); if (target) revealWorkspaceTarget(target); }}>查看结果</Button>
      </div></section><p>暂停与取消保留已派发作业及结果；不代表远程取消。不确定发送不会重试。每个新视频须完成最终整包音画审阅与确认才用于故事。</p>
    </>}
    {review && batch && projectId && <VideoBatchReview key={`${projectId}:${batch.id}`} actor={qa.actor} onBatchRead={value => { if (identity.current === projectId) setBatch(value); }} onReplaced={value => { if (identity.current === projectId) { setBatch(value); setReview(false); setEdits({}); } }} onConfirmStart={completion.arm} projectId={projectId} batch={batch} disabled={disabled || dirty || !ready || qa.blocked} onClose={() => { completion.clear(); setReview(false); }}
      onSaved={async () => { setReview(false); setBusy("已保存，正在刷新制作状态");
        try { const value = await batchApi.current(projectId); setBatch(value); await onChanged?.(); }
        catch (failure) { setError(`已保存全部视频确认；刷新制作状态失败：${String(failure)}`); }
        finally { setBusy(""); completion.reveal("video-batch-next-action"); } }} />}
  </Panel>;
}
