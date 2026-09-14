"""Stable public persistence surface; implementation ownership is package-local."""

from .codec import stable_hash
from .project.repository import ProjectSQLiteRepository
from .schema import (
    ApprovalDecisionRow, ArtifactRow, AuthoringDraftRow, Base, CharacterReferenceDecisionRow,
    CharacterReferenceProposalCandidateRow, CharacterReferenceProposalDeliveryRow, CharacterReferenceProposalRow,
    CharacterReferenceStateRow, EntityRevisionRow, FragmentReuseBindingRow, GateResultRow, GenerationAttemptRow,
    GenerationPlanRow, GenerationRunRow, GenerationWorkUnitRow, ImageJobCandidateRow, ImageJobDeliveryRow,
    ImageJobRow, ManagedAssetProvenanceRow, ManagedAssetRow, MediaTaskRow, ProductionUnitRow,
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow, ProviderProfileSelectionRow,
    ProviderSettingsRow, ReviewedShotBindingRow, SamePersonReviewRow, SamePersonReviewStateRow,
    SealedStageAggregateRow, StageHeadRow, StagePlanRow, StillPreviewRow, StoryGraphTopologyRow,
    TextProviderProfileRow, VideoJobRow, VideoPilotLedgerEventRow, VideoPilotLedgerRow, VideoReviewRow,
    VisualIntentRow, VisualSelectionStateRow, WorkUnitRepairIdempotencyRow, WorkUnitRepairScopeRow,
)


def __getattr__(name: str):
    """Load the retained runtime facade only for callers that request it.

    Project-folder composition imports this package on its way to the direct
    project repository.  Eagerly importing the compatibility facade there
    would make an otherwise independent project home fail the retirement
    boundary simply because Python initialized its parent package.
    """

    if name in {"ApprovalClosure", "ApprovalDecision", "SQLiteRepository"}:
        from .legacy_repository import ApprovalClosure, ApprovalDecision, SQLiteRepository

        values = {
            "ApprovalClosure": ApprovalClosure,
            "ApprovalDecision": ApprovalDecision,
            "SQLiteRepository": SQLiteRepository,
        }
        globals().update(values)
        return values[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ApprovalClosure", "ApprovalDecision", "ApprovalDecisionRow", "ArtifactRow", "AuthoringDraftRow", "Base",
    "CharacterReferenceDecisionRow", "CharacterReferenceProposalCandidateRow", "CharacterReferenceProposalDeliveryRow",
    "CharacterReferenceProposalRow", "CharacterReferenceStateRow", "EntityRevisionRow", "FragmentReuseBindingRow",
    "GateResultRow", "GenerationAttemptRow", "GenerationPlanRow", "GenerationRunRow", "GenerationWorkUnitRow",
    "ImageJobCandidateRow", "ImageJobDeliveryRow", "ImageJobRow", "ManagedAssetProvenanceRow", "ManagedAssetRow",
    "MediaTaskRow", "ProductionUnitRow", "ProjectCreationIdempotencyRow", "ProjectDuplicateIdempotencyRow", "ProjectRow",
    "ProjectSQLiteRepository", "PROJECT_TEXT_PIPELINE_TABLE_NAMES", "ProviderProfileSelectionRow", "ProviderSettingsRow", "ReviewedShotBindingRow",
    "SamePersonReviewRow", "SamePersonReviewStateRow", "SealedStageAggregateRow", "SQLiteRepository", "StageHeadRow",
    "StagePlanRow", "StillPreviewRow", "StoryGraphTopologyRow", "TextProviderProfileRow", "VideoJobRow",
    "VideoPilotLedgerEventRow", "VideoPilotLedgerRow", "VideoReviewRow", "VisualIntentRow", "VisualSelectionStateRow",
    "WorkUnitRepairIdempotencyRow", "WorkUnitRepairScopeRow", "stable_hash",
]
