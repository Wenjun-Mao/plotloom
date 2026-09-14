"""Regression contract for the behavior-preserving persistence package move."""

from __future__ import annotations

import inspect

import pytest

from plotloom.persistence import (
    Base,
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    ProjectSQLiteRepository,
    SQLiteRepository,
    stable_hash,
)
from plotloom.persistence.project.approvals import ProjectApprovalPersistence
from plotloom.persistence.project.canonical import ProjectCanonicalPersistence
from plotloom.persistence.project.catalog import ProjectCatalogPersistence
from plotloom.persistence.project.drafts import ProjectDraftPersistence
from plotloom.persistence.project.gates import ProjectGatePersistence
from plotloom.persistence.project.lifecycle import ProjectLifecyclePersistence
from plotloom.exceptions import NotFoundError


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
        "v2_projects", "v2_provider_profile_selection", "v2_provider_settings",
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
