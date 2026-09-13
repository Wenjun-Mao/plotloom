from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.test_alpha_acceptance import _FixtureResolver, _profile

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.api import create_project_folder_authoring_app
from plotloom.domain import Artifact, ArtifactKind, RunKind, RunStatus, STAGE_ORDER, WorkUnitStatus
from plotloom.exceptions import InvalidTransitionError, NotFoundError, RepairEligibilityError
from plotloom.generation.contracts import ProviderResponse, ProviderUsage
from plotloom.pipeline import RunSecretBroker
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
from plotloom.persistence import stable_hash


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


class _FailingProvider:
    """A deterministic provider failure that must remain in the project trace."""

    name = "failing-fixture"
    capabilities = _FixtureResolver().provider.capabilities

    def generate(self, request, secret) -> ProviderResponse:
        raise RuntimeError("fixture provider failed before a response")


class _FailingResolver:
    def __init__(self) -> None:
        self.provider = _FailingProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _InterruptingProvider:
    """Leaves a committed dispatch marker without a provider result."""

    name = "interrupting-fixture"
    capabilities = _FixtureResolver().provider.capabilities

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request, secret) -> ProviderResponse:
        self.calls += 1
        raise KeyboardInterrupt("fixture process interruption after dispatch")


class _InterruptingResolver:
    def __init__(self) -> None:
        self.provider = _InterruptingProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _BearerRecordingProvider:
    def __init__(self) -> None:
        self.delegate = _FixtureResolver().provider
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.observed_secrets: list[str] = []

    def generate(self, request, secret) -> ProviderResponse:
        assert secret is not None
        with secret.reveal() as value:
            self.observed_secrets.append(value)
        # The deterministic fixture is intentionally a no-auth provider; this
        # wrapper proves the broker lease reached the adapter boundary first.
        return self.delegate.generate(request, None)


class _BearerRecordingResolver:
    def __init__(self) -> None:
        self.provider = _BearerRecordingProvider()

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
        "v2_projects",
        "v2_entity_revisions",
        "v2_stage_heads",
        "v2_generation_runs",
        "v2_generation_attempts",
        "v2_generation_work_units",
        "v2_sealed_stage_aggregates",
    }.issubset(project_tables)
    assert {
        "v2_provider_settings",
        "v2_text_provider_profiles",
        "v2_provider_profile_selection",
        "v2_video_pilot_ledger",
        "v2_video_pilot_ledger_events",
    }.isdisjoint(project_tables)
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


def test_stale_exact_repair_and_foreign_project_routes_are_rejected(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    second = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": "第二个雾港"}))
    parent = ProjectPipelineExecutor(_RejectFinalStoryboardResolver()).execute(
        first,
        profile=_fixture_profile(max_semantic_corrections=0),
    )
    assert parent.status == RunStatus.QUARANTINED
    target = next(
        item
        for item in first.repository.list_generation_work_units(parent.id)
        if item.status == WorkUnitStatus.QUARANTINED
    )
    first.update_brief(
        FIXED_CHINESE_BRIEF.model_copy(update={"title": "已编辑的雾港"}),
        expected_revision=1,
    )
    with pytest.raises(RepairEligibilityError, match="repair"):
        with first.repository.admit_provider_snapshot(
            _fixture_profile(max_semantic_corrections=0).model_dump(mode="json", by_alias=True)
        ):
            first.repository.create_work_unit_repair_run(
                parent.id,
                target.id,
                idempotency_key="stale-project-repair",
            )
    with pytest.raises(NotFoundError, match="does not belong"):
        with first.repository.admit_provider_snapshot(
            _fixture_profile().model_dump(mode="json", by_alias=True)
        ):
            first.repository.create_run(
                second.project().id,
                RunKind.PIPELINE,
                STAGE_ORDER,
                provider_snapshot=_fixture_profile().model_dump(mode="json", by_alias=True),
            )


def test_profile_bound_bearer_and_none_modes_do_not_leak_or_persist_secret_artifacts(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    bearer_values = _fixture_profile().model_dump(mode="json", by_alias=True)
    bearer_values["textAuthMode"] = "bearer"
    bearer_values["profileHash"] = ""
    bearer_profile = TextProviderProfileSnapshotV3.model_validate(bearer_values)
    resolver = _BearerRecordingResolver()
    secret = "project-storage-bearer-secret"
    broker = RunSecretBroker(server_profile_keys={bearer_profile.profile_id: secret})
    try:
        completed = ProjectPipelineExecutor(resolver).execute(
            project,
            profile=bearer_profile,
            secret_broker=broker,
        )
    finally:
        broker.close()

    assert completed.status == RunStatus.SUCCEEDED
    assert resolver.provider.observed_secrets
    assert secret not in project.run_trace(completed.id).model_dump_json()
    assert secret.encode("utf-8") not in (project.home / "project.sqlite3").read_bytes()
    with pytest.raises(InvalidTransitionError, match="secret-shaped"):
        project.repository.add_artifact(
            Artifact(
                run_id=completed.id,
                kind=ArtifactKind.PROMPT,
                content={"unexpected": "sk-project-storage-leak"},
                content_hash=stable_hash({"unexpected": "sk-project-storage-leak"}),
            )
        )
    with pytest.raises(InvalidTransitionError, match="secret-shaped"):
        project.repository.add_artifact(
            Artifact(
                run_id=completed.id,
                kind=ArtifactKind.PROMPT,
                content={"apiKey": "not-an-allowed-evidence-value"},
                content_hash=stable_hash({"apiKey": "not-an-allowed-evidence-value"}),
            )
        )


def test_terminal_evidence_is_project_owned_without_partial_canonical_heads(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    failed_project = storage.projects.create(FIXED_CHINESE_BRIEF)
    failed = ProjectPipelineExecutor(_FailingResolver()).execute(
        failed_project,
        profile=_fixture_profile(),
    )
    quarantined_project = storage.projects.create(FIXED_CHINESE_BRIEF)
    quarantined = ProjectPipelineExecutor(_RejectFirstResolver()).execute(
        quarantined_project,
        profile=_fixture_profile(max_semantic_corrections=0),
    )
    cancelled_project = storage.projects.create(FIXED_CHINESE_BRIEF)
    with cancelled_project.repository.admit_provider_snapshot(
        _fixture_profile().model_dump(mode="json", by_alias=True)
    ):
        queued = cancelled_project.repository.create_run(
            cancelled_project.project().id,
            RunKind.PIPELINE,
            STAGE_ORDER,
            provider_snapshot=_fixture_profile().model_dump(mode="json", by_alias=True),
        )
    cancelled = cancelled_project.repository.cancel_run(queued.id)

    assert failed.status == RunStatus.FAILED
    assert quarantined.status == RunStatus.QUARANTINED
    assert cancelled.status == RunStatus.CANCELLED
    assert failed_project.run_trace(failed.id).attempts
    assert quarantined_project.run_execution_trace(quarantined.id).work_units
    assert cancelled_project.run_trace(cancelled.id).run.status == RunStatus.CANCELLED
    assert failed_project.canonical_stages() == []
    assert quarantined_project.canonical_stages() == []
    assert cancelled_project.canonical_stages() == []
    assert [run.id for run in failed_project.generation_runs()] == [failed.id]
    assert [run.id for run in quarantined_project.generation_runs()] == [quarantined.id]


def test_interrupted_dispatch_reopens_as_outcome_unknown_without_replay(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    resolver = _InterruptingResolver()

    with pytest.raises(KeyboardInterrupt):
        ProjectPipelineExecutor(resolver).execute(project, profile=_fixture_profile())

    interrupted = project.generation_runs()[0]
    assert interrupted.status == RunStatus.RUNNING
    assert resolver.provider.calls == 1

    reopened = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    ).projects.open(project.project().id)
    recovery = reopened.repository.reconcile_startup_jobs()
    trace = reopened.run_trace(interrupted.id)

    assert recovery.resubmit_run_ids == []
    assert resolver.provider.calls == 1
    assert any(attempt.outcome_unknown for attempt in trace.attempts)
    assert trace.run.status == RunStatus.FAILED
    assert reopened.canonical_stages() == []


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


def test_project_folder_authoring_api_persists_isolated_cas_drafts_and_exact_save_receipts(
    tmp_path: Path,
) -> None:
    """The 2B factory must use project.sqlite3, never a shared projection."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    client = TestClient(create_project_folder_authoring_app(storage))
    first = client.post(
        "/api/v2/projects",
        json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
    )
    second = client.post(
        "/api/v2/projects",
        json={
            "brief": FIXED_CHINESE_BRIEF.model_copy(update={"title": "第二个草稿项目"}).model_dump(
                mode="json", by_alias=True
            )
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    draft_brief = FIXED_CHINESE_BRIEF.model_copy(update={"title": "仅服务器草稿"})
    saved = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "brief",
            "entityId": "root",
            "baseCanonicalRevision": 1,
            "expectedDraftRevision": 0,
            "payload": draft_brief.model_dump(mode="json", by_alias=True),
        },
    )
    assert saved.status_code == 200
    assert saved.json()["draftRevision"] == 1
    assert client.get(f"/api/v2/projects/{second_id}/authoring-drafts").json() == []

    # A second tab cannot replace a server-acknowledged buffer using the old
    # draft CAS revision.  Its losing content remains a browser concern.
    stale = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "brief",
            "entityId": "root",
            "baseCanonicalRevision": 1,
            "expectedDraftRevision": 0,
            "payload": FIXED_CHINESE_BRIEF.model_copy(update={"title": "失去的标签页"}).model_dump(
                mode="json", by_alias=True
            ),
        },
    )
    assert stale.status_code == 409
    assert client.get(f"/api/v2/projects/{first_id}/authoring-drafts").json()[0]["payload"]["title"] == "仅服务器草稿"

    # Explicit canonical Save is the only operation that changes canonical
    # content. It must consume the exact payload and base revision that its
    # receipt acknowledges; a matching revision alone cannot delete a draft.
    mismatched = client.patch(
        f"/api/v2/projects/{first_id}",
        json={
            "expectedRevision": 1,
            "brief": FIXED_CHINESE_BRIEF.model_copy(update={"title": "不是已确认的草稿"}).model_dump(
                mode="json", by_alias=True
            ),
            "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1},
        },
    )
    assert mismatched.status_code == 409
    assert client.get(f"/api/v2/projects/{first_id}").json()["brief"]["title"] == FIXED_CHINESE_BRIEF.title
    assert client.get(f"/api/v2/projects/{first_id}/authoring-drafts").json()[0]["payload"]["title"] == "仅服务器草稿"

    # The matching canonical content consumes that exact draft receipt.
    committed = client.patch(
        f"/api/v2/projects/{first_id}",
        json={
            "expectedRevision": 1,
            "brief": draft_brief.model_dump(mode="json", by_alias=True),
            "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1},
        },
    )
    assert committed.status_code == 200
    assert committed.json()["brief"]["title"] == "仅服务器草稿"
    assert committed.headers["X-Plotloom-Draft-Consumed-Revision"] == "1"
    assert client.get(f"/api/v2/projects/{first_id}/authoring-drafts").json() == []

    # Reopening a process sees only the durable project-local SQLite draft.
    reopened_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    reopened_client = TestClient(create_project_folder_authoring_app(reopened_storage))
    reopened_draft = reopened_client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "brief",
            "entityId": "root",
            "baseCanonicalRevision": 2,
            "expectedDraftRevision": 0,
            "payload": FIXED_CHINESE_BRIEF.model_copy(update={"title": "重启后草稿"}).model_dump(
                mode="json", by_alias=True
            ),
        },
    )
    assert reopened_draft.status_code == 200
    after_restart = TestClient(
        create_project_folder_authoring_app(
            ProjectFolderStorage(
                outputs_root=tmp_path / "outputs",
                application_data_root=tmp_path / "application",
            )
        )
    ).get(f"/api/v2/projects/{first_id}/authoring-drafts")
    assert after_restart.status_code == 200
    assert after_restart.json()[0]["payload"]["title"] == "重启后草稿"
    assert "v2_authoring_drafts" in _table_names(
        storage.projects.open(first_id).home / "project.sqlite3"
    )


def test_project_folder_authoring_drafts_allow_only_the_brief_and_four_canonical_editor_shapes(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    completed = ProjectPipelineExecutor(_FixtureResolver()).execute(project, profile=_fixture_profile())
    assert completed.status == RunStatus.SUCCEEDED
    client = TestClient(create_project_folder_authoring_app(storage))
    project_id = project.project().id
    stages = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"]

    brief_draft = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1,
            "expectedDraftRevision": 0,
            "payload": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
        },
    )
    assert brief_draft.status_code == 200
    for stage in stages:
        response = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": stage["head"]["stage"], "entityId": "root",
                "baseCanonicalRevision": stage["head"]["revision"],
                "expectedDraftRevision": 0, "payload": stage["payload"],
            },
        )
        assert response.status_code == 200
    assert {draft["editorScope"] for draft in client.get(
        f"/api/v2/projects/{project_id}/authoring-drafts"
    ).json()} == {"brief", "story_bible", "story_graph", "scene_beats", "storyboard"}

    rejected = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1,
            "expectedDraftRevision": 1,
            "payload": {"apiKey": "not-allowed"},
        },
    )
    assert rejected.status_code == 422
