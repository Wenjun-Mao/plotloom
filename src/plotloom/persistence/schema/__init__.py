from .base import Base
from .project_authoring import (
    ApprovalDecisionRow, AuthoringDraftRow, EntityRevisionRow, GateResultRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectOperationalStateRow, ProjectRow, StageHeadRow,
)
from .project_source_outline import (
    SourceOutlineCandidateRow, SourceOutlineHeadRow, SourceOutlineRevisionRow,
    SourceOutlineGraphAdmissionRow,
    SourceOutlineSectionMapHeadRow, SourceOutlineSectionMapRevisionRow,
    SourceOutlineSourceRevisionRow,
)
from .project_cast import CastCandidateRow, CastHeadRow, CastRevisionRow
from .project_art import ArtCandidateRow, ArtHeadRow, ArtRevisionRow
from .project_script import ScriptCandidateRow, ScriptHeadRow, ScriptRevisionRow
from .project_storyboard_review import StoryboardReviewCandidateRow, StoryboardReviewHeadRow, StoryboardReviewRevisionRow
from .project_production_bridge import ProductionBridgeAdmissionRow, ProductionBridgeHeadRow, ProductionBridgeRevisionRow
from .project_generation import (
    ArtifactRow, FragmentReuseBindingRow, GenerationAttemptRow, GenerationPlanRow,
    GenerationRunRow, GenerationWorkUnitRow, MediaTaskRow, SealedStageAggregateRow, StagePlanRow,
    StoryGraphTopologyRow, RunArtifactBlobRow, WorkUnitRepairIdempotencyRow, WorkUnitRepairScopeRow,
)
from .project_media import (
    ArtReferenceDecisionRow, ArtReferenceDecisionStateRow,
    ArtReferenceProposalCandidateRow, ArtReferenceProposalDeliveryRow, ArtReferenceProposalRow,
    CharacterImportedAppearanceRow, CharacterReferenceDecisionRow, CharacterReferenceProposalCandidateRow,
    CharacterReferenceProposalDeliveryRow, CharacterReferenceProposalRow, CharacterReferenceStateRow,
    ImageJobCandidateRow, ImageJobDeliveryRow, ImageJobRow, ManagedAssetProvenanceRow, ManagedAssetRow,
    ProductionUnitRow, ReviewedShotBindingRow, SamePersonReviewRow, SamePersonReviewStateRow,
    StillPreviewRow, VideoJobRow, VideoReviewRow, VideoCandidateSelectionRow, ProjectVideoDispatchRow, VisualIntentRow, VisualSelectionStateRow,
)
from .application_control import ProviderProfileSelectionRow, ProviderSettingsRow, TextProviderProfileRow, VideoPilotLedgerEventRow, VideoPilotLedgerRow

# This intentionally names the project-owned port instead of using Base.metadata wholesale.
PROJECT_TEXT_PIPELINE_TABLE_NAMES = frozenset({
    "v2_projects", "v2_project_operational_states", "v2_entity_revisions", "v2_stage_heads", "v2_authoring_drafts",
    "v2_gate_results", "v2_generation_runs", "v2_generation_attempts", "v2_artifacts", "v2_run_artifact_blobs",
    "v2_generation_plans", "v2_generation_stage_plans", "v2_generation_work_units",
    "v2_sealed_stage_aggregates", "v2_generation_work_unit_repair_scopes",
    "v2_generation_fragment_reuse_bindings", "v2_generation_work_unit_repair_idempotency",
    "v2_generation_story_graph_topologies", "v2_media_tasks", "v2_approval_decisions",
    "v2_managed_assets", "v2_managed_asset_provenance", "v2_visual_intents",
    "v2_character_imported_appearances",
    "v2_visual_selection_states", "v2_reviewed_shot_bindings", "v2_still_previews",
    "v2_production_units", "v2_image_jobs", "v2_image_job_deliveries", "v2_image_job_candidates",
    "v2_character_reference_states", "v2_character_reference_decisions",
    "v2_character_reference_proposals", "v2_character_reference_proposal_deliveries",
    "v2_character_reference_proposal_candidates", "v2_same_person_review_states", "v2_same_person_reviews",
    "v2_art_reference_proposals", "v2_art_reference_proposal_deliveries", "v2_art_reference_proposal_candidates",
    "v2_art_reference_decision_states", "v2_art_reference_decisions",
    "v2_video_jobs", "v2_video_reviews", "v2_video_candidate_selections", "v2_project_video_dispatches",
    "v2_source_outline_heads", "v2_source_outline_source_revisions",
    "v2_source_outline_candidates", "v2_source_outline_revisions",
    "v2_source_outline_section_map_heads", "v2_source_outline_section_map_revisions",
    "v2_source_outline_graph_admissions",
    "v2_cast_heads", "v2_cast_candidates", "v2_cast_revisions",
    "v2_art_heads", "v2_art_candidates", "v2_art_revisions",
    "v2_script_heads", "v2_script_candidates", "v2_script_revisions",
    "v2_storyboard_review_heads", "v2_storyboard_review_candidates", "v2_storyboard_review_revisions",
    "v2_production_bridge_heads", "v2_production_bridge_revisions", "v2_production_bridge_admissions",
})
