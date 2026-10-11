import { useGraphWorkbench } from "../../features/graph/GraphWorkbenchContext";
import { branchDraftIsDirty, completeMap } from "../../pages/sourceStructureModel";
import { RecommendedWorkflowGuide } from "./RecommendedWorkflowGuide";
import { buildRecommendedWorkflow, type RecommendedWorkflowInput, type RecommendedWorkflowRoute } from "./recommendedWorkflow";

/** Observe the same graph draft as the branch editor; never infer import from delivery. */
export function WorkspaceWorkflowGuide({ input, onNavigate }: {
  input: Omit<RecommendedWorkflowInput, "branchDraft">;
  onNavigate: (route: RecommendedWorkflowRoute) => void;
}) {
  const owner = useGraphWorkbench();
  const mapping = owner.draft?.mapping ?? null;
  const model = buildRecommendedWorkflow({ ...input, branchDraft: {
    status: owner.readStatus,
    dirty: branchDraftIsDirty(mapping, input.sourceReview?.acceptedSectionMap ?? null, Boolean(owner.state?.draft)),
    complete: completeMap(mapping),
    stale: owner.stale,
    busy: owner.busy,
    blocked: Boolean(owner.state?.readOnlyReason),
  } });
  return <RecommendedWorkflowGuide model={model} actionDisabled={input.actionDisabled} onNavigate={onNavigate} />;
}
