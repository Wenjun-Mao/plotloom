import type { ProjectBrief, StoryGraph } from "../../types";
import type { GraphWorkbenchController } from "./GraphWorkbenchContext";
import { canonicalStructure, creatorStructure } from "./creatorStructure";

export function briefStructureBasis(owner: GraphWorkbenchController | null, graph: StoryGraph | undefined, brief: ProjectBrief) {
  if (!owner || owner.readStatus !== "ready" || owner.stale || !owner.state) return { label: "当前图尚未核实", structure: null };
  // An initial/unsaved editable payload is still the shared draft basis.
  if (owner.draft && !owner.state.readOnlyReason) return { label: "当前共享图草稿", structure: creatorStructure(owner.draft, brief) };
  if (owner.state.readOnlyReason && graph) return { label: "当前已接受规范图", structure: canonicalStructure(graph, brief) };
  return { label: "当前图尚未建立", structure: null };
}
export type BriefStructureBasis = ReturnType<typeof briefStructureBasis>;
