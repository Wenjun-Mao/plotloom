import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import { ProductionPresentationReview } from "./ProductionPresentationReview";
import { InstalledProductionSummary } from "./InstalledProductionSummary";
import { NativeBridgeIntentControls } from "./NativeBridgeIntentControls";
import { useExplicitReviewCloseGuard } from "../features/authoring/ReviewDraftContext";
import { useProductionBridgeReview, type BridgeReviewBasis } from "./useProductionBridgeReview";

function userFacingBridgeMessage(message: string): string {
  return message.replace(/^不能安装：/, "暂不能确认投产提案：");
}

/** F5 projection and dramatic-intent review; this panel never dispatches media. */
export function ProductionBridgePanel({ projectId, reviewBasis, readOnly: ownerReadOnly, onOpenShot, onInstalled }: {
  projectId: string; reviewBasis: BridgeReviewBasis; readOnly: boolean;
  onOpenShot?: (shotId: string) => boolean | void; onInstalled: (projectId: string) => Promise<void>;
}) {
  const review = useProductionBridgeReview(projectId, reviewBasis, ownerReadOnly || reviewBasis.status !== "current", onInstalled);
  const { state, proposal, intentEntries, presentationDirty, presentationTouched, presentationEditorNonce,
    busy, canonicalReady, error, loadFailed, draftConflict, intentDirty, retryLoad, run, setIntentEntries, setError } = review;
  const readOnly = ownerReadOnly || reviewBasis.status !== "current" || !review.acknowledged;
  useExplicitReviewCloseGuard(projectId, "production_bridge", intentDirty || draftConflict || (presentationTouched && presentationDirty), false,
    review.discard, "投产提案审阅");
  const job = state?.intentJob;
  if (!state) return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{loadFailed ? "加载失败" : "正在加载"}</strong></header>
    {loadFailed ? <><ErrorNotice message={userFacingBridgeMessage(error)} /><Button onClick={retryLoad}>重试加载</Button></> : <Spinner />}
  </section>;
  const unsaved = intentDirty || draftConflict || presentationDirty;
  const activeJob = job?.status === "queued" || job?.status === "dispatched";
  const intentAvailable = state.intentGeneration.status === "available";
  const unresolvedJob = activeJob || job?.status === "outcome_unknown" || job?.transport === "codex_native" && job.status === "cancelled" && !job.responseHash && state.nativeIntentTask?.state !== "prepared";
  const localEdits = intentDirty || draftConflict || (presentationTouched && presentationDirty);
  const canPrepare = !proposal || state.status === "stale" || state.status === "accepted";
  const preparation = state.preparation;
  const openInstalledShot = onOpenShot ? (shotId: string) => {
    if (!review.canAct() || draftConflict) return;
    if (onOpenShot(shotId) === false) setError("来源文字仍有未保存的编辑；请先保存或明确放弃，再打开投产镜头。");
  } : undefined;
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{reviewBasis.status !== "current" ? "分镜评审待确认" : state.status === "accepted" ? "投产提案已确认" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    {!review.acknowledged && <div className="notice warning" role="status">{loadFailed ? "投产提案刷新失败；已显示内容与草稿保留，操作暂时停用。" : "正在核对当前分镜评审对应的投产提案；草稿保留，操作暂时停用。"}</div>}
    {loadFailed && <Button disabled={busy} onClick={retryLoad}>重试加载</Button>}
    {state.simulationLabel && <div className="notice warning" data-testid="bridge-fake-banner">{state.simulationLabel}</div>}
    <p>将已确认的故事、剧本与分镜证据整理成待审阅的投产提案。戏剧意图须单独推断或由作者填写；这里不会批准镜头、选择参考、创建资产或发起媒体任务。</p>
    {state.status === "stale" && <div className="notice warning">{reviewBasis.status !== "current"
      ? "当前分镜评审尚未确认；旧提案与已有媒体仍保留。请完成分镜评审，或取消尚未确认的替换任务后重新核对。"
      : "故事来源或制作版本已变化。请核对当前内容，再准备新提案并重新审阅。旧提案与已有媒体仍保留；不会自动覆盖内容或生成媒体。"}</div>}
    {state.installation && <InstalledProductionSummary installation={state.installation} reviewAcknowledged={review.acknowledged} reviewBasisStatus={reviewBasis.status} disabled={readOnly || busy || draftConflict} canonicalReady={canonicalReady} onOpenShot={openInstalledShot} onReread={() => run(async () => state, false, false, true)} />}
    {canPrepare && <><Button variant="primary" disabled={readOnly || busy || localEdits || unresolvedJob || preparation.status !== "available"} onClick={() => {
      if (preparation.status === "available") run(() => plotloomApi.prepareProductionBridge(projectId, preparation.request), true, true);
    }}>{state.installation ? "准备重建提案" : proposal ? "重新准备投产提案" : "准备投产提案"}</Button>
      {state.installation && review.acknowledged && reviewBasis.status === "current" && <p>重建使用当前已确认的故事、剧本与分镜。确认后替换当前制作内容，并需要重新审核；旧媒体保留，不会自动生成或选用。</p>}
      {preparation.status === "unavailable" && <p className="action-prerequisite">当前尚不能准备提案。请核对来源、剧本与分镜评审，并等待已发起的制作任务完成。</p>}
      {proposal && <p>按当前来源新建提案，保留旧版本；戏剧意图与呈现方式需要重新审阅。{localEdits ? "请先复制所需文字，再明确放弃本地编辑。" : unresolvedJob ? "仍有执行中或结果不明的意图任务，暂不能重新准备。" : ""}</p>}
      {proposal && localEdits && <Button disabled={busy || readOnly} onClick={review.discard}>放弃本地编辑，保留已保存提案</Button>}</>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{userFacingBridgeMessage(conflict.message)}</div>)}
      {proposal.advisories.map((advisory, index) => <div className="notice" key={`${advisory.code}-${index}`}>{advisory.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 结构条目 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((raw, index) => {
        return <li key={String(raw.shotId ?? index)}>{String(raw.shotId)} · {String(raw.seconds)} 秒</li>;
      })}</ul></details>
      <NativeBridgeIntentControls projectId={projectId} state={state} disabled={readOnly || busy} localEdits={localEdits} run={operation => run(operation)} />
      {state.status !== "accepted" && (intentAvailable || job?.transport === "text_api" || state.nativeIntentGeneration.status === "unavailable") && <div className="bridge-intent-controls">
        {intentAvailable && <small>API 意图推断使用独立配置；请选择需要的生成方式。</small>}
        <Button variant="primary" disabled={readOnly || busy || activeJob || state.status === "stale" || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.generateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash })); }}>生成戏剧意图建议</Button>
        {!intentAvailable && <p className="action-prerequisite">当前服务未配置戏剧意图推断。可在下方逐项填写作者意图并保存整包；不会自动配置或重试模型。</p>}
        {job && job.transport !== "codex_native" && <small className="bridge-intent-status">{job.status === "queued" ? "等待执行" : job.status === "dispatched" ? "模型处理中" : job.status === "ready" ? "建议已进入新提案" : job.status === "outcome_unknown" ? "结果不确定，不会自动重试" : job.status === "stale" ? "来源或提案已变化，结果未采用" : job.status === "cancelled" ? "已取消" : "推断失败"}</small>}
        {job?.errorMessage && <ErrorNotice message={job.errorMessage} />}
        {job?.transport === "text_api" && job.status === "queued" && <Button disabled={readOnly || busy || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.resumeProductionBridgeIntent(projectId, job.id)); }}>继续排队任务</Button>}
        {activeJob && job.transport === "text_api" && <Button disabled={readOnly || busy || !intentAvailable} onClick={() => { if (intentAvailable) run(() => plotloomApi.cancelProductionBridgeIntent(projectId, job.id)); }}>取消推断任务</Button>}
      </div>}
      <details open className="bridge-intent-review"><summary>戏剧意图整包审阅</summary>
        <p><small>{proposal.intentPackage.suggestionOrigin !== "none" ? "模型建议仅供审阅，来源与目标由系统绑定。" : "来源摘录仅是证据，不是已完成的戏剧意图。"} 可逐项修改并保存整包；确认仅适用于当前提案。</small></p>
        {draftConflict && <div className="notice warning">服务器提案或审阅状态已变化；未保存的本地编辑仍在此保留。请复制所需文字后，明确载入当前提案。</div>}
        {draftConflict && <Button disabled={readOnly || busy} onClick={review.discard}>载入新提案并放弃本地编辑</Button>}
        {intentEntries.map((entry, index) => <label key={entry.id} className="bridge-intent-field"><span>{entry.targetKind === "scene_objective" ? "场次目标" : "节拍目的"} · 第 {index + 1} 项 <small>（第 {String(entry.sourceCoordinates.episode)} 结构条目 / 场次 {String(entry.sourceCoordinates.sceneIndex)}）</small></span><textarea disabled={readOnly || busy || state.status === "accepted" || state.status === "stale" || draftConflict} value={entry.text} onChange={event => setIntentEntries(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><small>来源摘录：{entry.sourceExcerpt}</small>{entry.suggestedText !== null && <small>模型原始建议：{entry.suggestedText}</small>}</label>)}
        {state.status !== "accepted" && <Button disabled={readOnly || busy || state.status === "stale" || (!intentDirty && proposal.intentPackage.reviewState !== "model_suggested") || draftConflict || intentEntries.some(entry => !entry.text.trim())} onClick={() => run(() => plotloomApi.updateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, entries: intentEntries.map(entry => ({ id: entry.id, text: entry.text })) }), true)}>保存戏剧意图整包</Button>}
        {state.status !== "accepted" && unsaved && <p><small>当前编辑未保存或提案已变化；保存并刷新前，不能确认投产提案。</small></p>}
      </details>
      <ProductionPresentationReview key={`${projectId}:${presentationEditorNonce}`} projectId={projectId} proposal={proposal} accepted={state.status === "accepted"} disabled={readOnly || busy || activeJob || state.status === "stale" || intentDirty || draftConflict} onSave={async entries => Boolean(await run(() => plotloomApi.updateProductionBridgePresentation(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, sourceHash: proposal.presentation.sourceHash, reviewedComplete: true, entries }), true))} onDirty={review.setPresentationDirty} onEdited={review.presentationEdited} />
      <details><summary>技术详情（版本、来源与冻结输入）</summary><code>{proposal.contentHash}</code>{state.staleReasons.length > 0 && <><p>来源过期诊断（原文）</p><ul>{state.staleReasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></>}{job && <p><small>推断任务 {job.id} · {job.transport === "codex_native" ? "Codex 原生冻结任务" : `API 配置 ${job.profileId} r${job.profileVersion}`} · 提示 v{job.promptVersion}</small></p>}{proposal.intentPackage.provenance && <p><small>建议来源任务：{String(proposal.intentPackage.provenance.jobId ?? "")}</small></p>}</details>
      <p>{state.status === "accepted" ? "场景与镜头数据已建立；此次确认不会自动生成图片或视频。" : "确认投产后，会建立后续制作使用的场景与镜头数据；不会自动生成图片或视频。"}</p>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable || unsaved || state.status === "stale" || unresolvedJob} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }), false, false, true)}>确认投产提案</Button>}
      {state.status !== "accepted" && (readOnly || busy || unsaved || unresolvedJob) && <p className="action-prerequisite">{readOnly ? "当前暂不能修改或确认此投产提案。请先核对项目权限与当前分镜评审状态。" : busy ? "正在处理提案，请稍候。" : unsaved ? "请先保存当前编辑，再确认投产。" : "仍有执行中或结果不明的意图任务，暂不能确认。"}</p>}
      {state.status !== "accepted" && !proposal.installable && <p>请先完成戏剧意图与呈现方式审阅，并显式解决项目规划冲突；系统不会拆分场次或静默改写规则。</p>}
    </>}
    {preparation.status === "unavailable" && <details><summary>提案准备诊断</summary><p>{preparation.reason}</p></details>}
    {error && <ErrorNotice message={userFacingBridgeMessage(error)} />}
  </section>;
}
