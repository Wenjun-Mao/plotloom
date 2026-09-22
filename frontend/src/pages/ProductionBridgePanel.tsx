import { useEffect, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Spinner } from "../components";
import type { ProductionBridgeState } from "../types";

/** Explicit F5 evidence projection; it neither approves nor dispatches media. */
export function ProductionBridgePanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const [state, setState] = useState<ProductionBridgeState>();
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const load = () => plotloomApi.getProductionBridge(projectId).then(setState).catch(reason => setError(reason instanceof Error ? reason.message : "无法加载投产提案。"));
  useEffect(() => { setState(undefined); setError(""); void load(); }, [projectId]);
  const run = (operation: () => Promise<ProductionBridgeState>) => { setBusy(true); setError(""); void operation().then(setState).catch(reason => setError(reason instanceof Error ? reason.message : "投产提案操作失败。")).finally(() => setBusy(false)); };
  if (!state) return <section className="panel cast-panel"><header><span>投产提案</span><strong>正在加载</strong></header><Spinner /></section>;
  const proposal = state.proposal;
  return <section className="panel cast-panel" data-testid="production-bridge">
    <header><span>投产提案</span><strong>{state.status === "accepted" ? "已安装" : state.status === "stale" ? "上下文已过期" : "待确认"}</strong></header>
    <p>将已接受的 F5 评审证据映射为规范场次与镜头。不会批准镜头、选择参考、创建资产或发起 H3 工作。</p>
    {state.staleReasons.length > 0 && <div className="notice warning">{state.staleReasons.join("；")}</div>}
    {!proposal && <Button variant="primary" disabled={readOnly || busy} onClick={() => run(() => plotloomApi.prepareProductionBridge(projectId))}>准备投产提案</Button>}
    {proposal && <>
      <p><small>提案 r{proposal.revision} · {proposal.scenes.length} 个场次 · {proposal.cuts.length} 个镜头</small></p>
      {proposal.conflicts.map((conflict, index) => <div className="notice warning" key={`${conflict.code}-${index}`}>{conflict.message}</div>)}
      <details><summary>查看场次与镜头</summary><ul>{proposal.scenes.map((scene, index) => <li key={String(scene.sceneId ?? index)}>{String(scene.sectionId)} / 第 {String(scene.episode)} 集 / 场次 {String(scene.sceneIndex)}：{String(scene.cutCount)} 个镜头</li>)}</ul><ul>{proposal.cuts.map((cut, index) => <li key={String(cut.shotId ?? index)}>{String(cut.shotId)} · {String(cut.seconds)} 秒</li>)}</ul></details>
      <details><summary>技术详情（哈希与冻结输入）</summary><code>{proposal.contentHash}</code></details>
      {state.status !== "accepted" && <Button variant="primary" disabled={readOnly || busy || !proposal.installable} onClick={() => run(() => plotloomApi.acceptProductionBridge(projectId, { expectedProposalRevision: proposal.revision, expectedContentHash: proposal.contentHash }))}>接受并安装</Button>}
      {state.status !== "accepted" && !proposal.installable && <p>请先显式修改项目规划规则或重新准备当前提案；系统不会拆分场次或静默改写规则。</p>}
      {state.status === "accepted" && <p>规范头已安装。下一步仍需在既有工作流中完成分镜审核、参考选择、关键帧与媒体准备。</p>}
    </>}
    {error && <ErrorNotice message={error} />}
  </section>;
}
