import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProductionBridgeIntentEntry, ProductionBridgeState } from "../types";

const proposalKey = (projectId: string, state: ProductionBridgeState) => {
  const proposal = state.proposal;
  return proposal ? `${projectId}:${proposal.revision}:${proposal.contentHash}` : undefined;
};

/** F5 projection and dramatic-intent review; this panel never dispatches media. */
export function ProductionBridgePanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
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
    {loadFailed ? <><ErrorNotice message={error} /><Button onClick={retryLoad}>重试加载</Button></> : <Spinner />}
  </section>;
  const proposal = state.proposal;
  const unsaved = intentDirty || draftConflict;
  const activeJob = job?.status === "queued" || job?.status === "dispatched";
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{state.status === "accepted" ? "已安装" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    <p>将已接受的 F5 评审证据映射为规范场次与镜头。戏剧意图须单独推断或由作者填写并审阅；不会批准镜头、选择参考、创建资产或发起 H3 工作。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!proposal && <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareProductionBridge(projectId), true)}>准备投产提案</Button>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{conflict.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 集 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((cut, index) => <li key={String(cut.shotId ?? index)}>{String(cut.shotId)} · {String(cut.seconds)} 秒</li>)}</ul></details>
      {state.status !== "accepted" && <div className="bridge-intent-controls">
        <Button variant="primary" disabled={readOnly || busy || activeJob || state.status === "stale"} onClick={() => run(() => plotloomApi.generateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>生成戏剧意图建议</Button>
        {job && <small className="bridge-intent-status">推断任务 {job.id.slice(0, 8)} · {job.status === "queued" ? "等待执行" : job.status === "dispatched" ? "模型处理中" : job.status === "ready" ? "建议已进入新提案" : job.status === "outcome_unknown" ? "结果不确定，不会自动重试" : job.status === "stale" ? "来源或提案已变化，结果未采用" : job.status === "cancelled" ? "已取消" : "失败"} · 配置 {job.profileId} r{job.profileVersion} · 提示 v{job.promptVersion}</small>}
        {job?.errorMessage && <ErrorNotice message={job.errorMessage} />}
        {job?.status === "queued" && <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.resumeProductionBridgeIntent(projectId, job.id))}>继续排队任务</Button>}
        {activeJob && <Button disabled={readOnly || busy} onClick={() => run(() => plotloomApi.cancelProductionBridgeIntent(projectId, job.id))}>取消推断任务</Button>}
      </div>}
      <details open className="bridge-intent-review"><summary>戏剧意图整包审阅</summary>
        <p><small>{proposal.intentPackage.method === "model_inference.v1" ? "模型建议仅供审阅，来源坐标与目标由系统绑定。" : "来源摘录仅是证据，不是已完成的戏剧意图。"} 可逐项修改并保存整包；接受只安装当前已保存的提案。</small></p>
        {draftConflict && <div className="notice warning">服务器已有新提案；未保存的本地编辑仍在此保留。请复制所需文字后，明确载入新提案。</div>}
        {draftConflict && <Button onClick={() => adopt(state)}>载入新提案并放弃本地编辑</Button>}
        {intentEntries.map((entry, index) => <label key={entry.id} className="bridge-intent-field"><span>{entry.targetKind === "scene_objective" ? "场次目标" : "节拍目的"} · {entry.targetId} <small>（来源 {String(entry.sourceCoordinates.sectionId)}{entry.targetKind === "beat_purpose" ? ` / 流 ${String(entry.sourceCoordinates.flowIndex)}` : ""}）</small></span><textarea disabled={readOnly || busy || state.status === "accepted" || draftConflict} value={entry.text} onChange={event => setIntentEntries(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><small>{entry.method === "model_inference.v1" ? "模型原始建议" : "来源摘录"}：{entry.suggestedText}</small></label>)}
        {state.status !== "accepted" && <Button disabled={readOnly || busy || !intentDirty || draftConflict || intentEntries.some(entry => !entry.text.trim())} onClick={() => run(() => plotloomApi.updateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, entries: intentEntries.map(entry => ({ id: entry.id, text: entry.text })) }), true)}>保存戏剧意图整包</Button>}
        {state.status !== "accepted" && unsaved && <p><small>当前编辑未保存或绑定已变化；接受安装保持禁用。</small></p>}
      </details>
      <details><summary>技术详情（哈希与冻结输入）</summary><code>{proposal.contentHash}</code>{proposal.intentPackage.provenance && <p><small>建议来源任务：{String(proposal.intentPackage.provenance.jobId ?? "")}</small></p>}</details>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable || unsaved} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>接受并安装</Button>}
      {state.status !== "accepted" && !proposal.installable && <p>请先完成戏剧意图审阅，并显式解决项目规划冲突；系统不会拆分场次或静默改写规则。</p>}
      {state.status === "accepted" && <p>规范头已安装。下一步仍需在既有工作流中完成分镜审核、参考选择、关键帧与媒体准备。</p>}
    </>}
    {error && <ErrorNotice message={error} />}
  </section>;
}
