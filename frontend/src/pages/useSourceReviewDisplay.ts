import { useRef } from "react";
import type { SourceOutlineReviewState } from "../types";
import type { WorkspaceSourceReviewRead } from "../app/workspace/useWorkspaceSourceReview";

/** Retained content is for reading only; the shared owner still controls verified authority. */
export function useSourceReviewDisplay(projectId: string, owner: Pick<WorkspaceSourceReviewRead, "value" | "status">) {
  const retained = useRef<{ projectId: string; value: SourceOutlineReviewState | null }>({ projectId, value: null });
  if (retained.current.projectId !== projectId) retained.current = { projectId, value: null };
  if (owner.status === "ready") retained.current.value = owner.value;
  return retained.current.value;
}
