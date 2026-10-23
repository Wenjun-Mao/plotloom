import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type MutableRefObject } from "react";
import { BaseEdge, EdgeLabelRenderer, MarkerType, Position, ReactFlow, type Edge, type EdgeProps, type Node } from "@xyflow/react";
import type { StoryGraph } from "../../types";
import { storyNodeKindLabels } from "./presentation";
import { CARD_HEIGHT, CARD_WIDTH, graphTopologyLayout } from "./creatorLayout";

type CanonicalEdgeData = {
  path: string;
  labelX: number;
  labelY: number;
  label: string;
  description: string;
  kind: "choice" | "continuation";
};
type CanonicalFlowEdge = Edge<CanonicalEdgeData, "canonical">;
type CanonicalFlowNode = Node<{ label: string }, "default">;

function CanonicalEdge({ id, data, markerEnd }: EdgeProps<CanonicalFlowEdge>) {
  if (!data) return null;
  return <>
    <BaseEdge id={id} path={data.path} markerEnd={markerEnd} style={{ stroke: data.kind === "choice" ? "var(--accent)" : "var(--line-strong)", strokeWidth: 2 }} />
    <EdgeLabelRenderer>
      <div role="note" tabIndex={0} aria-label={data.description} title={data.description}
        className={`canonical-edge-label ${data.kind} nopan nowheel`} data-edge-label={id}
        style={{ left: data.labelX, top: data.labelY, transform: "translate(-50%, -50%)" }}>
        {data.label}
      </div>
    </EdgeLabelRenderer>
  </>;
}

const edgeTypes = { canonical: CanonicalEdge };
const initialFitOptions = { minZoom: 1, maxZoom: 1, padding: 0.12 };

export function CanonicalGraphCanvas({ value, selectedNodeId, onNodeSelect, scrollRef }: {
  value: StoryGraph;
  selectedNodeId?: string | null;
  onNodeSelect?: (identity: string) => void;
  scrollRef?: MutableRefObject<HTMLDivElement | null>;
}) {
  const scroll = useRef<HTMLDivElement>(null);
  const [availableWidth, setAvailableWidth] = useState(0);
  const setScrollElement = (element: HTMLDivElement | null) => {
    scroll.current = element;
    if (scrollRef) scrollRef.current = element;
  };
  useLayoutEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const measure = () => setAvailableWidth(width => width === element.clientWidth ? width : element.clientWidth);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => graphTopologyLayout(value, availableWidth), [value, availableWidth]);
  const placements = useMemo(() => new Map(layout.nodes.map(placed => [placed.id, placed])), [layout.nodes]);
  const nodes = useMemo<CanonicalFlowNode[]>(() => value.nodes.map(node => {
    const placed = placements.get(node.id)!;
    return {
      id: node.id,
      type: "default",
      position: { x: placed.x, y: placed.y },
      data: { label: `${storyNodeKindLabels[node.kind]} · ${node.title || node.id}` },
      className: `flow-node canonical-flow-node ${node.kind}`,
      focusable: onNodeSelect ? true : undefined,
      selectable: onNodeSelect ? true : undefined,
      selected: onNodeSelect ? selectedNodeId === node.id : undefined,
      ariaLabel: onNodeSelect ? `${storyNodeKindLabels[node.kind]} · ${node.title || node.id}` : undefined,
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      style: { width: CARD_WIDTH, height: CARD_HEIGHT, padding: 12 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    };
  }), [placements, value.nodes, onNodeSelect, selectedNodeId]);
  const edges = useMemo<CanonicalFlowEdge[]>(() => layout.edges.map(({ edge, path, labelX, labelY }) => {
    const source = value.nodes.find(node => node.id === edge.sourceNodeId)!;
    const target = value.nodes.find(node => node.id === edge.targetNodeId)!;
    const label = edge.choiceText || (edge.kind === "choice" ? "待填写选项" : "后续");
    return {
      id: edge.id,
      source: edge.sourceNodeId,
      target: edge.targetNodeId,
      type: "canonical",
      markerEnd: { type: MarkerType.ArrowClosed },
      data: {
        path,
        labelX,
        labelY,
        label,
        kind: edge.kind,
        description: `${edge.kind === "choice" ? "选项" : "后续"}：${label} · ${source.title || source.id} → ${target.title || target.id}`,
      },
    };
  }), [layout.edges, value.nodes]);

  const selectFromKeyboard = onNodeSelect ? (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const nodeElement = (event.target as Element).closest<HTMLElement>(".canonical-flow-node");
    const identity = nodeElement?.dataset.id;
    if (!identity) return;
    // The graph is controlled and has no authoring onNodesChange handler, so
    // keyboard selection must update the presentation owner directly.
    event.preventDefault();
    event.stopPropagation();
    onNodeSelect(identity);
  } : undefined;

  return <div ref={setScrollElement} className="canonical-graph-scroll" tabIndex={0} aria-label="已接受路线横向平移">
    <div className="canonical-graph-canvas" style={{ width: layout.width, height: layout.height }} onKeyDownCapture={selectFromKeyboard}>
      <ReactFlow className="canonical-graph-flow" style={{ width: layout.width, height: layout.height }}
        nodes={nodes} edges={edges} edgeTypes={edgeTypes} fitView fitViewOptions={initialFitOptions}
        nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} elementsSelectable={false}
        zoomOnScroll={onNodeSelect ? false : undefined} zoomOnPinch={onNodeSelect ? false : undefined}
        zoomOnDoubleClick={onNodeSelect ? false : undefined} panOnScroll={onNodeSelect ? false : undefined}
        panOnDrag={onNodeSelect ? false : undefined} preventScrolling={onNodeSelect ? false : undefined}
        onNodeClick={onNodeSelect ? (_event, node) => onNodeSelect(node.id) : undefined} />
    </div>
  </div>;
}
