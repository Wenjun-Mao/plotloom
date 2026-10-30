import { BatchExecutionRetries } from "./features/video-batch/ExecutionRetries";
import { AutomaticRetryCount, automaticRetryCount } from "./features/generation-retry/AutomaticRetryCount";
import { useContext, useEffect, useRef, useState } from "react";
import { ReviewDraftContext, useReviewEditorDraft } from "./features/authoring/ReviewDraftContext";
import { plotloomApi } from "./api";
import type { H3PromptPreview, H3ReviewedDirections, VideoJobPrepareBody } from "./api";
import { Button, ErrorNotice, Field } from "./components";
import { ProjectQaContext, useProjectQa } from "./components/ProjectQaContext";
import { batchApi } from "./features/video-batch/api";
import type { Batch, Direction } from "./features/video-batch/contracts";
import { batchStateLabels, canAuthorizeBatch, ProductionBriefReview } from "./features/video-batch/production-review";
import { authorizedSingleDirections, batchIsSettled, isSingleShotBatch, matchesSingleRequest } from "./features/video-batch/single-request";

function newSeed(): number {
  const values = crypto.getRandomValues(new Uint32Array(2));
  return (values[0] & 0x1fffff) * 2 ** 32 + values[1];
}
function parseSeed(value: string): number | null {
  const seed = Number(value);
  return /^\d+$/.test(value) && Number.isSafeInteger(seed) && seed >= 0 ? seed : null;
}

export function H3DirectionsReview({ projectId, shotId, sourceIdentity, sourceReady, disabled, buildRequest: buildBaseRequest, onFreeze, keyframeHash, endFrameHash, quality, requestedSeconds, frameCount }: {
  projectId: string; shotId: string; sourceIdentity: string; sourceReady: boolean; disabled: boolean;
  buildRequest: (seed: number, idempotencyKey: string) => VideoJobPrepareBody;
  onFreeze: (packageValue: H3ReviewedDirections, seed: number, idempotencyKey: string) => Promise<void>;
  keyframeHash: string; endFrameHash?: string | null; quality: number; requestedSeconds: number; frameCount: number;
}) {
  const draftContext = useContext(ReviewDraftContext);
  const [sources, setSources] = useState<H3PromptPreview | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [batch, setBatch] = useState<Batch | null>(null);
  const [otherBatch, setOtherBatch] = useState<Batch | null>(null);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [sourceReadRequired, setSourceReadRequired] = useState(true);
  const [seedText, setSeedText] = useState(() => String(newSeed()));
  const [retryText, setRetryText] = useState("1");
  const retryLimit = automaticRetryCount(retryText);
  const buildRequest = (seed: number, key: string): VideoJobPrepareBody => ({ ...buildBaseRequest(seed, key), automaticRetryLimit: retryLimit });
  const seed = parseSeed(seedText), requestKey = useRef<string>(crypto.randomUUID()), requestEpoch = useRef(0);
  const currentIdentity = useRef(`${projectId}:${sourceIdentity}`); currentIdentity.current = `${projectId}:${sourceIdentity}`;
  const available = useRef(sourceReady && !disabled); available.current = sourceReady && !disabled;
  const restoredSourceHash = useRef("");
  const pending = useRef<number | null>(null);
  const qa = useProjectQa(projectId);

  useEffect(() => {
    setSources(null); setDrafts({}); setBatch(null); setOtherBatch(null); setError(""); setBusy(false);
    pending.current = null; setSeedText(String(newSeed())); setRetryText("1"); requestKey.current = crypto.randomUUID(); restoredSourceHash.current = "";
    setSourceReadRequired(true);
    return () => { requestEpoch.current += 1; };
  }, [projectId, sourceIdentity]);
  useEffect(() => {
    if (sourceReady && !disabled) return;
    requestEpoch.current += 1; pending.current = null; setBusy(false); setSourceReadRequired(true); setError("");
  }, [sourceReady, disabled]);
  const working = useReviewEditorDraft(projectId, "h3_directions", sourceIdentity, text => {
    const input = JSON.parse(text) as { seedText: string; drafts: Record<string, string>; sourceHash: string; idempotencyKey: string; automaticRetryLimit?: string };
    if (typeof input.seedText !== "string" || input.seedText.length > 100 || typeof input.sourceHash !== "string"
      || typeof input.idempotencyKey !== "string" || !input.idempotencyKey || !input.drafts || typeof input.drafts !== "object"
      || Array.isArray(input.drafts) || Object.values(input.drafts).some(value => typeof value !== "string")) throw new Error("制作指令草稿无法读取，请保留原输入后核实。");
    if (input.automaticRetryLimit !== undefined && (typeof input.automaticRetryLimit !== "string" || automaticRetryCount(input.automaticRetryLimit) === undefined)) throw new Error("自动重试次数草稿无法读取，请核实原输入。");
    setRetryText(input.automaticRetryLimit ?? "1");
    restoredSourceHash.current = input.sourceHash; requestKey.current = input.idempotencyKey;
    setSeedText(input.seedText); setDrafts(input.drafts); setSourceReadRequired(true); setBatch(null);
  }, disabled || busy || !sourceReady, undefined, shotId);
  available.current = sourceReady && !disabled && !working.stale;
  useEffect(() => {
    if (!working.stale) return;
    requestEpoch.current += 1; pending.current = null; setBusy(false); setSourceReadRequired(true);
  }, [working.stale]);
  const editorDisabled = disabled || working.stale;
  const remember = (rawSeed: string, values: Record<string, string>, sourceHash = sources?.sourceHash || restoredSourceHash.current) =>
    working.changed(JSON.stringify({ seedText: rawSeed, drafts: values, sourceHash, idempotencyKey: requestKey.current, automaticRetryLimit: retryText }));
  function changeSeed(value: string) {
    requestEpoch.current += 1; requestKey.current = crypto.randomUUID(); remember(value, drafts);
    setSeedText(value); setSources(null); setBatch(null); setOtherBatch(null); setError(""); setSourceReadRequired(true);
  }
  function changeRetryLimit(value: string) {
    requestEpoch.current += 1; requestKey.current = crypto.randomUUID(); setRetryText(value);
    working.changed(JSON.stringify({ seedText, drafts, sourceHash: sources?.sourceHash || restoredSourceHash.current,
      idempotencyKey: requestKey.current, automaticRetryLimit: value }));
    setSources(null); setBatch(null); setOtherBatch(null); setError(""); setSourceReadRequired(true);
  }
  async function execute(operation: (owns: () => boolean) => Promise<void>, rejectFailure = false) {
    if (pending.current !== null || busy || editorDisabled || !sourceReady || seed === null || retryLimit === undefined) { if (rejectFailure) throw new Error("当前来源或已有操作待核实。"); return; }
    const epoch = ++requestEpoch.current, identity = currentIdentity.current; pending.current = epoch;
    const owns = () => available.current && epoch === requestEpoch.current && identity === currentIdentity.current;
    setBusy(true); setError("");
    try { await operation(owns); }
    catch (reason) { if (owns()) { setError(`操作结果需要核实；请读取原任务，不会重放请求。${reason instanceof Error ? reason.message : String(reason)}`); setSourceReadRequired(true); } if (rejectFailure) throw reason; }
    finally { if (pending.current === epoch) pending.current = null; if (owns()) setBusy(false); }
  }
  const request = () => buildRequest(seed!, requestKey.current);
  const load = () => execute(async owns => {
    const body = request();
    const [preview, current] = await Promise.all([plotloomApi.previewH3Prompt(projectId, body), batchApi.current(projectId)]);
    if (!owns()) return;
    const sameSource = preview.sourceHash === (sources?.sourceHash || restoredSourceHash.current);
    const values = sameSource ? drafts : {};
    setSources(preview); setDrafts(values); setSourceReadRequired(false); remember(seedText, values, preview.sourceHash);
    if (current && matchesSingleRequest(current, body, preview.sourceHash)) { setBatch(current); setOtherBatch(null); }
    else { setBatch(null); setOtherBatch(current); }
  });
  // Read-only observation of the exact scoped batch. No command or retry is automatic.
  useEffect(() => {
    if (!batch || !sources || seed === null || sourceReadRequired || !sourceReady) return;
    const identity = currentIdentity.current, body = buildRequest(seed, requestKey.current), epoch = requestEpoch.current;
    const abort = new AbortController();
    const timer = setInterval(() => {
      void batchApi.current(projectId, abort.signal).then(value => {
        if (abort.signal.aborted || !available.current || currentIdentity.current !== identity || requestEpoch.current !== epoch) return;
        if (!value || !matchesSingleRequest(value, body, sources.sourceHash)) { setSourceReadRequired(true); setError("当前批次已变化，请核实原任务；不会采用其他清单。"); return; }
        setBatch(old => old?.id === value.id && old.revision > value.revision ? old : value);
      }).catch(() => { if (!abort.signal.aborted && currentIdentity.current === identity && requestEpoch.current === epoch) { setSourceReadRequired(true); setError("读取原任务失败；种子与草稿保留，请重新读取，不会重发。"); } });
    }, 5000);
    return () => { abort.abort(); clearInterval(timer); };
  }, [projectId, batch?.id, batch?.revision, sources?.sourceHash, seed, sourceReadRequired, sourceReady]);

  const setup = () => execute(async owns => {
    if (!sources || sourceReadRequired) return;
    if (draftContext?.enabled && draftContext.projectId === projectId) {
      const settled = await draftContext.quiescence.flush(projectId);
      if (!owns()) return;
      if (!settled) throw new Error("当前项目的输入尚未保存或存在冲突；请先核对原输入，再准备制作简报。");
    }
    const body = request(), current = await batchApi.current(projectId);
    if (!owns()) return;
    if (current && matchesSingleRequest(current, body, sources.sourceHash)) { setBatch(current); setOtherBatch(null); return; }
    if (current && !batchIsSettled(current)) { setOtherBatch(current); throw new Error("另一个批次尚未结束，请在原批次中处理；不会覆盖或改变它。"); }
    if (!body.profileId) throw new Error("请先明确本次 H3 规格。");
    const value = await batchApi.command(projectId, "setup", { profileId: body.profileId, aspectPolicy: body.aspectPolicy || "reject_mismatch",
      shotIds: [shotId], singleRequest: body, maxJobs: null, maxRequestedSeconds: null, automaticRetryLimit: retryLimit });
    if (!owns()) return;
    if (!matchesSingleRequest(value, body, sources.sourceHash)) throw new Error("返回清单与原单镜头请求不匹配，已停止。");
    setBatch(value); setOtherBatch(null);
  });
  const command = (name: "draft" | "check" | "directions" | "control" | "retry-execution", body: unknown, rejectFailure = false) => execute(async owns => {
    if (!batch || !sources || sourceReadRequired || !matchesSingleRequest(batch, request(), sources.sourceHash)) { if (rejectFailure) throw new Error("当前精确请求未核实。"); return; }
    const value = await batchApi.command(projectId, name, body);
    if (!owns()) { if (rejectFailure) throw new Error("当前请求已变化。"); return; }
    if (rejectFailure && (value.id !== batch.id || value.revision < batch.revision)) throw new Error("当前批次已变化，请读取原任务。");
    if (!matchesSingleRequest(value, request(), sources.sourceHash)) throw new Error("任务身份已变化，不能采用返回结果。");
    setBatch(previous => previous?.id === value.id && previous.revision > value.revision ? previous : value);
    if (name === "directions") { setDrafts({}); remember(seedText, {}, sources.sourceHash); }
  }, rejectFailure);
  const authorize = () => execute(async owns => {
    if (!batch || !sources || sourceReadRequired || qa.blocked || Object.keys(drafts).length || !canAuthorizeBatch(batch)) return;
    await batchApi.command(projectId, "start", { expectedRevision: batch.revision, manifestHash: batch.manifestHash,
      basis: "production-intent.v2", ...(qa.actor ? { attribution: qa.actor } : {}) });
    if (!owns()) return;
    const current = await batchApi.current(projectId);
    if (!owns()) return;
    const packageValue = current && authorizedSingleDirections(current, request(), sources.sourceHash);
    if (!current || !packageValue) throw new Error("生成授权结果尚未核实，请读取原任务；不会再次授权或发送。");
    if (JSON.stringify(packageValue.reviewBasis.attribution || null) !== JSON.stringify(qa.actor || null)) throw new Error("已保存授权的审阅身份不匹配，不能改用其他身份。");
    setBatch(current); await onFreeze(packageValue, seed!, requestKey.current);
  });
  const recover = () => execute(async owns => {
    if (!sources || sourceReadRequired) return;
    const current = await batchApi.current(projectId);
    if (!owns()) return;
    const packageValue = current && authorizedSingleDirections(current, request(), sources.sourceHash);
    if (!current || !packageValue) throw new Error("没有当前精确请求的已保存授权，不能准备新任务。");
    if (JSON.stringify(packageValue.reviewBasis.attribution || null) !== JSON.stringify(qa.actor || null)) throw new Error("已保存授权的审阅身份不匹配，不能改用其他身份。");
    setBatch(current); await onFreeze(packageValue, seed!, requestKey.current);
  });
  const cancelOther = () => execute(async owns => {
    if (!otherBatch || !isSingleShotBatch(otherBatch, shotId)) return;
    const value = await batchApi.current(projectId);
    if (!owns()) return;
    if (!value || value.id !== otherBatch.id || value.controlRevision !== otherBatch.controlRevision || !isSingleShotBatch(value, shotId))
      throw new Error("原单镜头批次已变化，请先重新读取。");
    const cancelled = await batchApi.command(projectId, "control", { batchId: value.id, expectedControlRevision: value.controlRevision, action: "cancel" });
    if (owns()) { setOtherBatch(cancelled); setSourceReadRequired(true); }
  });
  function newTake() {
    if (!batch || !batchIsSettled(batch) || busy || editorDisabled || !sourceReady) return;
    requestEpoch.current += 1; requestKey.current = crypto.randomUUID(); remember(seedText, {});
    setBatch(null); setOtherBatch(batch); setSources(null); setDrafts({}); setSourceReadRequired(true); setError("");
  }
  const target = batch?.manifest.targets[0], locked = editorDisabled || !sourceReady || sourceReadRequired || busy;
  const edited = Object.keys(drafts).length > 0;
  const fieldSources = target?.sources || sources?.sources || [];
  const fields: Direction[] = fieldSources.map(source => ({ path: source.path, english: drafts[source.path] ?? target?.directions?.fields.find(field => field.path === source.path)?.english ?? "" }));
  return <details className="video-technical-history h3-directions-review" data-testid="h3-directions-review">
    <summary>审阅制作简报与授权生成</summary>{working.notice}
    <p>助手起草英文供应商指令，再由独立助手核对原始来源。请审阅下方完整制作简报与生成设置；授权会开始生成，返回的视频仍需单独检查与选用。</p>
    <ProjectQaContext qa={qa} />
    <label className="h3-seed-field"><strong>H3 随机种子</strong><input aria-label="H3 随机种子" type="text" inputMode="numeric" value={seedText}
      disabled={editorDisabled || !sourceReady || busy} aria-invalid={seed === null} onChange={event => changeSeed(event.target.value)} />
      <small>默认随机。修改种子或设置会产生不同请求；已有任务不会被覆盖；自动重试按本次冻结的次数和剩余预算执行。</small>
      {seed === null && <small role="alert">请输入 0–9007199254740991 的十进制整数；不接受小数、指数或精度丢失。</small>}</label>
    <AutomaticRetryCount value={retryText} onChange={changeRetryLimit} disabled={editorDisabled || !sourceReady || busy} />
    <Button disabled={editorDisabled || !sourceReady || busy || seed === null || retryLimit === undefined} onClick={() => void load()}>读取当前来源</Button>
    {sourceReadRequired && <p role="status">请重新读取并核验当前来源；已有种子与草稿保留，尚不能授权生成。</p>}
    {sources && <>
      <small>来源绑定：{sources.sourceHash.slice(0, 12)}；修改来源、设置或审核选择后必须重新核验。</small>
      <small data-testid="h3-frozen-review-inputs">本次输入：质量 {quality}；请求 {requestedSeconds} 秒 / {frameCount} 帧；种子 {seed}；起始关键帧 SHA-256 {keyframeHash}；末帧 {endFrameHash ? `SHA-256 ${endFrameHash}` : "未使用"}。请求秒数不是最终播放时长。</small>
        <details><summary>编辑供应商英文候选（技术详情）</summary>
          <p>修改候选会使原检查与生成授权失效，并交由独立助手重新检查；创作事实请回到对应来源修改。</p>
          {fieldSources.map(source => <Field key={source.path} label={source.label}><p>{source.text}</p>
            <textarea aria-label={`${source.label}的英文生成说明`} value={fields.find(field => field.path === source.path)?.english || ""}
              disabled={locked || !!batch && (!["setup", "ready", "translation_rejected"].includes(batch.state) || !!batch.execution.authorizedManifestHash)}
              onChange={event => { const next = { ...drafts, [source.path]: event.target.value }; setDrafts(next); remember(seedText, next); }} /></Field>)}
        </details>
      {otherBatch && !batchIsSettled(otherBatch) && <p role="alert">另一个批次尚未结束，不能覆盖它。<a href="#video-batch-production">查看原批次</a>{isSingleShotBatch(otherBatch, shotId) && <Button disabled={locked} onClick={() => void cancelOther()}>结束原单镜头批次的新派发</Button>}</p>}
      {!batch && <Button disabled={locked || !!otherBatch && !batchIsSettled(otherBatch)} onClick={() => void setup()}>准备本镜头制作简报</Button>}
      {batch && <>
        <p role="status">{batchStateLabels[batch.state] || "任务状态需要核实"}</p>
        <BatchExecutionRetries projectId={projectId} batch={batch} disabled={locked || edited} onRetry={body => command("retry-execution", body, true)} onObserve={async () => {
          const identity = currentIdentity.current, epoch = requestEpoch.current, value = await batchApi.current(projectId);
          if (!available.current || identity !== currentIdentity.current || epoch !== requestEpoch.current || !value || value.id !== batch.id
            || !matchesSingleRequest(value, request(), sources.sourceHash)) throw new Error("当前单镜头请求已变化，请读取当前来源。");
          setBatch(previous => previous?.id === value.id && previous.revision > value.revision ? previous : value);
        }} />
        {batch.execution.error && <ErrorNotice message={batch.execution.error} />}
        {batch.manifest.blockers.map((item, index) => <p role="alert" key={index}>{item.message}</p>)}
        {target && <ProductionBriefReview target={target} />}
        {edited && <Button disabled={locked || fields.some(field => !field.english.trim())} onClick={() => void command("directions", { expectedRevision: batch.revision,
          draft: { version: "video-directions.draft.v1", targets: [{ shotId, sourceHash: target!.sourceHash, fields }] } })}>保存候选并由助手重新检查</Button>}
        {batch.state === "setup" && <Button disabled={locked || edited || !!batch.manifest.blockers.length} onClick={() => void command("draft", { expectedRevision: batch.revision })}>用助手起草并独立检查指令</Button>}
        {batch.state === "translation_rejected" && <p role="alert">请按检查结果修改来源或英文候选；不会自动重试生成。</p>}
        {["ready", "checking", "translation_rejected"].includes(batch.state) && <Button disabled={locked || edited} onClick={() => void command("check", { expectedRevision: batch.revision })}>核对当前候选的助手检查</Button>}
        <Button variant="primary" disabled={locked || edited || qa.blocked || !canAuthorizeBatch(batch)} onClick={() => void authorize()}>授权本镜头制作意图并开始生成</Button>
        {batchIsSettled(batch) && <Button disabled={locked} onClick={newTake}>保留设置并准备新的原片候选</Button>}
        {!batchIsSettled(batch) && <Button disabled={locked} onClick={() => void command("control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "cancel" })}>结束本次新派发</Button>}
        {batch.execution.authorizedManifestHash && !["cancelled", "stale"].includes(batch.state) && <Button disabled={locked || qa.blocked} onClick={() => void recover()}>读取本次已授权原任务</Button>}
        {["drafting", "checking", "running"].includes(batch.state) && <Button disabled={editorDisabled || busy} onClick={() => void command("control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "pause" })}>暂停本次新派发</Button>}
        {["paused", "blocked"].includes(batch.state) && <Button disabled={locked} onClick={() => void command("control", { batchId: batch.id, expectedControlRevision: batch.controlRevision, action: "resume" })}>继续本次原任务</Button>}
      </>}
    </>}
    {error && <ErrorNotice message={error} />}
  </details>;
}
