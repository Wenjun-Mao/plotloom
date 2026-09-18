"""Public project-persistence contracts and schema rows."""

from .codec import stable_hash
from .project.approvals import ApprovalClosure, ApprovalDecision
from .project.repository import ProjectSQLiteRepository
from .schema import (
    ApprovalDecisionRow, ArtifactRow, ArtReferenceProposalCandidateRow, ArtReferenceProposalDeliveryRow, ArtReferenceProposalRow, AuthoringDraftRow, Base, CharacterReferenceDecisionRow,
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
    "ApprovalClosure", "ApprovalDecision", "ApprovalDecisionRow", "ArtifactRow", "ArtReferenceProposalCandidateRow", "ArtReferenceProposalDeliveryRow", "ArtReferenceProposalRow", "AuthoringDraftRow", "Base",
    "CharacterReferenceDecisionRow", "CharacterReferenceProposalCandidateRow", "CharacterReferenceProposalDeliveryRow",
    "CharacterReferenceProposalRow", "CharacterReferenceStateRow", "EntityRevisionRow", "FragmentReuseBindingRow",
    "GateResultRow", "GenerationAttemptRow", "GenerationPlanRow", "GenerationRunRow", "GenerationWorkUnitRow",
    "ImageJobCandidateRow", "ImageJobDeliveryRow", "ImageJobRow", "ManagedAssetProvenanceRow", "ManagedAssetRow",
    "MediaTaskRow", "ProductionUnitRow", "ProjectCreationIdempotencyRow", "ProjectDuplicateIdempotencyRow", "ProjectRow",
    "ProjectSQLiteRepository", "PROJECT_TEXT_PIPELINE_TABLE_NAMES", "ProviderProfileSelectionRow", "ProviderSettingsRow", "ReviewedShotBindingRow",
    "SamePersonReviewRow", "SamePersonReviewStateRow", "SealedStageAggregateRow", "StageHeadRow",
    "StagePlanRow", "StillPreviewRow", "StoryGraphTopologyRow", "TextProviderProfileRow", "VideoJobRow",
    "VideoPilotLedgerEventRow", "VideoPilotLedgerRow", "VideoReviewRow", "VisualIntentRow", "VisualSelectionStateRow",
    "WorkUnitRepairIdempotencyRow", "WorkUnitRepairScopeRow", "stable_hash",
]
