import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type MutableRefObject, type ReactNode } from "react";
import { BaseEdge, Controls, EdgeLabelRenderer, MarkerType, Position, ReactFlow, type Edge, type EdgeProps, type Node } from "@xyflow/react";
import { professionalNavigation, useProfessionalPresentation } from "./ProfessionalPresentation";
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
type CanonicalFlowNode = Node<{ label: ReactNode }, "default">;

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

export function CanonicalGraphCanvas({ value, selectedNodeId, onNodeSelect, scrollRef, presentation = "creator" }: {
  value: StoryGraph;
  selectedNodeId?: string | null;
  onNodeSelect?: (identity: string) => void;
  scrollRef?: MutableRefObject<HTMLDivElement | null>;
  presentation?: "creator" | "professional";
}) {
  const session = useProfessionalPresentation();
  const [initialViewport] = useState(presentation === "professional" ? session.viewport : undefined);
  const professional = presentation === "professional";
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
      data: { label: <div className="canonical-node-label nopan nowheel" tabIndex={0}>{storyNodeKindLabels[node.kind]} · {node.title || node.id}</div> },
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

  const canvasStyle = professional ? { width: "100%", height: 540 } : { width: layout.width, height: layout.height };
  return <div ref={setScrollElement} className={`canonical-graph-scroll${professional ? " professional-canonical-scroll" : ""}`} tabIndex={0} aria-label={professional ? "专业路线画布" : "已接受路线横向平移"}>
    <div className="canonical-graph-canvas" style={canvasStyle} onKeyDownCapture={selectFromKeyboard}>
      <ReactFlow className="canonical-graph-flow" style={canvasStyle}
        nodes={nodes} edges={edges} edgeTypes={edgeTypes} fitView={!initialViewport} fitViewOptions={professional ? { padding: .12 } : initialFitOptions} defaultViewport={initialViewport}
        nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} elementsSelectable={false}
        {...(professional ? professionalNavigation : { zoomOnScroll: false, zoomOnPinch: false, zoomOnDoubleClick: false, panOnScroll: false, panOnDrag: false, preventScrolling: false })}
        onMoveEnd={professional ? (_, viewport) => { session.viewport = viewport; } : undefined}
        onNodeClick={onNodeSelect ? (_event, node) => onNodeSelect(node.id) : undefined}>{professional && <Controls showInteractive={false} />}</ReactFlow>
    </div>
  </div>;
}
