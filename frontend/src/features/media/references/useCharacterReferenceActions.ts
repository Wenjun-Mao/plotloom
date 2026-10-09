import type { Dispatch, SetStateAction } from "react";
import type {
  CharacterReferenceState,
  ReviewedKeyframe,
  SamePersonComparison,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";

export function useCharacterReferenceActions({
  projectId,
  referenceCharacterId,
  referencePrimaryAssetId,
  referenceComplementaryAssetIds,
  referenceReviewer,
  referenceNotes,
  referenceStateByCharacter,
  setBusy,
  setError,
  setReferenceNotes,
  setReferenceComplementaryAssetIds,
  refresh,
  selectedBinding,
  selectedIdentityMapping,
  samePersonReviewer,
  samePersonNotes,
  samePersonComparisons,
  workbench,
  setSamePersonNotes,
}: {
  projectId?: string;
  referenceCharacterId: string;
  referencePrimaryAssetId: string;
  referenceComplementaryAssetIds: string[];
  referenceReviewer: string;
  referenceNotes: string;
  referenceStateByCharacter: Map<string, CharacterReferenceState>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string>>;
  setReferenceNotes: Dispatch<SetStateAction<string>>;
  setReferenceComplementaryAssetIds: Dispatch<SetStateAction<string[]>>;
  refresh: (signal?: AbortSignal) => Promise<void>;
  selectedBinding: ReviewedKeyframe | undefined;
  selectedIdentityMapping: unknown[];
  samePersonReviewer: string;
  samePersonNotes: string;
  samePersonComparisons: SamePersonComparison[];
  workbench: VisualWorkbench;
  setSamePersonNotes: Dispatch<SetStateAction<string>>;
}) {
  const selectCharacterReference = async () => {
    if (!projectId || !referenceCharacterId || !referencePrimaryAssetId) return;
    const state = referenceStateByCharacter.get(referenceCharacterId);
    setBusy(true);
    setError("");
    try {
      await plotloomApi.selectCharacterReference(projectId, {
        characterId: referenceCharacterId,
        authority: "story_bible",
        primaryAssetId: referencePrimaryAssetId,
        complementaryAssetIds: referenceComplementaryAssetIds,
        expectedReferenceRevision: state?.revision ?? 0,
        reviewer: referenceReviewer.trim(),
        notes: referenceNotes.trim(),
      });
      setReferenceNotes("");
      setReferenceComplementaryAssetIds([]);
      await refresh();
    } catch (referenceError) {
      setError(
        referenceError instanceof Error
          ? referenceError.message
          : "无法选择角色身份参考",
      );
    } finally {
      setBusy(false);
    }
  };
  const revokeCharacterReference = async (characterId: string) => {
    if (!projectId) return;
    const state = referenceStateByCharacter.get(characterId);
    if (!state) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.revokeCharacterReference(projectId, characterId, {
        expectedReferenceRevision: state.revision,
        reviewer: referenceReviewer.trim(),
        reason:
          "Creator revoked this identity reference before preparing further image work.",
      });
      await refresh();
    } catch (referenceError) {
      setError(
        referenceError instanceof Error
          ? referenceError.message
          : "无法撤销角色身份参考",
      );
    } finally {
      setBusy(false);
    }
  };
  const recordSamePersonReview = async () => {
    if (
      !projectId ||
      !selectedBinding ||
      !selectedIdentityMapping.length ||
      !samePersonReviewer.trim() ||
      !samePersonNotes.trim()
    )
      return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.recordSamePersonReview(projectId, {
        bindingId: selectedBinding.id,
        expectedReviewRevision: workbench.samePersonReviews.revision,
        reviewer: samePersonReviewer.trim(),
        comparisons: samePersonComparisons,
        notes: samePersonNotes.trim(),
      });
      setSamePersonNotes("");
      await refresh();
    } catch (reviewError) {
      setError(
        reviewError instanceof Error
          ? reviewError.message
          : "无法记录同一人物复核",
      );
    } finally {
      setBusy(false);
    }
  };


  return {
    selectCharacterReference,
    revokeCharacterReference,
    recordSamePersonReview,
  };
}
