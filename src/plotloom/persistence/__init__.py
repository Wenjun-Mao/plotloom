"""Stable public persistence surface; implementation ownership is package-local."""

from .codec import stable_hash
from .legacy_repository import ApprovalClosure, ApprovalDecision, ProjectSQLiteRepository, SQLiteRepository
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
