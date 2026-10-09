import type { GraphAuthoringDraft, DraftEdge } from "./contracts";

export const CARD_WIDTH = 194, CARD_HEIGHT = 112, ROW_PITCH = 256, COLUMN_GAP = 34, GUTTER = 48;
export interface PlacedNode { id: string; rank: number; x: number; y: number; detached: boolean }
export interface PlacedEdge { edge: DraftEdge; path: string; labelX: number; labelY: number }
export interface CreatorLayout { nodes: PlacedNode[]; edges: PlacedEdge[]; rows: Array<{ rank: number; nodes: string[]; y: number }>; width: number; height: number }

/** Stable node order breaks ties; row hints only place unconnected roots. */
export function creatorLayout(draft: GraphAuthoringDraft, availableWidth: number): CreatorLayout {
  const { topology } = draft.mapping, rank = new Map<string, number>(), reachable = new Set<string>();
  const connected = topology.edges.filter(edge => edge.sourceNodeId && edge.targetNodeId);
  const incoming = (id: string) => connected.filter(edge => edge.targetNodeId === id);
  for (const node of topology.nodes) rank.set(node.id, node.id === topology.startNodeId ? 0 : incoming(node.id).length ? 0 : Math.max(0, draft.rowHints[node.id] ?? 0));
  // Valid command drafts are acyclic; the bounded pass also renders an unsafe
  // recovery record without entering an unbounded layout loop.
  for (let pass = 0; pass < topology.nodes.length; pass++) {
    let changed = false;
    for (const edge of connected) {
      const next = Math.min(128, (rank.get(edge.sourceNodeId!) ?? 0) + 1);
      if (next > (rank.get(edge.targetNodeId!) ?? 0)) { rank.set(edge.targetNodeId!, next); changed = true; }
    }
    if (!changed) break;
  }
  const visit = (id: string) => { if (reachable.has(id)) return; reachable.add(id); connected.filter(edge => edge.sourceNodeId === id).forEach(edge => visit(edge.targetNodeId!)); };
  if (topology.startNodeId) visit(topology.startNodeId);
  const ranks = [...new Set(rank.values())].sort((a, b) => a - b);
  const rows = ranks.map(value => ({ rank: value, nodes: topology.nodes.filter(node => rank.get(node.id) === value).map(node => node.id), y: 32 + value * ROW_PITCH }));
  const widest = Math.max(1, ...rows.map(row => row.nodes.length));
  const labelsByRank = new Map(ranks.map(value => [value, connected.filter(edge => rank.get(edge.targetNodeId!) === value)]));
  const columns = Math.max(widest, ...[...labelsByRank.values()].map(edges => edges.length));
  const width = Math.max(availableWidth, columns * CARD_WIDTH + (columns - 1) * COLUMN_GAP + GUTTER * 2 + 48);
  const nodes = rows.flatMap(row => {
    const rowWidth = row.nodes.length * CARD_WIDTH + (row.nodes.length - 1) * COLUMN_GAP;
    return row.nodes.map((id, index) => ({ id, rank: row.rank, x: (width - 48 - rowWidth) / 2 + index * (CARD_WIDTH + COLUMN_GAP), y: row.y, detached: !reachable.has(id) }));
  });
  const byId = new Map(nodes.map(node => [node.id, node]));
  // Structural edits append identities, but label lanes must follow visible
  // targets (and sources at a join), not historical edge creation order.
  for (const lane of labelsByRank.values()) lane.sort((left, right) =>
    (byId.get(left.targetNodeId!)?.x ?? 0) - (byId.get(right.targetNodeId!)?.x ?? 0)
    || (byId.get(left.sourceNodeId!)?.x ?? 0) - (byId.get(right.sourceNodeId!)?.x ?? 0));
  const edges = connected.flatMap((edge, index) => {
    const source = byId.get(edge.sourceNodeId!), target = byId.get(edge.targetNodeId!);
    if (!source || !target) return [];
    const sx = source.x + CARD_WIDTH / 2, sy = source.y + CARD_HEIGHT + 9, tx = target.x + CARD_WIDTH / 2, ty = target.y - 9;
    const short = target.rank === source.rank + 1;
    // Every incoming label owns a separate lane, including converging and skip
    // links. They share the row gap without occluding exact-edge controls.
    const lane = labelsByRank.get(target.rank)!;
    const labelX = (width - 48 - (lane.length - 1) * (CARD_WIDTH + COLUMN_GAP)) / 2 + lane.findIndex(item => item.id === edge.id) * (CARD_WIDTH + COLUMN_GAP);
    const labelY = ty - 59;
    // Skip links travel through an outside gutter rather than through cards.
    const gutter = 12 + index % 4 * 8;
    const path = short ? `M ${sx} ${sy} C ${sx} ${labelY}, ${labelX} ${labelY}, ${labelX} ${labelY} C ${labelX} ${labelY}, ${tx} ${labelY}, ${tx} ${ty}`
      : `M ${sx} ${sy} L ${sx} ${sy + 22} Q ${sx} ${sy + 30} ${sx - 8} ${sy + 30} L ${gutter + 8} ${sy + 30} Q ${gutter} ${sy + 30} ${gutter} ${sy + 38} L ${gutter} ${labelY - 8} Q ${gutter} ${labelY} ${gutter + 8} ${labelY} L ${labelX} ${labelY} C ${labelX} ${labelY}, ${tx} ${labelY}, ${tx} ${ty}`;
    return [{ edge, path, labelX, labelY }];
  });
  return { nodes, edges, rows, width, height: Math.max(320, (rows.at(-1)?.y ?? 0) + ROW_PITCH) };
}

export function rowConnectionDefaults(draft: GraphAuthoringDraft, nodeIds: string[]) {
  const edges = draft.mapping.topology.edges, nodes = draft.mapping.topology.nodes;
  const inputs = nodeIds.map(id => edges.filter(edge => edge.targetNodeId === id));
  const sources = new Set(inputs.flatMap(edges => edges.map(edge => edge.sourceNodeId)));
  const candidateParent = sources.size === 1 ? [...sources][0] : null;
  const parent = candidateParent && inputs.every(edges => edges.length > 0 && edges.every(edge => edge.kind === "choice" && edge.sourceNodeId === candidateParent))
    && nodes.find(node => node.id === candidateParent)?.kind === "decision" ? candidateParent : null;
  const outputs = nodeIds.map(id => edges.filter(edge => edge.sourceNodeId === id));
  const targets = new Set(outputs.flatMap(edges => edges.map(edge => edge.targetNodeId)));
  const candidate = targets.size === 1 ? [...targets][0] : null;
  const target = parent && outputs.every(edges => edges.length === 1) && nodes.some(node => node.id === candidate && ["join", "ending"].includes(node.kind)) ? candidate : null;
  return { parent, target };
}
