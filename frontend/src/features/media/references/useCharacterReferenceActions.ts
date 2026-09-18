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
  proposalCharacterId,
  castRevision,
  proposalDirection,
  proposalParentCandidateAssetId,
  setProposalDirection,
  setProposalParentCandidateAssetId,
  setCopiedAssignment,
  setCopiedAssignmentStatus,
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
  proposalCharacterId: string;
  castRevision?: number;
  proposalDirection: string;
  proposalParentCandidateAssetId: string;
  setProposalDirection: Dispatch<SetStateAction<string>>;
  setProposalParentCandidateAssetId: Dispatch<SetStateAction<string>>;
  setCopiedAssignment: Dispatch<SetStateAction<string>>;
  setCopiedAssignmentStatus: Dispatch<SetStateAction<"copied" | "manual" | "">>;
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
  const prepareCharacterReferenceProposal = async () => {
    if (
      !projectId ||
      !proposalCharacterId ||
      !castRevision ||
      !proposalDirection.trim()
    )
      return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.prepareCharacterReferenceProposal(projectId, {
        characterId: proposalCharacterId,
        castRevision,
        visualDirection: proposalDirection.trim(),
        parentCandidateAssetId: proposalParentCandidateAssetId || undefined,
      });
      setProposalDirection("");
      setProposalParentCandidateAssetId("");
      await refresh();
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "无法准备角色参考 proposal",
      );
    } finally {
      setBusy(false);
    }
  };
  const copyCharacterReferenceProposal = async (proposalId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const copied = await plotloomApi.copyCharacterReferenceProposal(
        projectId,
        proposalId,
      );
      setCopiedAssignment(copied.assignment);
      setCopiedAssignmentStatus("manual");
      await refresh();
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "无法复制角色参考 assignment",
      );
    } finally {
      setBusy(false);
    }
  };
  const refreshCharacterReferenceProposal = async (proposalId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.refreshCharacterReferenceProposal(
        projectId,
        proposalId,
      );
      await refresh();
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "无法检查角色参考 delivery",
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
    prepareCharacterReferenceProposal,
    copyCharacterReferenceProposal,
    refreshCharacterReferenceProposal,
    recordSamePersonReview,
  };
}
