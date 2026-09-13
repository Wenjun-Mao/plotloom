from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

import pytest
from pydantic import ValidationError

from tests.test_alpha_acceptance import _FixtureResolver, _profile

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import RunKind, RunStatus, STAGE_ORDER
from plotloom.generation.contracts import ProviderResponse, ProviderUsage
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import (
    OwnedArtifact,
    PROJECT_STORAGE_FORMAT_VERSION,
    ProjectFolderStorage,
    ProjectStorageConflictError,
    ProjectStorageConfinementError,
    ProjectStorageError,
)
from plotloom.provider_profiles import TextProviderProfileSnapshotV3


def _fixture_profile(*, max_semantic_corrections: int = 2) -> TextProviderProfileSnapshotV3:
    values = _profile("offline_fixture").model_dump(mode="json", by_alias=True)
    values.update(
        profileSchemaVersion=3,
        adapterId="openai_compatible",
        adapterVersion="1",
        maxSemanticCorrections=max_semantic_corrections,
        presetId="custom" if max_semantic_corrections == 0 else "compatible_v1",
        profileHash="",
    )
    return TextProviderProfileSnapshotV3.model_validate(values)


class _RejectFinalStoryboardProvider:
    """Existing fixture behavior with one known rejected final work unit."""

    def __init__(self) -> None:
        self.delegate = _FixtureResolver().provider
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.storyboard_requests = 0
        self.rejected = False

    def generate(self, request, secret) -> ProviderResponse:
        prompt = "\n".join(message.content for message in request.messages)
        if "【目标戏剧场景】" in prompt:
            self.storyboard_requests += 1
            # The fixed workload has nine storyboard units. Rejecting the last
            # one leaves all exact upstream/sibling evidence available to the
            # existing exact-repair contract.
            if self.storyboard_requests == 9 and not self.rejected:
                self.rejected = True
                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                    usage=ProviderUsage(input_tokens=1, output_tokens=1),
                )
        return self.delegate.generate(request, secret)


class _RejectFinalStoryboardResolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalStoryboardProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _RejectFirstProvider:
    """A failed repair source used to prove no partial project installation."""

    def __init__(self) -> None:
        self.delegate = _FixtureResolver().provider
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.rejected = False

    def generate(self, request, secret) -> ProviderResponse:
        if not self.rejected:
            self.rejected = True
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                usage=ProviderUsage(input_tokens=1, output_tokens=1),
            )
        return self.delegate.generate(request, secret)


class _RejectFirstResolver:
    def __init__(self) -> None:
        self.provider = _RejectFirstProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def _table_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def test_two_project_homes_run_actual_four_stage_pipeline_and_reopen_by_project_id(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    profile = _fixture_profile()
    saved_profile = storage.application.save_text_profile(profile, expected_revision=0)
    assert storage.application.select_profile(saved_profile.profile_id) == saved_profile

    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    second = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": "第二个雾港"}))
    first_run = storage.execute_selected_text_pipeline(
        first.project().id,
        provider_resolver=_FixtureResolver(),
    )
    second_run = storage.execute_selected_text_pipeline(
        second.project().id,
        provider_resolver=_FixtureResolver(),
    )

    # The new stores neither read nor need the former shared project database.
    old_shared_database = tmp_path / "retained-pilot" / "plotloom.sqlite3"
    old_shared_database.parent.mkdir()
    old_shared_database.write_bytes(b"not a project store")
    old_shared_database.unlink()

    reopened = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    reopened_first = reopened.projects.open(first.project().id)
    reopened_second = reopened.projects.open(second.project().id)

    assert first_run.status == RunStatus.SUCCEEDED
    assert second_run.status == RunStatus.SUCCEEDED
    assert [item.head.stage for item in reopened_first.canonical_stages()] == list(STAGE_ORDER)
    assert [item.head.stage for item in reopened_second.canonical_stages()] == list(STAGE_ORDER)
    assert [item.id for item in reopened_first.generation_runs()] == [first_run.id]
    assert [item.id for item in reopened_second.generation_runs()] == [second_run.id]
    assert reopened_first.run_trace(first_run.id).run.project_id == reopened_first.project().id
    assert reopened_second.run_trace(second_run.id).run.project_id == reopened_second.project().id
    assert [seal.stage for seal in reopened_first.run_execution_trace(first_run.id).sealed_aggregates] == list(STAGE_ORDER)
    assert [seal.stage for seal in reopened_second.run_execution_trace(second_run.id).sealed_aggregates] == list(STAGE_ORDER)
    assert reopened_first.generation_runs()[0].provider_snapshot == profile.model_dump(
        mode="json", by_alias=True
    )
    assert reopened_first.generation_runs()[0].provider_snapshot["adapterVersion"] == "1"
    assert first.home != second.home
    assert {home.manifest.project_id for home in reopened.projects.discover()} == {
        first.project().id,
        second.project().id,
    }

    project_tables = _table_names(first.home / "project.sqlite3")
    application_tables = _table_names(tmp_path / "application" / "application.sqlite3")
    assert {
        "project_state",
        "canonical_entity_revisions",
        "canonical_stage_heads",
        "generation_run_evidence",
        "generation_attempt_evidence",
        "generation_work_unit_evidence",
        "sealed_stage_aggregate_evidence",
    }.issubset(project_tables)
    assert "application_profiles" not in project_tables
    assert {"application_profiles", "application_preferences", "global_accounting"}.issubset(
        application_tables
    )
    assert "canonical_stage_heads" not in application_tables


def test_exact_repair_lineage_is_project_owned_and_reopenable(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    completed = ProjectPipelineExecutor(_RejectFinalStoryboardResolver()).execute(
        project,
        profile=_fixture_profile(max_semantic_corrections=0),
        exact_repair=True,
    )

    runs = project.generation_runs()
    parent, child = runs
    assert completed.id == child.id
    assert parent.kind == RunKind.PIPELINE
    assert parent.status == RunStatus.QUARANTINED
    assert child.kind == RunKind.REPAIR
    assert child.status == RunStatus.SUCCEEDED
    assert child.parent_run_id == parent.id
    scope = project.repair_scope(child.id)
    assert scope.child_run_id == child.id
    assert scope.parent_run_id == parent.id
    assert project.fragment_reuse_bindings(child.id)
    assert [seal.stage for seal in project.run_execution_trace(child.id).sealed_aggregates] == list(
        STAGE_ORDER
    )

    reopened = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    ).projects.open(project.project().id)
    assert [run.id for run in reopened.generation_runs()] == [parent.id, child.id]
    assert reopened.repair_scope(child.id) == scope
    assert [item.head.stage for item in reopened.canonical_stages()] == list(STAGE_ORDER)


def test_stale_or_failed_repair_evidence_cannot_partially_install(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    stale_project = storage.projects.create(FIXED_CHINESE_BRIEF)
    evidence = ProjectPipelineExecutor(_FixtureResolver()).collect(
        stale_project,
        profile=_fixture_profile(),
    )
    stale_project.update_brief(
        FIXED_CHINESE_BRIEF.model_copy(update={"title": "编辑后的雾港"}),
        expected_revision=1,
    )
    with pytest.raises(ProjectStorageConflictError, match="stale"):
        stale_project.install_generation_evidence(evidence)
    assert stale_project.canonical_stages() == []
    assert stale_project.generation_runs() == []

    failed_project = storage.projects.create(FIXED_CHINESE_BRIEF)
    with pytest.raises(ProjectStorageError, match="pipeline result is failed"):
        ProjectPipelineExecutor(_RejectFirstResolver()).collect(
            failed_project,
            profile=_fixture_profile(max_semantic_corrections=0),
            exact_repair=True,
        )
    assert failed_project.canonical_stages() == []
    assert failed_project.generation_runs() == []


def test_project_storage_confines_artifacts_and_rejects_secret_profile_configuration(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    artifact = project._artifacts.put(b"confined bytes", media_type="application/octet-stream")

    with pytest.raises(ProjectStorageConfinementError):
        OwnedArtifact(
            content_hash=artifact.content_hash,
            relative_path="../outside.bin",
            media_type="application/octet-stream",
            size_bytes=artifact.size_bytes,
        )
    with pytest.raises(ValidationError, match="credentials"):
        storage.application.save_profile(
            "unsafe",
            {"baseUrl": "https://example.test", "apiKey": "sk-not-for-storage"},
            expected_revision=0,
        )

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / artifact.content_hash).write_bytes(project.read_artifact(artifact))
    hash_directory = project.home / "assets" / artifact.content_hash[:2]
    (hash_directory / artifact.content_hash).unlink()
    hash_directory.rmdir()
    hash_directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProjectStorageConfinementError, match="symlink"):
        project.read_artifact(artifact)


def test_project_storage_rejects_cross_project_links_and_hidden_operational_homes(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    artifact = first._artifacts.put(b"owned by first", media_type="application/octet-stream")
    second = storage.projects.create(FIXED_CHINESE_BRIEF)
    target = second.home / artifact.relative_path
    target.parent.mkdir(parents=True)
    os.link(first.home / artifact.relative_path, target)
    with pytest.raises(ProjectStorageConfinementError, match="hard linked"):
        second.read_artifact(artifact)

    with pytest.raises(ProjectStorageConfinementError, match="non-overlapping"):
        ProjectFolderStorage(
            outputs_root=tmp_path / "one-root",
            application_data_root=tmp_path / "one-root",
        )

    snapshots = storage.projects.outputs_root / ".snapshots" / "ignored"
    snapshots.mkdir(parents=True)
    (snapshots / "project.json").write_text(
        json.dumps(
            {
                "formatVersion": PROJECT_STORAGE_FORMAT_VERSION,
                "projectId": "not-a-live-project",
                "createdAt": "2026-09-13T00:00:00Z",
                "databasePath": "project.sqlite3",
            }
        ),
        encoding="utf-8",
    )
    assert {home.manifest.project_id for home in storage.projects.discover()} == {
        first.project().id,
        second.project().id,
    }
