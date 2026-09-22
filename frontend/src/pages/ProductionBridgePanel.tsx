import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProductionBridgeIntentEntry, ProductionBridgeState } from "../types";

/** Explicit F5 evidence projection; it neither approves nor dispatches media. */
export function ProductionBridgePanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ProductionBridgeState>();
  const [intentEntries, setIntentEntries] = useState<ProductionBridgeIntentEntry[]>([]);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const activeRequest = useRef({ projectId, epoch: 0, request: 0 });
  const draftProposalKey = useRef<string | undefined>(undefined);
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
  // Advance ownership before paint so a prior project's late promise cannot replace this view.
  useLayoutEffect(() => {
    const current = activeRequest.current;
    const request = { projectId, epoch: current.epoch + 1, request: current.request + 1 };
    activeRequest.current = request;
    draftProposalKey.current = undefined;
    setState(undefined); setIntentEntries([]); setBusy(false); setError("");
    void plotloomApi.getProductionBridge(projectId)
      .then(next => { if (owns(request)) setState(next); })
      .catch(reason => { if (owns(request)) setError(reason instanceof Error ? reason.message : "无法加载投产提案。"); });
  }, [projectId]);
  useEffect(() => {
    const proposal = state?.proposal;
    if (!proposal) return;
    const proposalKey = `${projectId}:${proposal.revision}:${proposal.contentHash}`;
    if (draftProposalKey.current !== proposalKey) {
      draftProposalKey.current = proposalKey;
      setIntentEntries(proposal.intentPackage.entries);
    }
  }, [projectId, state?.proposal?.contentHash, state?.proposal?.revision]);
  const run = (operation: () => Promise<ProductionBridgeState>) => {
    const request = beginRequest();
    setBusy(true); setError("");
    void operation()
      .then(next => { if (owns(request)) setState(next); })
      .catch(reason => { if (owns(request)) setError(reason instanceof Error ? reason.message : "投产提案操作失败。"); })
      .finally(() => { if (owns(request)) setBusy(false); });
  };
  if (!state) return <section className="panel cast-panel"><header><span>投产提案</span><strong>正在加载</strong></header><Spinner /></section>;
  const proposal = state.proposal;
  const intentDirty = intentEntries.length !== proposal?.intentPackage.entries.length
    || intentEntries.some((entry, index) => entry.id !== proposal?.intentPackage.entries[index]?.id || entry.text !== proposal?.intentPackage.entries[index]?.text);
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{state.status === "accepted" ? "已安装" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    <p>将已接受的 F5 评审证据映射为规范场次与镜头。不会批准镜头、选择参考、创建资产或发起 H3 工作。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!proposal && <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareProductionBridge(projectId))}>准备投产提案</Button>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{conflict.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 集 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((cut, index) => <li key={String(cut.shotId ?? index)}>{String(cut.shotId)} · {String(cut.seconds)} 秒</li>)}</ul></details>
      <details open><summary>来源摘录审阅补充（一个可编辑的整包）</summary>
        <p><small>这些摘录不是 F1–F5 的冻结事实，也不是模型推断；它们以 {proposal.intentPackage.method} 从已接受坐标确定性生成，必须随整包明确保存。</small></p>
        {intentEntries.map((entry, index) => <label key={entry.id} className="stacked-field"><span>{entry.targetKind === "scene_objective" ? "场次目标" : "节拍目的"} · {entry.targetId} <small>（来源 {String(entry.sourceCoordinates.sectionId)}{entry.targetKind === "beat_purpose" ? ` / 流 ${String(entry.sourceCoordinates.flowIndex)}` : ""}）</small></span><textarea disabled={readOnly || busy || state.status === "accepted"} value={entry.text} onChange={event => setIntentEntries(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><small>原始建议：{entry.suggestedText}</small></label>)}
        {state.status !== "accepted" && <Button disabled={readOnly || busy || !intentDirty || intentEntries.some(entry => !entry.text.trim())} onClick={() => run(() => plotloomApi.updateProductionBridgeIntent(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash, entries: intentEntries.map(entry => ({ id: entry.id, text: entry.text })) }))}>保存来源摘录整包</Button>}
        {state.status !== "accepted" && intentDirty && <p><small>当前编辑尚未保存；接受安装会保持禁用，直到显示的整包已保存。</small></p>}
      </details>
      <details><summary>技术详情（哈希与冻结输入）</summary><code>{proposal.contentHash}</code></details>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable || intentDirty} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>接受并安装</Button>}
      {state.status !== "accepted" && !proposal.installable && <p>请先显式修改项目规划规则或重新准备当前提案；系统不会拆分场次或静默改写规则。</p>}
      {state.status === "accepted" && <p>规范头已安装。下一步仍需在既有工作流中完成分镜审核、参考选择、关键帧与媒体准备。</p>}
    </>}
    {error && <ErrorNotice message={error} />}
  </section>;
}
