"""Regression contract for the behavior-preserving persistence package move."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from plotloom.persistence import (
    Base,
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    ProjectSQLiteRepository,
    SQLiteRepository,
    VideoPilotLedgerEventRow,
    VideoPilotLedgerRow,
    stable_hash,
)
from plotloom.persistence.project.approvals import ProjectApprovalPersistence
from plotloom.persistence.project.canonical import ProjectCanonicalPersistence
from plotloom.persistence.project.catalog import ProjectCatalogPersistence
from plotloom.persistence.project.drafts import ProjectDraftPersistence
from plotloom.persistence.project.gates import ProjectGatePersistence
from plotloom.persistence.project.lifecycle import ProjectLifecyclePersistence
from plotloom.persistence.project.generation_aggregates import ProjectGenerationAggregatePersistence
from plotloom.persistence.project.generation_attempts import ProjectGenerationAttemptPersistence
from plotloom.persistence.project.generation_evidence import ProjectGenerationEvidencePersistence
from plotloom.persistence.project.generation_lifecycle import ProjectGenerationLifecyclePersistence
from plotloom.persistence.project.generation_plans import ProjectGenerationPlanningPersistence
from plotloom.persistence.project.generation_progress import ProjectGenerationProgressPersistence
from plotloom.persistence.project.generation_recovery import ProjectGenerationRecoveryPersistence
from plotloom.persistence.project.generation_repairs import ProjectGenerationRepairPersistence
from plotloom.persistence.project.generation_reuse import ProjectGenerationReusePersistence
from plotloom.persistence.project.generation_snapshots import ProjectGenerationSnapshots
from plotloom.persistence.project.generation_access import GenerationPersistenceAccess
from plotloom.persistence.project.media import ProjectMediaPersistence
from plotloom.persistence.project.media_admission import KeyframeAdmission
from plotloom.persistence.project.media_assets import ManagedAssetPersistence
from plotloom.persistence.project.media_character_references import CharacterReferencePersistence
from plotloom.persistence.project.media_image_currentness import ImageJobCurrentness
from plotloom.persistence.project.media_image_delivery import ImageJobDeliveryPersistence
from plotloom.persistence.project.media_image_preparation import ImageJobPreparationPersistence
from plotloom.persistence.project.media_keyframes import ReviewedKeyframePersistence
from plotloom.persistence.project.media_reference_proposals import CharacterReferenceProposalPersistence
from plotloom.persistence.project.media_same_person_reviews import SamePersonReviewPersistence
from plotloom.persistence.project.media_tasks import GenericMediaTaskPersistence
from plotloom.persistence.project.media_video import VideoJobPersistence
from plotloom.persistence.project.media_video_currentness import VideoJobCurrentness
from plotloom.persistence.project.media_visual_intents import VisualIntentPersistence
from plotloom.persistence.application.profiles import ApplicationProfilePersistence
from plotloom.persistence.application.profile_admission import TextProviderProfileAdmissionPersistence
from plotloom.persistence.application.profile_bootstrap import DefaultProfileBootstrapPersistence
from plotloom.persistence.application.profile_catalog import TextProviderProfileCatalogPersistence
from plotloom.persistence.application.profile_settings import ProviderSettingsPersistence
from plotloom.persistence.application.accounting import VideoPilotAccounting
from plotloom.exceptions import NotFoundError
from plotloom.domain import utc_now


BASELINE_TABLE_NAMES = frozenset(
    {
        "v2_approval_decisions", "v2_artifacts", "v2_authoring_drafts",
        "v2_character_reference_decisions", "v2_character_reference_proposal_candidates",
        "v2_character_reference_proposal_deliveries", "v2_character_reference_proposals",
        "v2_character_reference_states", "v2_entity_revisions", "v2_gate_results",
        "v2_generation_attempts", "v2_generation_fragment_reuse_bindings", "v2_generation_plans",
        "v2_generation_runs", "v2_generation_stage_plans", "v2_generation_story_graph_topologies",
        "v2_generation_work_unit_repair_idempotency", "v2_generation_work_unit_repair_scopes",
        "v2_generation_work_units", "v2_image_job_candidates", "v2_image_job_deliveries",
        "v2_image_jobs", "v2_managed_asset_provenance", "v2_managed_assets", "v2_media_tasks",
        "v2_production_units", "v2_project_creation_idempotency", "v2_project_duplicate_idempotency",
        "v2_projects", "v2_project_operational_states", "v2_provider_profile_selection", "v2_provider_settings",
        "v2_reviewed_shot_bindings", "v2_same_person_review_states", "v2_same_person_reviews",
        "v2_sealed_stage_aggregates", "v2_stage_heads", "v2_still_previews",
        "v2_text_provider_profiles", "v2_video_jobs", "v2_video_pilot_ledger",
        "v2_video_pilot_ledger_events", "v2_video_reviews", "v2_visual_intents",
        "v2_visual_selection_states",
    }
)


def test_persistence_package_preserves_baseline_metadata_imports_and_table_scope() -> None:
    assert set(Base.metadata.tables) == BASELINE_TABLE_NAMES
    assert PROJECT_TEXT_PIPELINE_TABLE_NAMES < BASELINE_TABLE_NAMES
    project_repository = ProjectSQLiteRepository("sqlite://", project_id="contract")
    try:
        assert set(project_repository._schema_tables()) == {
            Base.metadata.tables[name] for name in PROJECT_TEXT_PIPELINE_TABLE_NAMES
        }
    finally:
        project_repository.close()
    assert stable_hash({"alpha": [1, 2], "beta": "值"}) == (
        "d1c816b248d363468d360dd1235bd833410aca740fad1a2f6e96ee1643c20bf0"
    )


def test_persistence_package_preserves_repository_signatures_and_named_leases() -> None:
    assert tuple(inspect.signature(SQLiteRepository).parameters) == (
        "database_url", "create_schema", "sqlite_busy_timeout_ms", "schema_scope"
    )
    assert tuple(inspect.signature(ProjectSQLiteRepository).parameters) == (
        "database_url", "project_id", "create_schema", "sqlite_busy_timeout_ms"
    )
    for name in ("_read", "_write", "_bootstrap_write", "_lifecycle_write", "_work_unit_claim_write"):
        assert hasattr(SQLiteRepository, name)


def test_project_authoring_and_lifecycle_use_explicit_capability_composition() -> None:
    """Keep the retained facade compatible while capability bodies stay moved."""

    repository = SQLiteRepository("sqlite://")
    try:
        assert isinstance(repository._catalog, ProjectCatalogPersistence)
        assert isinstance(repository._lifecycle, ProjectLifecyclePersistence)
        assert isinstance(repository._drafts, ProjectDraftPersistence)
        assert isinstance(repository._gates, ProjectGatePersistence)
        assert isinstance(repository._approvals, ProjectApprovalPersistence)
        assert isinstance(repository._canonical, ProjectCanonicalPersistence)
        assert "self._catalog.create_project" in inspect.getsource(SQLiteRepository.create_project)
        assert "self._lifecycle.archive_project" in inspect.getsource(SQLiteRepository.archive_project)
        assert "self._drafts.upsert_authoring_draft" in inspect.getsource(
            SQLiteRepository.upsert_authoring_draft
        )
        assert "self._workflow.update_stage_consuming_authoring_draft" in inspect.getsource(
            SQLiteRepository.update_stage_consuming_authoring_draft
        )
    finally:
        repository.close()


def test_moved_facade_signatures_and_project_bound_identity_remain_stable() -> None:
    expected_parameters = {
        "create_project": ("self", "brief", "initial_stages", "idempotency_key"),
        "duplicate_project": ("self", "project_id", "expected_lifecycle_revision", "title", "idempotency_key"),
        "archive_project": ("self", "project_id", "expected_lifecycle_revision"),
        "update_project_consuming_authoring_draft": (
            "self", "project_id", "expected_revision", "brief", "entity_id", "expected_draft_revision",
        ),
        "upsert_authoring_draft": (
            "self", "project_id", "editor_scope", "entity_id", "base_canonical_revision",
            "expected_draft_revision", "payload",
        ),
        "update_stage_consuming_authoring_draft": (
            "self", "project_id", "stage", "expected_revision", "payload", "entity_id",
            "expected_draft_revision",
        ),
    }
    for method_name, parameter_names in expected_parameters.items():
        assert tuple(inspect.signature(getattr(SQLiteRepository, method_name)).parameters) == parameter_names

    project_repository = ProjectSQLiteRepository("sqlite://", project_id="bound")
    try:
        with pytest.raises(NotFoundError, match="does not belong"):
            project_repository.get_project("other")
    finally:
        project_repository.close()


def test_generation_capabilities_are_explicitly_composed_with_preserved_facade_signatures() -> None:
    """Generation contracts stay typed capability calls, not dynamic forwarding."""

    repository = SQLiteRepository("sqlite://")
    try:
        capabilities = (
            ("_generation_snapshots", ProjectGenerationSnapshots, ("capture_snapshot", "create_run")),
            ("_generation_plans", ProjectGenerationPlanningPersistence, ("get_or_create_stage_plan",)),
            ("_generation_attempts", ProjectGenerationAttemptPersistence, ("allocate_attempt_for_work_unit", "persist_attempt_response")),
            ("_generation_reuse", ProjectGenerationReusePersistence, ("prepare_repair_stage_reuse",)),
            ("_generation_aggregates", ProjectGenerationAggregatePersistence, ("seal_stage_aggregate", "seal_repair_stage_aggregate")),
            ("_generation_progress", ProjectGenerationProgressPersistence, ("get_run_execution_trace", "get_run_progress")),
            ("_generation_repairs", ProjectGenerationRepairPersistence, ("create_work_unit_repair_run",)),
            ("_generation_recovery", ProjectGenerationRecoveryPersistence, ("reconcile_startup_jobs",)),
            ("_generation_lifecycle", ProjectGenerationLifecyclePersistence, ("commit_sealed_run", "cancel_run")),
            ("_generation_evidence", ProjectGenerationEvidencePersistence, ("add_artifact", "get_run_trace")),
        )
        for attribute, capability_type, methods in capabilities:
            assert isinstance(getattr(repository, attribute), capability_type)
            for method in methods:
                assert f"self.{attribute}.{method}" in inspect.getsource(
                    getattr(SQLiteRepository, method)
                )
        assert not hasattr(SQLiteRepository, "__getattr__")
    finally:
        repository.close()


def test_generation_policy_is_absent_from_the_retained_facade_and_owners_do_not_bounce_back() -> None:
    """Keep generation rules out of compatibility composition after extraction."""

    policy_names = {
        "_validate_repair_scope_in_session",
        "_repair_stage_dependencies_in_session",
        "_validate_frozen_reuse_source_in_session",
        "_required_unit_evidence_in_session",
        "_required_repair_unit_evidence_in_session",
        "_obsolete_generation_planning_policy_recovery_code_in_session",
        "_exact_repair_parent_contract_code_in_session",
        "_work_unit_repair_eligibility_in_session",
        "_commit_run_outputs",
        "_commit_parsed_run_outputs_in_session",
    }
    assert not policy_names.intersection(vars(SQLiteRepository))
    assert "facade" not in GenerationPersistenceAccess.__dataclass_fields__

    owners = Path(__file__).parents[2] / "src" / "plotloom" / "persistence" / "project"
    generation_sources = "\n".join(
        path.read_text()
        for path in owners.glob("generation_*.py")
        if path.name != "generation_access.py"
    )
    assert "access.facade" not in generation_sources
    assert "repository._" not in generation_sources


def test_media_and_application_control_are_explicit_owners_without_facade_bouncebacks() -> None:
    """Project facts, application control, and accounting retain separate roots."""

    repository = SQLiteRepository("sqlite://")
    try:
        assert isinstance(repository._media, ProjectMediaPersistence)
        assert isinstance(repository._application_profiles, ApplicationProfilePersistence)
        assert isinstance(repository._video_accounting, VideoPilotAccounting)
        assert "self._media.image_preparation.prepare_image_job" in inspect.getsource(
            SQLiteRepository.prepare_image_job
        )
        assert "self._application_profiles.create_text_provider_profile" in inspect.getsource(
            SQLiteRepository.create_text_provider_profile
        )
    finally:
        repository.close()

    owners = Path(__file__).parents[2] / "src" / "plotloom" / "persistence"
    authoring_sources = "\n".join(
        (owners / "project" / name).read_text()
        for name in ("catalog.py", "lifecycle.py", "drafts.py", "gates.py", "approvals.py", "canonical.py", "workflow.py")
    )
    media_source = (owners / "project" / "media.py").read_text()
    application_sources = "\n".join(
        path.read_text() for path in (owners / "application").glob("*.py")
    )
    assert "self._repository" not in authoring_sources
    assert "legacy_repository" not in authoring_sources
    assert "legacy_repository" not in media_source
    assert "legacy_repository" not in application_sources
    assert "VideoPilotLedger" not in media_source


def test_media_and_control_submodules_keep_currentness_and_projection_boundaries() -> None:
    """Prevent a new policy monolith or facade back-reference from returning."""

    repository = SQLiteRepository("sqlite://")
    try:
        media = repository._media
        assert isinstance(media.admission, KeyframeAdmission)
        assert isinstance(media.assets, ManagedAssetPersistence)
        assert isinstance(media.intents, VisualIntentPersistence)
        assert isinstance(media.keyframes, ReviewedKeyframePersistence)
        assert isinstance(media.references, CharacterReferencePersistence)
        assert isinstance(media.proposals, CharacterReferenceProposalPersistence)
        assert isinstance(media.same_person, SamePersonReviewPersistence)
        assert isinstance(media.image_currentness, ImageJobCurrentness)
        assert isinstance(media.image_preparation, ImageJobPreparationPersistence)
        assert isinstance(media.image_delivery, ImageJobDeliveryPersistence)
        assert isinstance(media.video_currentness, VideoJobCurrentness)
        assert isinstance(media.video, VideoJobPersistence)
        assert isinstance(media.tasks, GenericMediaTaskPersistence)
        assert "_approval_is_active_in_session" not in vars(ReviewedKeyframePersistence)
        assert "_selection_state_in_session" not in vars(ReviewedKeyframePersistence)
        assert "self._media.admission.list_current_reviewed_keyframes" in inspect.getsource(
            SQLiteRepository.list_current_reviewed_keyframes
        )

        profiles = repository._application_profiles
        assert isinstance(profiles._bootstrap, DefaultProfileBootstrapPersistence)
        assert isinstance(profiles._catalog, TextProviderProfileCatalogPersistence)
        assert isinstance(profiles._admission, TextProviderProfileAdmissionPersistence)
        assert isinstance(profiles._settings, ProviderSettingsPersistence)
    finally:
        repository.close()

    owners = Path(__file__).parents[2] / "src" / "plotloom" / "persistence"
    owner_paths = [
        owners / "project" / "media.py",
        owners / "application" / "profiles.py",
        *sorted((owners / "project").glob("media_*.py")),
        *sorted((owners / "application").glob("profile_*.py")),
    ]
    assert owner_paths
    for path in owner_paths:
        source = path.read_text()
        assert len(source.splitlines()) < 400, path.name
        assert "legacy_repository" not in source
        assert "self._repository" not in source
        assert "__getattr__" not in source


def test_extracted_pilot_accounting_reuses_the_historical_durable_ledger_identity() -> None:
    """A capability move must not make existing shared reservations invisible."""

    repository = SQLiteRepository("sqlite://")
    try:
        now = utc_now()
        with repository._write() as session:  # noqa: SLF001 - persisted compatibility fixture
            session.add(VideoPilotLedgerRow(
                id="wan-3.0-pilot-100-requested-seconds", limit_seconds=100,
                reserved_seconds=10, created_at=now, updated_at=now,
            ))
            session.flush()
            session.add(VideoPilotLedgerEventRow(
                id="historical-reservation", ledger_id="wan-3.0-pilot-100-requested-seconds",
                video_job_id="historical-job", event="reserved", seconds=10, created_at=now,
            ))
        assert repository.video_budget() == {
            "limitSeconds": 100,
            "reservedSeconds": 10,
            "remainingSeconds": 90,
            "attempts": [{
                "videoJobId": "historical-job", "event": "reserved", "seconds": 10,
                "createdAt": now.isoformat(),
            }],
        }
    finally:
        repository.close()
