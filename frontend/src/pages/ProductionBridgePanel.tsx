import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProductionBridgeIntentEntry, ProductionBridgeState } from "../types";
import { bridgeCut } from "../production-bridge-handoff";

const proposalKey = (projectId: string, state: ProductionBridgeState) => {
  const proposal = state.proposal;
  return proposal ? `${projectId}:${proposal.revision}:${proposal.contentHash}` : undefined;
};

function userFacingBridgeMessage(message: string): string {
  return message.replace(/^不能安装：/, "暂不能确认投产提案：");
}

/** F5 projection and dramatic-intent review; this panel never dispatches media. */
export function ProductionBridgePanel({ projectId, readOnly, onOpenShot }: { projectId: string; readOnly: boolean; onOpenShot?: (shotId: string) => boolean | void }) {
  const [state, setState] = useState<ProductionBridgeState>();
  const [intentEntries, setIntentEntries] = useState<ProductionBridgeIntentEntry[]>([]);
  const [busy, setBusy] = useState(false);
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
    setState(undefined); setIntentEntries([]); setBusy(false); setError(""); setLoadFailed(false); setDraftConflict(false);
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

  const run = (operation: () => Promise<ProductionBridgeState>, adoptResult = false) => {
    const request = beginRequest();
    setBusy(true); setError("");
    void operation()
      .then(next => { if (owns(request)) { if (adoptResult) adopt(next); else setState(next); } })
      .catch(reason => { if (owns(request)) setError(reason instanceof Error ? reason.message : "投产提案操作失败。"); })
      .finally(() => { if (owns(request)) setBusy(false); });
  };

  if (!state) return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{loadFailed ? "加载失败" : "正在加载"}</strong></header>
    {loadFailed ? <><ErrorNotice message={userFacingBridgeMessage(error)} /><Button onClick={retryLoad}>重试加载</Button></> : <Spinner />}
  </section>;
  const proposal = state.proposal;
  const unsaved = intentDirty || draftConflict;
  const activeJob = job?.status === "queued" || job?.status === "dispatched";
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{state.status === "accepted" ? "投产提案已确认" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    {state.simulationLabel && <div className="notice warning" data-testid="bridge-fake-banner">{state.simulationLabel}</div>}
    <p>将已接受的故事、剧本与分镜证据整理成待审阅的投产提案。戏剧意图须单独推断或由作者填写；这里不会批准镜头、选择参考、创建资产或发起媒体任务。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!proposal && <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareProductionBridge(projectId), true)}>准备投产提案</Button>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{userFacingBridgeMessage(conflict.message)}</div>)}
      {proposal.advisories?.map((advisory, index) => <div className="notice" key={`${advisory.code}-${index}`}>{advisory.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 集 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((raw, index) => {
        const cut = bridgeCut(raw);
        return <li key={String(raw.shotId ?? index)}>{String(raw.shotId)} · {String(raw.seconds)} 秒{cut && state.status === "accepted" && state.staleReasons.length === 0 && state.installedStoryboardCurrent === true && onOpenShot && <Button variant="quiet" onClick={() => { if (onOpenShot(cut.shotId) === false) setError("来源文字仍有未保存的编辑；请先保存或明确放弃，再打开投产镜头。"); }}>在分镜工作台打开 {cut.shotId}</Button>}</li>;
      })}</ul></details>
      {state.status !== "accepted" && <div className="bridge-intent-controls">
        <Button variant="primary" disabled={readOnly || busy || activeJob || state.status === "stale"} onClick={() => run(() => plotloomApi.generateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>生成戏剧意图建议</Button>
        {job && <small className="bridge-intent-status">{job.status === "queued" ? "等待执行" : job.status === "dispatched" ? "模型处理中" : job.status === "ready" ? "建议已进入新提案" : job.status === "outcome_unknown" ? "结果不确定，不会自动重试" : job.status === "stale" ? "来源或提案已变化，结果未采用" : job.status === "cancelled" ? "已取消" : "推断失败"}</small>}
        {job?.errorMessage && <ErrorNotice message={job.errorMessage} />}
        {job?.status === "queued" && <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.resumeProductionBridgeIntent(projectId, job.id))}>继续排队任务</Button>}
        {activeJob && <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelProductionBridgeIntent(projectId, job.id))}>取消推断任务</Button>}
      </div>}
      <details open className="bridge-intent-review"><summary>戏剧意图整包审阅</summary>
        <p><small>{proposal.intentPackage.suggestionOrigin === "model_inference.v1" ? "模型建议仅供审阅，来源与目标由系统绑定。" : "来源摘录仅是证据，不是已完成的戏剧意图。"} 可逐项修改并保存整包；确认仅适用于当前提案。</small></p>
        {draftConflict && <div className="notice warning">服务器已有新提案；未保存的本地编辑仍在此保留。请复制所需文字后，明确载入新提案。</div>}
        {draftConflict && <Button onClick={() => adopt(state)}>载入新提案并放弃本地编辑</Button>}
        {intentEntries.map((entry, index) => <label key={entry.id} className="bridge-intent-field"><span>{entry.targetKind === "scene_objective" ? "场次目标" : "节拍目的"} · 第 {index + 1} 项 <small>（第 {String(entry.sourceCoordinates.episode)} 集 / 场次 {String(entry.sourceCoordinates.sceneIndex)}）</small></span><textarea disabled={readOnly || busy || state.status === "accepted" || draftConflict} value={entry.text} onChange={event => setIntentEntries(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><small>来源摘录：{entry.sourceExcerpt}</small>{entry.suggestedText !== null && <small>模型原始建议：{entry.suggestedText}</small>}</label>)}
        {state.status !== "accepted" && <Button disabled={readOnly || busy || !intentDirty || draftConflict || intentEntries.some(entry => !entry.text.trim())} onClick={() => run(() => plotloomApi.updateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, entries: intentEntries.map(entry => ({ id: entry.id, text: entry.text })) }), true)}>保存戏剧意图整包</Button>}
        {state.status !== "accepted" && unsaved && <p><small>当前编辑未保存或提案已变化；保存并刷新前，不能确认投产提案。</small></p>}
      </details>
      <details><summary>技术详情（版本、来源与冻结输入）</summary><code>{proposal.contentHash}</code>{job && <p><small>推断任务 {job.id} · 配置 {job.profileId} r{job.profileVersion} · 提示 v{job.promptVersion}</small></p>}{proposal.intentPackage.provenance && <p><small>建议来源任务：{String(proposal.intentPackage.provenance.jobId ?? "")}</small></p>}</details>
      <p>确认后，将建立后续制作使用的场景与镜头数据；不会自动生成图片或视频。</p>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable || unsaved} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>确认投产提案</Button>}
      {state.status !== "accepted" && !proposal.installable && <p>请先完成戏剧意图审阅，并显式解决项目规划冲突；系统不会拆分场次或静默改写规则。</p>}
      {state.status === "accepted" && <p>{state.installedStoryboardCurrent
        ? "投产提案已确认。可在上方选择镜头进入既有分镜工作台；分镜审核、参考选择、关键帧与媒体准备仍须分别完成。"
        : "投产提案已确认，但确认时的分镜版本不再是当前版本；请在既有分镜工作台核对当前镜头，来源镜头直达已暂停。"}</p>}
    </>}
    {error && <ErrorNotice message={userFacingBridgeMessage(error)} />}
  </section>;
}
