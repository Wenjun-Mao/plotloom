import { useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import type {
  ApprovalDecision,
  ImageJob,
  Shot,
  StoryBible,
  Storyboard,
  VisualIntent,
  VisualWorkbench,
  ReviewedKeyframe,
} from "../../../types";
import {
  type ImageJobDraftTarget,
  useImageJobDirectionDraft,
  useVisualIntentDraft,
  type IntentDraft,
} from "../../../visual-intent-drafts";
import type { ProjectDraftQuiescence } from "../../authoring/projectDraftQuiescence";
import type { MediaReadPhase } from "../useMediaWorkbenchData";
import { currentProductionReferences } from "../references/production-reference";
import { newSamePersonComparisons, latestCurrentReviewsByBinding } from "../references/same-person-draft";
import type { SamePersonComparisonDraft } from "../../../same-person-review-types";
import { ownsOrdinaryIntent } from "./visual-intent-ownership";

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
    sourceBindingId: intent?.intent.targetUse?.source.bindingId,
    retainedVisualIntentId: intent?.intent.targetUse ? intent.id : undefined,
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
  mediaReadPhase,
  imageJobs,
  imageExchangeConfigured,
  imageJobTarget,
  keptAssetId,
  previewLength,
  previewId,
  playing,
  frameIndex,
  referenceCharacterId,
  setPreviewLength,
  setReferenceCharacterId,
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
  mediaReadPhase: MediaReadPhase;
  imageJobs: ImageJob[];
  imageExchangeConfigured: boolean;
  imageJobTarget: ImageJobDraftTarget;
  keptAssetId: string;
  previewLength: number;
  previewId: string;
  playing: boolean;
  frameIndex: number;
  referenceCharacterId: string;
  setPreviewLength: Dispatch<SetStateAction<number>>;
  setReferenceCharacterId: Dispatch<SetStateAction<string>>;
  setSamePersonComparisons: Dispatch<SetStateAction<SamePersonComparisonDraft[]>>;
  setKeptAssetId: Dispatch<SetStateAction<string>>;
  setFrameIndex: Dispatch<SetStateAction<number>>;
}) {
  const retainedSelection = useRef<{
    projectId?: string;
    shotId?: string;
    bindingId?: string;
    initialized: boolean;
  }>({ projectId, shotId: selectedShot?.id, initialized: false });
  const pendingCrossShotUse = useRef<ReviewedKeyframe | null>(null);
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
    () => currentProductionReferences(workbench.characterReferences),
    [workbench.characterReferences],
  );
  const currentMappingForShot = (shot: Shot | undefined) => {
    return (shot?.characterIds ?? []).flatMap((characterId) => {
      const reference = currentReferenceByCharacter.get(characterId);
      return reference ? [{ characterId, referenceDecisionId: reference.id,
        referenceRevision: reference.referenceRevision, characterContextHash: reference.characterContextHash,
        assets: reference.assetHashes.map((asset, index) => ({ ...asset, view: index === 0 ? "primary" as const : "complementary" as const })) }] : [];
    });
  };
  const mappingForBinding = (binding: typeof selectedBinding) => {
    const intent = workbench.visualIntents.find((item) => item.id === binding?.visualIntentId);
    if (!intent?.intent.targetUse) return identityMappingForAsset(binding?.assetId, imageJobs);
    return currentMappingForShot(storyboard.shots.find((item) => item.id === binding?.shotId));
  };
  const selectedIdentityMapping = mappingForBinding(selectedBinding);
  const currentReviewByBinding = useMemo(
    () =>
      latestCurrentReviewsByBinding(workbench.samePersonReviews.reviews),
    [workbench.samePersonReviews.reviews],
  );
  const identityReviewMissingShotIds = previewShotIds.filter((shotId) => {
    const binding = workbench.reviewedKeyframes.find(
      (item) => item.shotId === shotId,
    );
    return (
      mappingForBinding(binding).length > 0 &&
      !currentReviewByBinding.get(binding?.id ?? "")?.productionEligible
    );
  });
  const originJob = imageJobs.find((job) => job.deliveries.some((delivery) => delivery.candidates.some((candidate) => candidate.assetId === keptAssetId)));
  const foreignOrigin = (originJob?.request.frozenSnapshot?.shot?.id && originJob.request.frozenSnapshot.shot.id !== selectedShot?.id)
    || workbench.reviewedKeyframes.some((binding) => binding.assetId === keptAssetId && binding.shotId !== selectedShot?.id);
  const activeIntent = workbench.visualIntents.find((intent) => intent.assetId === keptAssetId &&
    intent.intent.role === "shot_keyframe" && intent.intent.targetUse?.targetShotId === selectedShot?.id
  ) ?? workbench.visualIntents.find(
    (intent) =>
      intent.assetId === keptAssetId && intent.intent.role === "shot_keyframe" &&
      !intent.intent.targetUse && (!foreignOrigin || ownsOrdinaryIntent(intent, selectedShot?.id, workbench.reviewedKeyframes)),
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
  const retainedIdentityMapping = intentDraft.sourceBindingId
    ? currentMappingForShot(selectedShot) : identityMappingForAsset(keptAssetId, imageJobs);
  const retainCrossShotFrame = (binding: ReviewedKeyframe) => {
    if (binding.assetId === keptAssetId) intentEditor.update((value) => ({ ...value, sourceBindingId: binding.id, retainedVisualIntentId: undefined }));
    else { pendingCrossShotUse.current = binding; setKeptAssetId(binding.assetId); }
  };
  useEffect(() => {
    const source = pendingCrossShotUse.current;
    if (source?.assetId === keptAssetId) {
      pendingCrossShotUse.current = null;
      intentEditor.update((value) => ({ ...value, sourceBindingId: source.id, retainedVisualIntentId: undefined }));
    }
  }, [keptAssetId]);
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
    imageJobTarget.kind === "original" ? imageJobTarget.sceneContinuityBindingId ?? "original" : imageJobTarget.kind === "refinement" ? imageJobTarget.parentCandidateAssetId : imageJobTarget.profileId,
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
            ? `请在“角色身份参考”区域为当前制作角色明确选用参考图：${selectedShot.characterIds.filter((characterId) => !currentReferenceByCharacter.has(characterId)).join("、")}。角色页的外观选择不会自动作为制作参考。`
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
  }, [bible.characters, referenceCharacterId]);
  const samePersonIdentityBasis = JSON.stringify([projectId, selectedShot?.id, selectedBinding?.id, selectedIdentityMapping]);
  const samePersonDraftBasis = useRef<string | null>(null);
  useEffect(() => {
    // Read withdrawal is unknown, not a new target. Only a ready exact binding
    // or frozen identity change resets the reviewer's authored observations.
    if (mediaReadPhase !== "ready" || samePersonDraftBasis.current === samePersonIdentityBasis) return;
    samePersonDraftBasis.current = samePersonIdentityBasis;
    setSamePersonComparisons(newSamePersonComparisons(JSON.parse(samePersonIdentityBasis)[3]));
  }, [mediaReadPhase, samePersonIdentityBasis]);
  // Read withdrawal means unknown, not a binding change. Keep explicit creator
  // retention through refresh, and restore only on navigation or an actual
  // authoritative binding transition (ADR 0103).
  useEffect(() => {
    const prior = retainedSelection.current;
    const changedScope = prior.projectId !== projectId
      || prior.shotId !== selectedShot?.id;
    if (changedScope) {
      retainedSelection.current = { projectId, shotId: selectedShot?.id, initialized: false };
      setKeptAssetId("");
    }
    if (mediaReadPhase !== "ready") return;
    const current = retainedSelection.current;
    const targetDraft = activeIntent?.intent.targetUse;
    const staleTargetDraft = !selectedBinding && targetDraft
      && (targetDraft.targetShotId !== selectedShot?.id || activeIntent?.targetUseCurrent !== true);
    if (!current.initialized || current.bindingId !== selectedBinding?.id || staleTargetDraft) {
      const keepCurrentTargetDraft = current.initialized && !selectedBinding
        && activeIntent?.intent.targetUse?.targetShotId === selectedShot?.id
        && activeIntent?.targetUseCurrent === true;
      if (!keepCurrentTargetDraft) setKeptAssetId(selectedBinding?.assetId ?? "");
      retainedSelection.current = { ...current, bindingId: selectedBinding?.id, initialized: true };
    }
  }, [projectId, selectedShot?.id, mediaReadPhase, selectedBinding?.id, activeIntent?.id, activeIntent?.targetUseCurrent]);
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
    retainCrossShotFrame,
    eligibleRefinementCandidates,
    targetCandidate,
    imageJobContextId,
    imageJobDirection,
    imageJobPrerequisite,
  };
}
