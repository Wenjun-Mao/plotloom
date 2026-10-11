import { useGraphWorkbench } from "../../features/graph/GraphWorkbenchContext";
import { useWorkspaceProduction } from "../../features/graph/WorkspaceProductionContext";
import { useReviewWorkflowRead, useBridgeWorkflowRead } from "./ReviewWorkflowReadContext";
import { branchDraftIsDirty, completeMap } from "../../pages/sourceStructureModel";
import { RecommendedWorkflowGuide } from "./RecommendedWorkflowGuide";
import { buildRecommendedWorkflow, type RecommendedWorkflowInput, type RecommendedWorkflowRoute } from "./recommendedWorkflow";

/** Observe the same graph draft as the branch editor; never infer import from delivery. */
export function WorkspaceWorkflowGuide({ input, onNavigate }: {
  input: Omit<RecommendedWorkflowInput, "branchDraft" | "productionRead" | "scriptRead" | "artRead" | "castRead" | "storyboardRead" | "bridgeRead" | "shotRead">;
  onNavigate: (route: RecommendedWorkflowRoute) => void;
}) {
  const owner = useGraphWorkbench();
  const production = useWorkspaceProduction();
  const reviewRead = useReviewWorkflowRead();
  const scriptRead = reviewRead?.stage === "script" ? reviewRead : undefined;
  const artRead = reviewRead?.stage === "art" ? reviewRead : undefined;
  const castRead = reviewRead?.stage === "characters" ? reviewRead : undefined;
  const storyboardRead = reviewRead?.stage === "storyboard-review" ? reviewRead : undefined;
  const shotRead = reviewRead?.stage === "shot-media" ? reviewRead : undefined;
  const bridgeRead = useBridgeWorkflowRead();
  const mapping = owner.draft?.mapping ?? null;
  const pendingFields = Boolean(owner.draft && Object.keys(owner.draft.fieldBuffers).length);
  const model = buildRecommendedWorkflow({ ...input, productionRead: production.data, scriptRead, artRead, castRead, storyboardRead, bridgeRead, shotRead, branchDraft: {
    status: owner.readStatus,
    dirty: branchDraftIsDirty(mapping, input.sourceReview?.acceptedSectionMap ?? null, Boolean(owner.state?.draft))
      || pendingFields,
    complete: completeMap(mapping) && !pendingFields,
    pendingFields,
    stale: owner.stale,
    busy: owner.busy,
    blocked: Boolean(owner.state?.readOnlyReason),
  } });
  return <RecommendedWorkflowGuide model={model} actionDisabled={input.actionDisabled} onNavigate={onNavigate} />;
}
