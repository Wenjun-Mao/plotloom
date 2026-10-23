import { useEffect, useRef } from "react";
import { Button } from "../../components";
import type { ProjectBrief } from "../../types";
import type { BriefStructureBasis } from "./briefStructureBasis";

export const structureTargets = ["nodeBudget", "maxOutDegree", "decisionPointsPerPath", "endingCount", "desiredJoinCount"] as const;
export function BriefTargetPreview({ before, after, basis, busy, onCancel, onConfirm }: { before: ProjectBrief; after: ProjectBrief; basis: BriefStructureBasis; busy: boolean; onCancel: () => void; onConfirm: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const actual = basis.structure;
  const labels = ["节点上限", "最多选项", "每条路线选择次数", "结局数量", "汇合数量"];
  return <dialog ref={dialog} className="graph-command-dialog" aria-label="确认结构目标调整" onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}>
    <h2>确认结构目标调整</h2><p>调整简报目标会使相关建议与后续证据需要重新检查。图的节点、连接、正文和已有媒体均保留；不会自动改图或生成内容。</p>
    <table><thead><tr><th>目标</th><th>当前</th><th>调整后</th></tr></thead><tbody>{structureTargets.map((key, index) => <tr key={key}><td>{labels[index]}</td><td>{before[key]}</td><td>{after[key]}</td></tr>)}</tbody></table>
    <p>预览依据：{basis.label}（打开预览时）。</p>
    {actual ? <><p>当前实际图：{actual.actual.nodes} 节点 · {actual.actual.endings} 结局 · {actual.actual.joins} 汇合 · {actual.actual.routes}{actual.truncated ? "+" : ""} 条完整路线 · 每条路线 {actual.actual.choices.join(" / ") || "尚未完成"} 次选择 · 最多 {actual.actual.degree} 个选项。</p><p>{actual.incomplete ? "当前图尚未完成；计数不代表可确认或应用。" : ""}{actual.mismatches.join("；") || (!actual.incomplete && "当前图符合调整后的结构目标。")}</p></> : <p>无法提供已核实的实际图计数；目标保存后仍需明确审阅并确认图内容。</p>}
    <footer><Button disabled={busy} onClick={onCancel}>取消调整</Button><Button variant="primary" busy={busy} onClick={onConfirm}>确认并保存目标</Button></footer>
  </dialog>;
}
