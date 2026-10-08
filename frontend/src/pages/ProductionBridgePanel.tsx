import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProductionBridgeIntentEntry, ProductionBridgeState } from "../types";
import { ProductionPresentationReview } from "./ProductionPresentationReview";
import { InstalledProductionSummary } from "./InstalledProductionSummary";
import { useExplicitReviewCloseGuard } from "../features/authoring/ReviewDraftContext";

const proposalKey = (projectId: string, state: ProductionBridgeState) => {
  const proposal = state.proposal;
  return proposal ? `${projectId}:${proposal.revision}:${proposal.contentHash}` : undefined;
};

function userFacingBridgeMessage(message: string): string {
  return message.replace(/^不能安装：/, "暂不能确认投产提案：");
}

/** F5 projection and dramatic-intent review; this panel never dispatches media. */
export function ProductionBridgePanel({ projectId, readOnly, onOpenShot, onInstalled }: { projectId: string; readOnly: boolean; onOpenShot?: (shotId: string) => boolean | void; onInstalled: (projectId: string) => Promise<void> }) {
  const [state, setState] = useState<ProductionBridgeState>();
  const [intentEntries, setIntentEntries] = useState<ProductionBridgeIntentEntry[]>([]);
  const [presentationDirty, setPresentationDirty] = useState(false);
  const [presentationEditorNonce, setPresentationEditorNonce] = useState(0);
  const [presentationTouched, setPresentationTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [canonicalReady, setCanonicalReady] = useState(true);
  const [error, setError] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);
  const [draftConflict, setDraftConflict] = useState(false);
  const activeRequest = useRef({ projectId, epoch: 0, request: 0 });
  const draftProposalKey = useRef<string | undefined>(undefined);
  const draftBaseline = useRef<ProductionBridgeIntentEntry[]>([]);
  const owns = (request: { projectId: string; epoch: number; request: number }) => {
    const active = activeRequest.current;
    return active.projectId === request.projectId && active.epoch === request.epoch && active.request === request.request;
  };
  const beginRequest = () => {
    const current = activeRequest.current;
    const request = { ...current, request: current.request + 1 };
    activeRequest.current = request;
    return request;
  };
  const adopt = (next: ProductionBridgeState) => {
    draftProposalKey.current = proposalKey(projectId, next);
    draftBaseline.current = next.proposal?.intentPackage.entries ?? [];
    setIntentEntries(draftBaseline.current);
    setDraftConflict(false);
    setState(next);
  };
  const retryLoad = () => {
    const request = beginRequest();
    setError(""); setLoadFailed(false);
    void plotloomApi.getProductionBridge(projectId)
      .then(next => { if (owns(request)) adopt(next); })
      .catch(reason => { if (owns(request)) { setLoadFailed(true); setError(reason instanceof Error ? reason.message : "无法加载投产提案。"); } });
  };

  // Advance ownership before paint, and invalidate it on project change and unmount.
  useLayoutEffect(() => {
    const current = activeRequest.current;
    const request = { projectId, epoch: current.epoch + 1, request: current.request + 1 };
    activeRequest.current = request;
    const controller = new AbortController();
    draftProposalKey.current = undefined;
    draftBaseline.current = [];
    setState(undefined); setIntentEntries([]); setPresentationDirty(false); setPresentationTouched(false); setBusy(false); setCanonicalReady(true); setError(""); setLoadFailed(false); setDraftConflict(false);
    void plotloomApi.getProductionBridge(projectId, controller.signal)
      .then(next => { if (owns(request)) adopt(next); })
      .catch(reason => { if (owns(request)) { setLoadFailed(true); setError(reason instanceof Error ? reason.message : "无法加载投产提案。"); } });
    return () => {
      controller.abort();
      const active = activeRequest.current;
      activeRequest.current = { ...active, epoch: active.epoch + 1, request: active.request + 1 };
    };
  }, [projectId]);

  const currentProposalKey = state ? proposalKey(projectId, state) : undefined;
  const intentDirty = intentEntries.length !== draftBaseline.current.length
    || intentEntries.some((entry, index) => entry.id !== draftBaseline.current[index]?.id || entry.text !== draftBaseline.current[index]?.text);
  useExplicitReviewCloseGuard(projectId, "production_bridge", intentDirty || draftConflict || (presentationTouched && presentationDirty), busy,
    () => { if (state) adopt(state); setPresentationTouched(false); }, "投产提案审阅");
  useEffect(() => {
    if (!state?.proposal || !currentProposalKey || draftProposalKey.current === currentProposalKey) return;
    if (intentDirty) { setDraftConflict(true); return; }
    draftProposalKey.current = currentProposalKey;
    draftBaseline.current = state.proposal.intentPackage.entries;
    setIntentEntries(state.proposal.intentPackage.entries);
    setDraftConflict(false);
  }, [currentProposalKey, state?.proposal]);

  const job = state?.intentJob;
  useEffect(() => {
    if (!job || !["queued", "dispatched"].includes(job.status) || busy) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = () => {
      const request = beginRequest();
      void plotloomApi.getProductionBridge(projectId)
        .then(next => { if (owns(request)) { setState(next); setError(""); } })
        .catch(reason => { if (owns(request)) setError(reason instanceof Error ? reason.message : "无法刷新推断任务。"); })
        .finally(() => { if (!stopped && owns(request)) timer = setTimeout(poll, 1500); });
    };
    timer = setTimeout(poll, 1500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [projectId, job?.id, job?.status, busy]);

  const run = (operation: () => Promise<ProductionBridgeState>, adoptResult = false, resetPresentation = false, refreshCanonical = false) => {
    const request = beginRequest();
    let installed = false;
    setBusy(true); setError("");
    void operation()
      .then(async next => {
        if (!owns(request)) return;
        if (adoptResult) adopt(next); else setState(next);
        if (resetPresentation) { setPresentationTouched(false); setPresentationEditorNonce(value => value + 1); }
        if (refreshCanonical) {
          installed = next.installation?.status === "current" && next.status === "accepted";
          setCanonicalReady(false);
          await onInstalled(projectId);
          if (owns(request)) setCanonicalReady(true);
        }
      })
      .catch(reason => { if (owns(request)) setError(installed ? `投产已确认；请刷新服务器版本读取当前镜头：${reason instanceof Error ? reason.message : "读取失败"}` : reason instanceof Error ? reason.message : "投产提案操作失败。"); })
      .finally(() => { if (owns(request)) setBusy(false); });
  };

  if (!state) return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{loadFailed ? "加载失败" : "正在加载"}</strong></header>
    {loadFailed ? <><ErrorNotice message={userFacingBridgeMessage(error)} /><Button onClick={retryLoad}>重试加载</Button></> : <Spinner />}
  </section>;
  const proposal = state.proposal;
  const unsaved = intentDirty || draftConflict || presentationDirty;
  const activeJob = job?.status === "queued" || job?.status === "dispatched";
  const intentAvailable = state.intentGeneration.status === "available";
  const unresolvedJob = activeJob || job?.status === "outcome_unknown";
  const localEdits = intentDirty || draftConflict || (presentationTouched && presentationDirty);
  const canPrepare = !proposal || state.status === "stale" || state.status === "accepted";
  const preparation = state.preparation;
  const openInstalledShot = onOpenShot ? (shotId: string) => {
    if (onOpenShot(shotId) === false) setError("来源文字仍有未保存的编辑；请先保存或明确放弃，再打开投产镜头。");
  } : undefined;
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{state.status === "accepted" ? "投产提案已确认" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    {state.simulationLabel && <div className="notice warning" data-testid="bridge-fake-banner">{state.simulationLabel}</div>}
    <p>将已确认的故事、剧本与分镜证据整理成待审阅的投产提案。戏剧意图须单独推断或由作者填写；这里不会批准镜头、选择参考、创建资产或发起媒体任务。</p>
    {state.status === "stale" && <div className="notice warning">故事来源或制作版本已变化。请核对当前内容，再准备新提案并重新审阅。旧提案与已有媒体仍保留；不会自动覆盖内容或生成媒体。</div>}
    {state.installation && <InstalledProductionSummary installation={state.installation} disabled={readOnly || busy} canonicalReady={canonicalReady} onOpenShot={openInstalledShot} onReread={() => run(async () => state, false, false, true)} />}
    {canPrepare && <><Button variant="primary" disabled={readOnly || busy || localEdits || unresolvedJob || preparation.status !== "available"} onClick={() => {
      if (preparation.status === "available") run(() => plotloomApi.prepareProductionBridge(projectId, preparation.request), true, true);
    }}>{state.installation ? "准备重建提案" : proposal ? "重新准备投产提案" : "准备投产提案"}</Button>
      {state.installation && <p>重建使用当前已确认的故事、剧本与分镜。确认后替换当前制作内容，并需要重新审核；旧媒体保留，不会自动生成或选用。</p>}
      {preparation.status === "unavailable" && <p className="action-prerequisite">当前尚不能准备提案。请核对来源、剧本与分镜评审，并等待已发起的制作任务完成。</p>}
      {proposal && <p>按当前来源新建提案，保留旧版本；戏剧意图与呈现方式需要重新审阅。{localEdits ? "请先复制所需文字，再明确放弃本地编辑。" : unresolvedJob ? "仍有执行中或结果不明的意图任务，暂不能重新准备。" : ""}</p>}
      {proposal && localEdits && <Button disabled={busy || readOnly} onClick={() => { adopt(state); setPresentationTouched(false); setPresentationDirty(false); setPresentationEditorNonce(value => value + 1); }}>放弃本地编辑，保留已保存提案</Button>}</>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{userFacingBridgeMessage(conflict.message)}</div>)}
      {proposal.advisories.map((advisory, index) => <div className="notice" key={`${advisory.code}-${index}`}>{advisory.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 结构条目 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((raw, index) => {
        return <li key={String(raw.shotId ?? index)}>{String(raw.shotId)} · {String(raw.seconds)} 秒</li>;
      })}</ul></details>
      {state.status !== "accepted" && <div className="bridge-intent-controls">
        <Button variant="primary" disabled={readOnly || busy || activeJob || state.status === "stale" || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.generateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash })); }}>生成戏剧意图建议</Button>
        {!intentAvailable && <p className="action-prerequisite">当前服务未配置戏剧意图推断。可在下方逐项填写作者意图并保存整包；不会自动配置或重试模型。</p>}
        {job && <small className="bridge-intent-status">{job.status === "queued" ? "等待执行" : job.status === "dispatched" ? "模型处理中" : job.status === "ready" ? "建议已进入新提案" : job.status === "outcome_unknown" ? "结果不确定，不会自动重试" : job.status === "stale" ? "来源或提案已变化，结果未采用" : job.status === "cancelled" ? "已取消" : "推断失败"}</small>}
        {job?.errorMessage && <ErrorNotice message={job.errorMessage} />}
        {job?.status === "queued" && <Button disabled={readOnly || busy || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.resumeProductionBridgeIntent(projectId, job.id)); }}>继续排队任务</Button>}
        {activeJob && <Button disabled={readOnly || busy || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.cancelProductionBridgeIntent(projectId, job.id)); }}>取消推断任务</Button>}
      </div>}
      <details open className="bridge-intent-review"><summary>戏剧意图整包审阅</summary>
        <p><small>{proposal.intentPackage.suggestionOrigin === "model_inference.v1" ? "模型建议仅供审阅，来源与目标由系统绑定。" : "来源摘录仅是证据，不是已完成的戏剧意图。"} 可逐项修改并保存整包；确认仅适用于当前提案。</small></p>
        {draftConflict && <div className="notice warning">服务器已有新提案；未保存的本地编辑仍在此保留。请复制所需文字后，明确载入新提案。</div>}
        {draftConflict && <Button onClick={() => adopt(state)}>载入新提案并放弃本地编辑</Button>}
        {intentEntries.map((entry, index) => <label key={entry.id} className="bridge-intent-field"><span>{entry.targetKind === "scene_objective" ? "场次目标" : "节拍目的"} · 第 {index + 1} 项 <small>（第 {String(entry.sourceCoordinates.episode)} 结构条目 / 场次 {String(entry.sourceCoordinates.sceneIndex)}）</small></span><textarea disabled={readOnly || busy || state.status === "accepted" || state.status === "stale" || draftConflict} value={entry.text} onChange={event => setIntentEntries(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><small>来源摘录：{entry.sourceExcerpt}</small>{entry.suggestedText !== null && <small>模型原始建议：{entry.suggestedText}</small>}</label>)}
        {state.status !== "accepted" && <Button disabled={readOnly || busy || state.status === "stale" || !intentDirty || draftConflict || intentEntries.some(entry => !entry.text.trim())} onClick={() => run(() => plotloomApi.updateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, entries: intentEntries.map(entry => ({ id: entry.id, text: entry.text })) }), true)}>保存戏剧意图整包</Button>}
        {state.status !== "accepted" && unsaved && <p><small>当前编辑未保存或提案已变化；保存并刷新前，不能确认投产提案。</small></p>}
      </details>
      <ProductionPresentationReview key={`${projectId}:${presentationEditorNonce}`} projectId={projectId} proposal={proposal} accepted={state.status === "accepted"} disabled={readOnly || busy || activeJob || state.status === "stale" || intentDirty || draftConflict} onSaved={adopt} onDirty={setPresentationDirty} onEdited={() => setPresentationTouched(true)} onBusy={setBusy} />
      <details><summary>技术详情（版本、来源与冻结输入）</summary><code>{proposal.contentHash}</code>{state.staleReasons.length > 0 && <><p>来源过期诊断（原文）</p><ul>{state.staleReasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></>}{job && <p><small>推断任务 {job.id} · 配置 {job.profileId} r{job.profileVersion} · 提示 v{job.promptVersion}</small></p>}{proposal.intentPackage.provenance && <p><small>建议来源任务：{String(proposal.intentPackage.provenance.jobId ?? "")}</small></p>}</details>
      <p>{state.status === "accepted" ? "场景与镜头数据已建立；此次确认不会自动生成图片或视频。" : "确认投产后，会建立后续制作使用的场景与镜头数据；不会自动生成图片或视频。"}</p>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable || unsaved || state.status === "stale" || unresolvedJob} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }), false, false, true)}>确认投产提案</Button>}
      {state.status !== "accepted" && (readOnly || busy || unsaved || unresolvedJob) && <p className="action-prerequisite">{readOnly ? "项目当前只读。" : busy ? "正在处理提案，请稍候。" : unsaved ? "请先保存当前编辑，再确认投产。" : "仍有执行中或结果不明的意图任务，暂不能确认。"}</p>}
      {state.status !== "accepted" && !proposal.installable && <p>请先完成戏剧意图与呈现方式审阅，并显式解决项目规划冲突；系统不会拆分场次或静默改写规则。</p>}
    </>}
    {preparation.status === "unavailable" && <details><summary>提案准备诊断</summary><p>{preparation.reason}</p></details>}
    {error && <ErrorNotice message={userFacingBridgeMessage(error)} />}
  </section>;
}
