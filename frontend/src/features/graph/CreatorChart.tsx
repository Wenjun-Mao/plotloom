import { useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { CARD_WIDTH, CARD_HEIGHT, type CreatorLayout } from "./creatorLayout";
import type { CreatorEdit } from "./CreatorEditDialog";
import { storyNodeKindLabels } from "./presentation";

export function CreatorChart({ layout, disabled, onEdit }: { layout: CreatorLayout; disabled: boolean; onEdit: (action: CreatorEdit) => void }) {
  const owner = useGraphWorkbench(), draft = owner.draft!, root = useRef<HTMLDivElement>(null);
  const dragging = useRef<{ source: string; startX: number; startY: number } | null>(null);
  const [dragLine, setDragLine] = useState<{ x: number; y: number; sx: number; sy: number } | null>(null);
  const title = (id: string) => draft.mapping.sections.find(section => section.sectionId === id)?.title || "待填写节点";
  const cancel = () => { dragging.current = null; setDragLine(null); };
  useEffect(() => { const escape = (event: KeyboardEvent) => { if (event.key === "Escape") cancel(); }; window.addEventListener("keydown", escape); return () => window.removeEventListener("keydown", escape); }, []);
  const finish = (event: PointerEvent<HTMLButtonElement>) => {
    const gesture = dragging.current; if (!gesture) return;
    const moved = Math.hypot(event.clientX - gesture.startX, event.clientY - gesture.startY) > 6;
    const dropped = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>("[data-creator-node]")?.dataset.creatorNode;
    const outputs = draft.mapping.topology.edges.filter(edge => edge.sourceNodeId === gesture.source);
    cancel();
    onEdit({ type: "connection", nodeId: gesture.source, endpoint: "target", edgeId: outputs.length === 1 ? outputs[0].id : null, targetNodeId: moved ? dropped : undefined });
  };
  return <div ref={root} className="creator-chart" style={{ width: layout.width, height: layout.height }} aria-label="自动布局剧情图">
    <svg className="creator-arrows" width={layout.width} height={layout.height} aria-hidden="true"><defs><marker id="creator-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M 0 0 L 8 4 L 0 8 z" fill="currentColor" /></marker></defs>
      {layout.edges.map(({ edge, path }) => <path key={edge.id} data-creator-edge={edge.id} d={path} className={edge.kind} markerEnd="url(#creator-arrow)" />)}
      {dragLine && <path className="creator-drag-line" d={`M ${dragLine.sx} ${dragLine.sy} L ${dragLine.x} ${dragLine.y}`} />}
    </svg>
    {layout.edges.map(({ edge, labelX, labelY }) => {
      const option = draft.mapping.choices.flatMap(choice => choice.outcomes).find(option => option.outcomeId === edge.id);
      return <button key={edge.id} type="button" className={`creator-edge-label ${edge.kind}`} data-edge-label={edge.id} style={{ left: labelX, top: labelY }} title={`${option?.label || "后续"} · ${title(edge.sourceNodeId!)} → ${title(edge.targetNodeId!)}`} disabled={disabled} onClick={() => onEdit({ type: "connection", nodeId: edge.sourceNodeId!, endpoint: "target", edgeId: edge.id })}>{option?.label || (edge.kind === "choice" ? "待填写选项" : "后续")}</button>;
    })}
    {layout.nodes.map(placed => {
      const node = draft.mapping.topology.nodes.find(node => node.id === placed.id)!, section = draft.mapping.sections.find(section => section.sectionId === placed.id)!;
      const inputs = draft.mapping.topology.edges.filter(edge => edge.targetNodeId === node.id);
      return <article key={node.id} data-creator-node={node.id} data-rank={placed.rank} className={`creator-node ${node.kind}${owner.selectedNodeId === node.id ? " selected" : ""}${placed.detached ? " detached" : ""}`} style={{ left: placed.x, top: placed.y, width: CARD_WIDTH, height: CARD_HEIGHT }}>
        <button type="button" className="creator-node-select" aria-label={`选择节点 ${section.title || node.id}`} aria-pressed={owner.selectedNodeId === node.id} onClick={() => owner.selectNode(node.id)}><span>{storyNodeKindLabels[node.kind]}{placed.detached ? " · 未接入" : ""}</span><strong title={section.title}>{section.title || "待填写标题"}</strong><small>{section.footageMode === "route_only" ? "路线控制 · 无需拍摄" : section.summary || "待填写剧情"}</small></button>
        <button type="button" className="creator-port input" aria-label={`修改 ${section.title || node.id} 的输入`} title="逐条选择新的精确输入" disabled={disabled || node.id === draft.mapping.topology.startNodeId} onClick={() => onEdit({ type: "connection", nodeId: node.id, endpoint: "source", edgeId: inputs.length === 1 ? inputs[0].id : null })}>↑</button>
        <button type="button" className="creator-port output" aria-label={`连接 ${section.title || node.id} 的后续`} title="点击编辑后续，或拖到目标节点" disabled={disabled || node.kind === "ending"}
          onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); dragging.current = { source: node.id, startX: event.clientX, startY: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId); }}
          onPointerMove={event => { if (!dragging.current || !root.current) return; const rect = root.current.getBoundingClientRect(); setDragLine({ sx: placed.x + CARD_WIDTH / 2, sy: placed.y + CARD_HEIGHT + 10, x: event.clientX - rect.left, y: event.clientY - rect.top }); }}
          onPointerUp={finish} onPointerCancel={cancel} onLostPointerCapture={cancel}
          onClick={event => { if (event.detail === 0) onEdit({ type: "connection", nodeId: node.id, endpoint: "target", edgeId: null }); }}>↓</button>
      </article>;
    })}
    {layout.rows.map(row => {
      const last = layout.nodes.filter(node => node.rank === row.rank).at(-1)!;
      return <div key={row.rank}><button type="button" className="creator-row-add" aria-label={`向第 ${row.rank + 1} 行添加节点`} style={{ left: last.x + CARD_WIDTH + 12, top: row.y + 34 }} disabled={disabled} onClick={() => onEdit({ type: "row", rank: row.rank, nodes: row.nodes })}><span className="creator-row-add-icon" aria-hidden="true" /></button>
        <button type="button" className="creator-row-insert" aria-label={`在第 ${row.rank + 1} 行后插入新一行`} style={{ left: layout.width / 2 - 65, top: row.y + CARD_HEIGHT + 106 }} disabled={disabled} onClick={() => onEdit({ type: "insert", rank: row.rank + 1, edgeId: null })}>插入新一行</button></div>;
    })}
  </div>;
}
