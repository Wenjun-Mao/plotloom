import { createContext, useContext } from "react";
import type { SectionMap, SourceOutlineReviewState } from "../../types";
import type { GraphAuthoringDraft, GraphCommand, GraphCommandPreview, GraphMapDraft, GraphWorkbenchState } from "./contracts";

export interface GraphWorkbenchController {
  state: GraphWorkbenchState | null;
  readStatus: "loading" | "ready" | "failed";
  readError: string;
  draft: GraphAuthoringDraft | null;
  selectedNodeId: string | null;
  busy: boolean;
  error: string;
  errorDetails?: unknown;
  stale: boolean;
  preview: GraphCommandPreview | null;
  previewConflict: boolean;
  canUndo: boolean;
  refresh: () => Promise<void>;
  selectNode: (identity: string | null) => void;
  changeMapping: (mapping: GraphMapDraft) => void;
  changeDraft: (draft: GraphAuthoringDraft) => void;
  adoptMapping: (mapping: SectionMap) => void;
  saveDraft: () => Promise<boolean>;
  confirmMapping: (source: SourceOutlineReviewState) => Promise<boolean>;
  installMapping: (source: SourceOutlineReviewState) => Promise<boolean>;
  prepareCommand: (command: GraphCommand) => Promise<boolean>;
  cancelPreview: () => void;
  applyPreview: () => Promise<void>;
  undo: () => Promise<void>;
  recover: () => Promise<void>;
  discard: () => Promise<boolean>;
}
export const GraphWorkbenchContext = createContext<GraphWorkbenchController | null>(null);
export function useGraphWorkbench(): GraphWorkbenchController {
  const value = useContext(GraphWorkbenchContext);
  if (!value) throw new Error("The shared graph draft owner is required.");
  return value;
}
