import type { StoryGraph } from "../../src/types";

export function canonicalFourNodeSplit(): StoryGraph {
  return {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "共同开场", kind: "start", summary: "灯塔的值守夜。", footageMode: "footage" },
      { id: "decision", title: "选择照明方向", kind: "decision", summary: "海雾正向港湾推进。", footageMode: "route_only" },
      { id: "sea-ending", title: "继续照向海面", kind: "ending", summary: "航道上的船只看见信标。", footageMode: "footage" },
      { id: "shore-ending", title: "照亮岸边石阶", kind: "ending", summary: "岸边的人们沿石阶撤离。", footageMode: "footage" },
    ],
    edges: [
      { id: "start-decision", sourceNodeId: "start", targetNodeId: "decision", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "decision-sea", sourceNodeId: "decision", targetNodeId: "sea-ending", kind: "choice", choiceText: "继续照向海面", stateEffects: { harbor_signal: "visible" }, entityStateEffects: [{ entityType: "location", entityId: "loc_control", state: "active" }] },
      { id: "decision-shore", sourceNodeId: "decision", targetNodeId: "shore-ending", kind: "choice", choiceText: "照亮岸边石阶", stateEffects: {}, entityStateEffects: [] },
    ], joinContracts: [],
  };
}
