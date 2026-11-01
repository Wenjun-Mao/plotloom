import { BatchExecutionRetries } from "./ExecutionRetries";
import { AutomaticRetryCount, automaticRetryCount } from "../generation-retry/AutomaticRetryCount";
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
import { batchStateLabels, canAuthorizeBatch, ProductionBriefReview } from "./production-review";
import { WorkflowTiming } from "../../components/WorkflowTiming";
import "./video-batch.css";
import { CompletedClips } from "./CompletedClips";
export function VideoBatchPanel({ projectId, disabled, dirty, onChanged, onStory }: {
  projectId?: string; disabled: boolean; dirty: boolean; onChanged?: () => Promise<void>; onStory?: () => void;
}) {
  const [batch, setBatch] = useState<Batch | null>(null); const [backend, setBackend] = useState<VideoBackend | null>(null);
  const [operator, setOperator] = useState<import("../../operator-attribution").CodexTaskAttribution | undefined>(undefined);
  const qa = useProjectQa(projectId);
  const statusLabel = batch?.state === "approved" && batch.execution.reviewAttribution?.kind === "agent_operated_qa"
    ? "全部视频已保存代理 QA 确认" : batch ? batchStateLabels[batch.state] || "任务状态需要核实" : "";
  const [setupMode, setSetupMode] = useState(false);
  const readIdentity = useRef<string | undefined>(undefined);
  const [profile, setProfile] = useState(""); const [aspect, setAspect] = useState("reject_mismatch");
  const [maxJobs, setMaxJobs] = useState<BudgetInput>(null); const [maxSeconds, setMaxSeconds] = useState<BudgetInput>(null);
  const jobLimit = parseBudget(maxJobs, 1); const secondsLimit = parseBudget(maxSeconds, 5);
  const [retries, setRetries] = useState("1"); const retryLimit = automaticRetryCount(retries);
  function resetBudgets() { setMaxJobs(null); setMaxSeconds(null); setRetries("1"); }
  const [error, setError] = useState(""); const [busy, setBusy] = useState(""); const [review, setReview] = useState(false);
  const [ready, setReady] = useState(false); const [epoch, setEpoch] = useState(0);
  const [edits, setEdits] = useState<Record<string, Direction[]>>({}); const command = useRef<object | null>(null);
  const identity = useRef({ projectId });
  if (identity.current.projectId !== projectId) identity.current = { projectId };
  const owner = identity.current;
  const completion = useCompletionReveal(`${projectId}:${batch?.id || ""}`, dirty);
  const previous = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (batch?.state === "awaiting_review" && previous.current !== batch.state) {
      completion.reveal("video-batch-next-action"); void onChanged?.();
    }
    previous.current = batch?.state;
  }, [batch?.state]);
  useEffect(() => {
    if (readIdentity.current !== projectId) { readIdentity.current = projectId; setBatch(null); setReady(false); setReview(false); setEdits({}); setSetupMode(false); setBusy(""); setError(""); resetBudgets(); }
    if (!projectId) return;
    const abort = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await batchApi.current(projectId, abort.signal);
        if (abort.signal.aborted) return;
        setBatch(old => old && value?.id === old.id && old.revision > value.revision ? old : value);
        setReady(true);
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
  async function execute(label: string, name: string, body: unknown, foreground = false, rejectFailure = false) {
    if (!projectId || command.current === owner) { if (rejectFailure) throw new Error("已有操作待核实。"); return; }
    const clearApplied = working.clear;
    command.current = owner; setBusy(label); setError("");
    if (foreground) completion.arm(); else completion.clear();
    try {
      const value = await batchApi.command(projectId, name, body);
      if (identity.current !== owner) { if (rejectFailure) throw new Error("项目已变化，请重新读取。"); return; }
      if (rejectFailure && (!batch || value.id !== batch.id || value.revision < batch.revision)) throw new Error("当前批次已变化，请重新读取。");
      setBatch(previous => previous?.id === value.id && previous.revision > value.revision ? previous : value); setReady(true);
      if (name === "directions") { await clearApplied(); setEdits({}); }
      if (name === "setup") setSetupMode(false);
    } catch (failure) {
      if (identity.current === owner) { setReady(false); setError(`操作结果待核实，正在读取原批次；不会重放请求。${String(failure)}`); setEpoch(value => value + 1); }
      if (rejectFailure) throw failure;
    } finally { if (command.current === owner) command.current = null; if (identity.current === owner) setBusy(""); }
  }
  const controlLocked = disabled || !!busy || !ready;
  const locked = controlLocked || dirty || working.stale;
  const edited = Object.keys(edits).length > 0;
  return <Panel className="video-batch-panel form-card" id="video-batch-production"><h2>{batch?.manifest.setup.singleRequest && !setupMode ? "本镜头制作批次" : "批量制作视频"}</h2>
    <p>{batch?.manifest.setup.singleRequest && !setupMode ? "此清单来自手动制作中的单镜头请求，沿用其原种子、规格、播放窗口与请求标识。生成后仍须明确选择视频与播放窗口；音画质量观察可选。" : "覆盖全部路线的唯一制作镜头。保留已有可用视频，只为真正缺失项制作；全部生成后统一选择视频与播放窗口；音画质量观察可选。"}</p>
    <ProjectQaContext qa={qa} />{working.notice}
    {projectId && <CompletedClips projectId={projectId} disabled={disabled || dirty || !!busy} onOperator={setOperator} onBatch={value => { setBatch(value); setReady(true); setSetupMode(false); }} />}
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
    </div><AutomaticRetryCount value={retries} onChange={setRetries} disabled={locked} /><p>总预算默认不限；可分别设置任务与源秒上限。默认串行；失败后的新尝试按本次自动重试次数与剩余预算执行。此处只准备清单；不会发送 H3 作业。无可靠货币估价，以下按任务及请求秒数计量。</p>
      <Button variant="primary" disabled={locked || !backend?.enabled || !profile || jobLimit === undefined || secondsLimit === undefined || retryLimit === undefined} onClick={() => { if (jobLimit !== undefined && secondsLimit !== undefined && retryLimit !== undefined) void execute("正在核对全部路线与已有任务", "setup", { profileId: profile, aspectPolicy: aspect, maxJobs: jobLimit, maxRequestedSeconds: secondsLimit, automaticRetryLimit: retryLimit }); }}>批量生成缺失视频</Button>
      {!backend?.enabled && <p>H3 后端尚未配置或不可用；可继续使用手动制作查看已有任务。</p>}</>}
    {batch && !setupMode && <><h3>{statusLabel}</h3>
      <WorkflowTiming timing={batch.timing} kind="batch" verified={ready} />
      {projectId && <BatchExecutionRetries projectId={projectId} batch={batch} disabled={locked || edited} onRetry={body => execute("正在核对失败任务并手动重试", "retry-execution", body, false, true)} onObserve={async () => {
        const value = await batchApi.current(projectId);
        if (identity.current !== owner || !value || value.id !== batch.id) throw new Error("原批次已变化，请重新读取。");
        setBatch(previous => previous?.id === value.id && previous.revision > value.revision ? previous : value); setReady(true); setError("");
      }} />}
      {Object.entries(batch.execution.failures || {}).map(([shotId, failure]) => <p role="alert" key={shotId}>{batch.manifest.targets.find(target => target.shotId === shotId)?.title || "镜头"}：{failure.message}</p>)}
      {batch.manifest.replacement && <p>重做后继清单 · 新作业 {batch.manifest.newJobs} 项；复用镜头保留原始完成事实。</p>}
      {batch.rejectedTakes?.map(item => <p key={item.jobId}>上次拒绝 · {item.shotId}：{item.reason}。请回到对应创作来源明确需要的变化，再核对供应商候选。</p>)}
      {batch.execution.reviewAttribution?.kind === "agent_operated_qa" && <p role="status">{humanReviewLabel({ reviewer: "", attribution: batch.execution.reviewAttribution })} · 一次性测试批次</p>}
      <p>{batch.manifest.scopeShotIds.length} 个唯一镜头 · 保留 {batch.manifest.kept.length} 个已选视频 · {batch.manifest.targets.filter(item => item.mode === "reuse").length} 个复用候选 · 计划新作业 {batch.manifest.newJobs} 项 · 请求 {batch.manifest.requestedSeconds} 源秒</p>
      <p>规格 {batch.manifest.setup.profileId} · 原生音频 · 比例处理 {({ reject_mismatch: "比例不符则阻止", contain_pad: "网关填边", cover_center_crop: "网关居中裁剪" } as Record<string, string>)[batch.manifest.setup.aspectPolicy] || "需核实"} · 任务上限 {budgetSummary(batch.manifest.setup.maxJobs, "项")} / 源秒上限 {budgetSummary(batch.manifest.setup.maxRequestedSeconds, "秒")} · 最多同时 1 项</p>
      {batch.execution.error && <p role="alert">{batch.execution.error}</p>}
      {batch.manifest.blockers.map((item, index) => <p role="alert" key={index}>{item.shotId} · {item.message}</p>)}
      <section aria-label="完整制作简报"><p>请逐项审阅以下完整简报与可见设置。授权会开始视频生成；助手保真检查不等于媒体接受，也不代表你亲自核对了英文。</p>{batch.manifest.targets.map(target => <ProductionBriefReview key={target.shotId} target={target} />)}</section>
      <details><summary>供应商英文候选编辑与完整指令（技术详情）</summary>
        {batch.manifest.targets.map(target => <article key={target.shotId}><h4>{target.title} · {target.shotId}</h4>
          <p>作者目标 {target.authoredDurationUnits / 1000} 秒；请求源 {target.requestedSeconds} 秒 / {target.requestedFrames} 帧 · {({ generate: "新制作", prepared: "已准备原任务", observe: "跟踪原任务", reuse: "复用已有原片" })[target.mode]}</p>
          <p>本项冻结规格 {target.args.profile_id} · 比例处理 {target.args.aspect_policy}；复用或跟踪的原任务保持其原始设置。</p>
          <p>种子 {target.args.seed} · 首尾帧及意图来源均冻结于本清单；完整编译提示词保留下方的作者对白与画面文字。</p>
          {target.sources.map(source => <Field key={source.path} label={`${source.label} · ${source.path}`}><p>{source.text}</p>
            <textarea value={(edits[target.shotId] || target.directions?.fields || []).find(field => field.path === source.path)?.english || ""}
              disabled={locked || !["setup", "ready", "translation_rejected"].includes(batch.state) || !!batch.execution.authorizedManifestHash || target.mode !== "generate"}
              onChange={event => { const fields = edits[target.shotId] || target.directions?.fields || target.sources.map(item => ({ path: item.path, english: "" }));
                const next = { ...edits, [target.shotId]: fields.map(field => field.path === source.path ? { ...field, english: event.target.value } : field) }; setEdits(next); working.changed(JSON.stringify(next)); }} /></Field>)}
          <pre>{target.compiledPrompt || "英文方向尚未准备；不会生成视频。"}</pre></article>)}
      </details>
      {edited && <Button disabled={locked} onClick={() => void execute("正在保存候选并排入独立助手检查", "directions", { expectedRevision: batch.revision,
        draft: { version: "video-directions.draft.v1", targets: batch.manifest.targets.filter(item => item.mode === "generate").map(item => ({ shotId: item.shotId, sourceHash: item.sourceHash, fields: edits[item.shotId] || item.directions?.fields || [] })) } })}>保存候选并由助手重新检查</Button>}
      <section id="video-batch-next-action" aria-label="视频制作下一步">
      <p role="status">{statusLabel}{batch.progress && ` · 播放提案就绪 ${batch.progress.ready}/${batch.progress.total} · 失败 ${batch.progress.failed} · 不确定或阻碍 ${batch.progress.blocked}`}</p><div className="button-row">
        {["cancelled", "approved"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => { resetBudgets(); setSetupMode(true); }}>准备新的缺失视频清单</Button>}
        {batch.state === "setup" && <Button disabled={locked || !!batch.manifest.blockers.length} onClick={() => void execute("正在准备供应商指令起草与独立检查", "draft", { expectedRevision: batch.revision })}>用助手起草并独立检查全部指令</Button>}
        {["checking", "translation_rejected"].includes(batch.state) && <Button disabled={locked || edited} onClick={() => void execute("正在核对当前候选的独立检查", "check", { expectedRevision: batch.revision })}>核对当前候选的助手检查</Button>}
        {batch.state === "translation_rejected" && <p role="alert">请修正列出的语义问题；修正来源后重新准备，或修改技术候选后重新检查。未发送视频。</p>}
        {batch.state === "ready" && <Button variant="primary" disabled={locked || edited || qa.blocked || !canAuthorizeBatch(batch)} onClick={() => void execute("正在保存制作意图授权并开始生成", "start", { expectedRevision: batch.revision, manifestHash: batch.manifestHash, basis: "production-intent.v2", ...(qa.actor ? { attribution: qa.actor } : operator ? { operator } : {}) }, true)}>授权全部制作意图并开始生成</Button>}
        {["running", "drafting", "checking"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => void execute("正在暂停新派发", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "pause" })}>暂停新派发</Button>}
        {["paused", "blocked"].includes(batch.state) && <Button disabled={locked} onClick={() => void execute("正在核对原清单并恢复", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "resume" }, true)}>继续原批次</Button>}
        {!["approved", "cancelled"].includes(batch.state) && <Button disabled={controlLocked} onClick={() => void execute("正在取消本地新派发", "control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "cancel" })}>取消新派发</Button>}
        {batch.state === "awaiting_review" && <Button variant="primary" disabled={locked} onClick={() => setReview(true)}>审阅全部视频</Button>}
        {["cancelled", "blocked"].includes(batch.state) && !!Object.keys(batch.execution.segments || {}).length && <Button disabled={locked} onClick={() => setReview(true)}>审阅已完成视频与重做镜头</Button>}
        {batch.state === "approved" && <Button variant="primary" onClick={onStory}>已保存 · 查看故事播放</Button>}
        <Button variant="quiet" onClick={() => { const target = document.getElementById("video-batch-next-action"); if (target) revealWorkspaceTarget(target); }}>查看结果</Button>
      </div></section><p>暂停与取消保留已派发作业及结果；不代表远程取消。结果不确定时，仅在确认本地执行已停止且本次权限与预算允许后，按冻结次数使用新任务身份重试；可能重复生成并产生费用。每个新视频须通过技术核验并明确选用才用于故事；音画质量观察可选。</p>
    </>}
    {review && batch && projectId && <VideoBatchReview key={`${projectId}:${batch.id}`} actor={qa.actor} onBatchRead={value => { if (identity.current === owner) setBatch(value); }} onReplaced={value => { if (identity.current === owner) { setBatch(value); setReview(false); setEdits({}); } }} onConfirmStart={completion.arm} projectId={projectId} batch={batch} disabled={disabled || dirty || !ready || qa.blocked} onClose={() => { completion.clear(); setReview(false); }}
      onSaved={async () => { setReview(false); setBusy("已保存，正在刷新制作状态");
        try { const value = await batchApi.current(projectId); if (identity.current !== owner) return; setBatch(value); await onChanged?.(); }
        catch (failure) { if (identity.current === owner) setError(`已保存全部视频确认；刷新制作状态失败：${String(failure)}`); }
        finally { if (identity.current === owner) { setBusy(""); completion.reveal("video-batch-next-action"); } } }} />}
  </Panel>;
}
