import { useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import type {
  ApprovalDecision,
  ImageJob,
  SamePersonComparison,
  Shot,
  StoryBible,
  Storyboard,
  VisualIntent,
  VisualWorkbench,
} from "../../../types";
import {
  type ImageJobDraftTarget,
  useImageJobDirectionDraft,
  useVisualIntentDraft,
  type IntentDraft,
} from "../../../visual-intent-drafts";
import type { ProjectDraftQuiescence } from "../../authoring/projectDraftQuiescence";

function draftFor(
  intent: VisualIntent | undefined,
  shot: Shot | undefined,
): IntentDraft {
  return {
    identityIntent: intent?.intent.identityIntent ?? "",
    compositionIntent:
      intent?.intent.compositionIntent ?? shot?.composition ?? "",
    styleIntent: intent?.intent.styleIntent ?? shot?.visualIntent ?? "",
    sourceRefs: intent?.intent.sourceRefs.join("\n") ?? "",
  };
}

function identityMappingForAsset(
  assetId: string | undefined,
  jobs: ImageJob[],
) {
  if (!assetId) return [];
  const job = jobs.find((candidateJob) =>
    candidateJob.deliveries.some((delivery) =>
      delivery.candidates.some((candidate) => candidate.assetId === assetId),
    ),
  );
  return job?.request.frozenSnapshot?.characterIdentity ?? [];
}

export function useMediaSelectionContext({
  projectId,
  storyboard,
  bible,
  selectedShot,
  storyboardRevision,
  mediaDraftsEnabled,
  draftQuiescence,
  currentApproval,
  workbench,
  imageJobs,
  imageExchangeConfigured,
  imageJobTarget,
  keptAssetId,
  previewLength,
  previewId,
  playing,
  frameIndex,
  referenceCharacterId,
  proposalCharacterId,
  setPreviewLength,
  setReferenceCharacterId,
  setProposalCharacterId,
  setSamePersonComparisons,
  setKeptAssetId,
  setFrameIndex,
}: {
  projectId?: string;
  storyboard: Storyboard;
  bible: StoryBible;
  selectedShot: Shot | undefined;
  storyboardRevision?: number;
  mediaDraftsEnabled: boolean;
  draftQuiescence?: ProjectDraftQuiescence;
  currentApproval: ApprovalDecision | undefined;
  workbench: VisualWorkbench;
  imageJobs: ImageJob[];
  imageExchangeConfigured: boolean;
  imageJobTarget: ImageJobDraftTarget;
  keptAssetId: string;
  previewLength: number;
  previewId: string;
  playing: boolean;
  frameIndex: number;
  referenceCharacterId: string;
  proposalCharacterId: string;
  setPreviewLength: Dispatch<SetStateAction<number>>;
  setReferenceCharacterId: Dispatch<SetStateAction<string>>;
  setProposalCharacterId: Dispatch<SetStateAction<string>>;
  setSamePersonComparisons: Dispatch<SetStateAction<SamePersonComparison[]>>;
  setKeptAssetId: Dispatch<SetStateAction<string>>;
  setFrameIndex: Dispatch<SetStateAction<number>>;
}) {
  const priorProjectId = useRef(projectId);
  const sceneShots = useMemo(
    () =>
      selectedShot
        ? storyboard.shots
            .filter((shot) => shot.sceneId === selectedShot.sceneId)
            .sort((left, right) => left.order - right.order)
        : [],
    [storyboard, selectedShot],
  );
  const previewStart = selectedShot
    ? sceneShots.findIndex((shot) => shot.id === selectedShot.id)
    : -1;
  const maxPreviewLength =
    previewStart < 0 ? 0 : sceneShots.length - previewStart;
  const previewShotIds = useMemo(
    () =>
      previewStart < 0
        ? []
        : sceneShots
            .slice(
              previewStart,
              previewStart + Math.min(previewLength, maxPreviewLength),
            )
            .map((shot) => shot.id),
    [maxPreviewLength, previewLength, previewStart, sceneShots],
  );
  const preview = workbench.previews.find((item) => item.id === previewId);
  const reviewedShotIds = useMemo(
    () => new Set(workbench.reviewedKeyframes.map((binding) => binding.shotId)),
    [workbench.reviewedKeyframes],
  );
  const missingPreviewShotIds = previewShotIds.filter(
    (shotId) => !reviewedShotIds.has(shotId),
  );
  const selectedBinding = selectedShot
    ? workbench.reviewedKeyframes.find(
        (binding) => binding.shotId === selectedShot.id,
      )
    : undefined;
  const assetById = useMemo(
    () => new Map(workbench.assets.map((asset) => [asset.id, asset])),
    [workbench.assets],
  );
  const referenceStateByCharacter = useMemo(
    () =>
      new Map(
        workbench.characterReferences.states.map((state) => [
          state.characterId,
          state,
        ]),
      ),
    [workbench.characterReferences.states],
  );
  const currentReferenceByCharacter = useMemo(
    () =>
      new Map(
        workbench.characterReferences.decisions
          .filter((decision) => decision.current)
          .map((decision) => [decision.characterId, decision]),
      ),
    [workbench.characterReferences.decisions],
  );
  const selectedIdentityMapping = useMemo(
    () => identityMappingForAsset(selectedBinding?.assetId, imageJobs),
    [imageJobs, selectedBinding?.assetId],
  );
  const retainedIdentityMapping = useMemo(
    () => identityMappingForAsset(keptAssetId, imageJobs),
    [imageJobs, keptAssetId],
  );
  const currentReviewByBinding = useMemo(
    () =>
      new Map(
        workbench.samePersonReviews.reviews
          .filter((item) => item.current)
          .map((item) => [item.bindingId, item]),
      ),
    [workbench.samePersonReviews.reviews],
  );
  const identityReviewMissingShotIds = previewShotIds.filter((shotId) => {
    const binding = workbench.reviewedKeyframes.find(
      (item) => item.shotId === shotId,
    );
    return (
      identityMappingForAsset(binding?.assetId, imageJobs).length > 0 &&
      !currentReviewByBinding.has(binding?.id ?? "")
    );
  });
  const activeIntent = workbench.visualIntents.find(
    (intent) =>
      intent.assetId === keptAssetId && intent.intent.role === "shot_keyframe",
  );
  const intentEditor = useVisualIntentDraft(
    projectId,
    selectedShot?.id,
    keptAssetId,
    activeIntent?.id,
    draftFor(activeIntent, selectedShot),
    storyboardRevision,
    mediaDraftsEnabled,
    draftQuiescence,
  );
  const intentDraft = intentEditor.value;
  const setIntentDraft = intentEditor.update;
  const eligibleRefinementCandidates = useMemo(
    () =>
      imageJobs
        .filter((job) => job.current)
        .flatMap((job) =>
          job.deliveries.flatMap((delivery) => delivery.candidates),
        )
        .filter((candidate) => candidate.assetId === selectedBinding?.assetId),
    [imageJobs, selectedBinding?.assetId],
  );
  const targetCandidate =
    imageJobTarget.kind === "refinement"
      ? eligibleRefinementCandidates.find(
          (candidate) =>
            candidate.assetId === imageJobTarget.parentCandidateAssetId,
        )
      : undefined;
  const imageJobContextId = [
    currentApproval?.id ?? "no-approval",
    `storyboard-${storyboardRevision ?? 0}`,
    imageJobTarget.kind === "original" ? "original" : imageJobTarget.kind === "refinement" ? imageJobTarget.parentCandidateAssetId : imageJobTarget.profileId,
    selectedBinding?.id ?? "no-binding",
    `selection-${selectedBinding?.selectionRevision ?? 0}`,
    `intent-${selectedBinding?.visualIntentRevision ?? 0}`,
  ].join(":");
  const imageJobDirection = useImageJobDirectionDraft(
    projectId,
    selectedShot?.id,
    imageJobTarget,
    imageJobContextId,
    storyboardRevision,
    mediaDraftsEnabled,
    draftQuiescence,
  );
  const imageJobPrerequisite = !projectId
    ? "先保存项目。"
    : !imageExchangeConfigured
      ? "先在同一主机设置 PLOTLOOM_IMAGE_EXCHANGE_ROOT 并重启服务。"
      : !selectedShot
        ? "先选择一个镜头。"
        : !currentApproval || !storyboardRevision
          ? "先保存有效分镜、检查 Gate receipt，再显式批准当前分镜。"
          : selectedShot.characterIds.some(
                (characterId) => !currentReferenceByCharacter.has(characterId),
              )
            ? `当前 Shot 的可见角色缺少已选择的身份参考：${selectedShot.characterIds.filter((characterId) => !currentReferenceByCharacter.has(characterId)).join("、")}。`
            : imageJobTarget.kind === "refinement" && !targetCandidate
              ? "参考细化只能使用当前镜头已审核选择的当前 P1 候选。"
              : imageJobTarget.kind === "keyframe_adaptation" && !selectedBinding
                ? "关键帧比例适配需要当前镜头的审核关键帧。"
              : null;

  useEffect(() => {
    setPreviewLength((current) =>
      Math.max(1, Math.min(current, maxPreviewLength || 1)),
    );
  }, [maxPreviewLength]);
  useEffect(() => {
    if (!referenceCharacterId && bible.characters[0])
      setReferenceCharacterId(bible.characters[0].id);
    if (!proposalCharacterId && bible.characters[0])
      setProposalCharacterId(bible.characters[0].id);
  }, [bible.characters, proposalCharacterId, referenceCharacterId]);
  useEffect(() => {
    setSamePersonComparisons(
      selectedIdentityMapping.map((item) => ({
        characterId: item.characterId,
        judgment: "pass",
        identityNotes:
          "Face, build, and stable visual anchors match the selected reference.",
        stateNotes:
          "Current shot state is judged separately from durable identity.",
      })),
    );
  }, [selectedBinding?.id, selectedIdentityMapping]);
  // A reviewed binding is durable per Shot. Restore it after a reload or a
  // parent review refresh rather than making the creator rediscover which
  // candidate and intent revision were already selected.
  useEffect(() => {
    const changedProject = priorProjectId.current !== projectId;
    priorProjectId.current = projectId;
    if (selectedBinding) setKeptAssetId(selectedBinding.assetId);
    else if (changedProject) setKeptAssetId("");
  }, [projectId, selectedBinding?.id]);
  useEffect(() => {
    if (!playing || !preview) return;
    const frame = preview.manifest.frames[frameIndex];
    if (!frame) return;
    // Frozen duration is the playback contract; do not add a UI timing floor.
    const timer = window.setTimeout(
      () =>
        setFrameIndex(
          (current) => (current + 1) % preview.manifest.frames.length,
        ),
      frame.durationMs,
    );
    return () => window.clearTimeout(timer);
  }, [playing, preview, frameIndex]);

  return {
    maxPreviewLength,
    previewShotIds,
    preview,
    missingPreviewShotIds,
    selectedBinding,
    assetById,
    referenceStateByCharacter,
    currentReferenceByCharacter,
    selectedIdentityMapping,
    retainedIdentityMapping,
    currentReviewByBinding,
    identityReviewMissingShotIds,
    activeIntent,
    intentEditor,
    intentDraft,
    eligibleRefinementCandidates,
    targetCandidate,
    imageJobContextId,
    imageJobDirection,
    imageJobPrerequisite,
  };
}
