import { createContext, useContext, type ReactNode } from "react";
import type { WorkspaceProject } from "../../types";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { useCreatorProduction } from "./useCreatorProduction";

export const WorkspaceProductionContext = createContext<ReturnType<typeof useCreatorProduction> | null>(null);

/** One observer for the guide and node inspector; review pages still own writes. */
export function WorkspaceProductionProvider({ project, active, children }: { project: WorkspaceProject; active: boolean; children: ReactNode }) {
  const graph = useGraphWorkbench();
  const read = useCreatorProduction(project, graph.state?.bindingHash, active && graph.readStatus === "ready" && Boolean(graph.state));
  return <WorkspaceProductionContext.Provider value={read}>{children}</WorkspaceProductionContext.Provider>;
}

export function useWorkspaceProduction() {
  const read = useContext(WorkspaceProductionContext);
  if (!read) throw new Error("The shared workspace production observer is required.");
  return read;
}
