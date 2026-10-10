from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from plotloom.domain import StageName, StageStatus
from plotloom.exceptions import InvalidTransitionError
from plotloom.generation.prompts import PromptRenderer
from plotloom.pipeline import RunSecretBroker
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.production_bridge_intent_contract import (
    bind_intent_suggestions,
    intent_response_schema,
)
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from tests.production_bridge_intent_fixtures import (
    FakeAdapter,
    FakeResolver,
    _pending_project,
    _profile,
    _wait_for_job,
)


def test_model_result_creates_only_reviewable_bridge_revision_then_explicit_install(
    tmp_path: Path,
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker()
    )
    try:
        job_id = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
        )
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "ready"
            assert state.proposal and state.proposal.revision == revision + 1
            assert (
                state.proposal.intent_package.suggestion_origin == "model_inference.v1"
            )
            assert state.proposal.intent_package.review_state == "model_suggested"
            assert state.proposal.intent_package.provenance["jobId"] == job_id
            assert not state.proposal.installable
            for entry in state.proposal.intent_package.entries:
                assert entry.text == entry.suggested_text and entry.text != ""
                assert entry.source_excerpt != entry.suggested_text
                assert entry.source_content_hash
            for stage in (
                StageName.STORY_BIBLE,
                StageName.SCENE_BEATS,
                StageName.STORYBOARD,
            ):
                assert (
                    store.authoring.get_stage_head(project_id, stage).status
                    == StageStatus.MISSING
                )
            with pytest.raises(InvalidTransitionError):
                store.accept_production_bridge(
                    ProductionBridgeAcceptRequest(
                        expected_proposal_revision=state.proposal.revision,
                        expected_content_hash=state.proposal.content_hash,
                    )
                )
            reviewed = store.update_production_bridge_intent_package(
                ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=state.proposal.revision,
                    expected_content_hash=state.proposal.content_hash,
                    entries=[
                        {"id": entry.id, "text": entry.text}
                        for entry in state.proposal.intent_package.entries
                    ],
                )
            )
            accepted = store.accept_production_bridge(
                ProductionBridgeAcceptRequest(
                    expected_proposal_revision=reviewed.proposal.revision,
                    expected_content_hash=reviewed.proposal.content_hash,
                )
            )
            assert accepted.status == "accepted"
    finally:
        service.close()


def test_model_edit_save_reload_and_reinfer_keep_source_suggestion_and_author_text_distinct(
    tmp_path: Path,
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    first_adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(first_adapter), secrets=RunSecretBroker()
    )
    try:
        with closing(storage.projects.open(project_id)) as store:
            initial = store.production_bridge_state().proposal
            assert initial
            excerpts = {
                entry.id: entry.source_excerpt
                for entry in initial.intent_package.entries
            }
        first_job = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
        )
        _wait_for_job(service, first_adapter, first_job)
        with closing(storage.projects.open(project_id)) as store:
            inferred = store.production_bridge_state().proposal
            assert inferred
            originals = {
                entry.id: entry.suggested_text
                for entry in inferred.intent_package.entries
            }
            assert all(
                entry.source_excerpt == excerpts[entry.id]
                for entry in inferred.intent_package.entries
            )
            saved = store.update_production_bridge_intent_package(
                ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=inferred.revision,
                    expected_content_hash=inferred.content_hash,
                    entries=[
                        {"id": entry.id, "text": f"作者修订：{entry.id}"}
                        for entry in inferred.intent_package.entries
                    ],
                )
            ).proposal
            assert saved
        with closing(storage.projects.open(project_id)) as store:
            reloaded = store.production_bridge_state().proposal
            assert reloaded
            assert reloaded.intent_package.review_state == "author_saved"
            assert reloaded.intent_package.suggestion_origin == "model_inference.v1"
            assert reloaded.intent_package.provenance["jobId"] == first_job
            for entry in reloaded.intent_package.entries:
                assert entry.source_excerpt == excerpts[entry.id]
                assert entry.suggested_text == originals[entry.id]
                assert entry.text == f"作者修订：{entry.id}"
            _context, targets = (
                store.repository.production_bridge_intent.source_context(
                    project_id,
                    expected_revision=reloaded.revision,
                    expected_hash=reloaded.content_hash,
                )
            )
            assert {
                target["id"]: target["sourceExcerpt"] for target in targets
            } == excerpts
        second_adapter = FakeAdapter(held=True)
        service.resolver = FakeResolver(second_adapter)
        second_job = service.create(
            project_id,
            expected_revision=reloaded.revision,
            expected_hash=reloaded.content_hash,
            profile_snapshot=_profile(),
        )
        with closing(storage.projects.open(project_id)) as store:
            entries = store.repository.production_bridge_intent.expected_entries(
                project_id, second_job
            )
            assert {
                entry["id"]: entry["sourceExcerpt"] for entry in entries
            } == excerpts
        _wait_for_job(service, second_adapter, second_job)
        with closing(storage.projects.open(project_id)) as store:
            reinferred = store.production_bridge_state().proposal
            assert (
                reinferred
                and reinferred.intent_package.provenance["jobId"] == second_job
            )
            assert all(
                entry.source_excerpt == excerpts[entry.id]
                for entry in reinferred.intent_package.entries
            )
    finally:
        service.close()


@pytest.mark.parametrize(
    "mode,expected",
    [("duplicate", "failed"), ("unknown", "outcome_unknown"), ("not_sent", "failed")],
)
def test_invalid_or_unknown_result_never_mutates_proposal(
    tmp_path: Path, mode: str, expected: str
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(mode, held=True)
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker()
    )
    try:
        job_id = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
        )
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == expected
            if mode == "not_sent":
                assert state.intent_job.error_code == "provider.request_not_sent"
            assert (
                state.proposal
                and state.proposal.revision == revision
                and not state.proposal.installable
            )
        assert adapter.calls == 1
    finally:
        service.close()


def test_late_model_result_cannot_replace_author_edit_or_cancellation(
    tmp_path: Path,
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker()
    )
    try:
        job_id = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
        )
        assert adapter.started.wait(8)
        with closing(storage.projects.open(project_id)) as store:
            proposal = store.production_bridge_state().proposal
            assert proposal
            author = store.update_production_bridge_intent_package(
                ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=revision,
                    expected_content_hash=digest,
                    entries=[
                        {"id": entry.id, "text": f"作者写下的目的：{entry.id}"}
                        for entry in proposal.intent_package.entries
                    ],
                )
            ).proposal
            assert author and author.installable
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "stale"
            assert state.proposal and state.proposal.content_hash == author.content_hash
            assert state.proposal.intent_package.review_state == "author_saved"
            assert state.proposal.intent_package.suggestion_origin == "none"

        second = FakeAdapter(held=True)
        service.resolver = FakeResolver(second)
        second_id = service.create(
            project_id,
            expected_revision=author.revision,
            expected_hash=author.content_hash,
            profile_snapshot=_profile(),
        )
        assert second.started.wait(8)
        service.cancel(project_id, second_id)
        _wait_for_job(service, second, second_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "cancelled"
            assert state.proposal and state.proposal.content_hash == author.content_hash
    finally:
        service.close()


def test_exact_target_contract_rejects_missing_extra_duplicate_and_blank() -> None:
    for value in (
        {"entries": [{"id": "a", "suggestedText": "意图"}]},
        {
            "entries": [
                {"id": "a", "suggestedText": "意图"},
                {"id": "a", "suggestedText": "目的"},
            ]
        },
        {
            "entries": [
                {"id": "a", "suggestedText": "意图"},
                {"id": "b", "suggestedText": "目的"},
                {"id": "c", "suggestedText": "额外"},
            ]
        },
        {
            "entries": [
                {"id": "a", "suggestedText": " "},
                {"id": "b", "suggestedText": "目的"},
            ]
        },
    ):
        with pytest.raises(ValueError):
            bind_intent_suggestions(value, ["a", "b"])


def test_stale_brief_cannot_admit_late_inference(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker()
    )
    try:
        job_id = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
        )
        assert adapter.started.wait(8)
        with closing(storage.projects.open(project_id)) as store:
            project = store.project()
            store.update_brief(
                project.brief.model_copy(
                    update={
                        "target_playthrough_seconds": project.brief.target_playthrough_seconds
                        + 1
                    }
                ),
                expected_revision=project.revision,
            )
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "stale"
            assert state.proposal and state.proposal.revision == revision
    finally:
        service.close()


def test_restart_marks_only_dispatched_attempt_unknown_without_resubmitting(
    tmp_path: Path,
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    with closing(storage.projects.open(project_id)) as store:
        owner = store.repository.production_bridge_intent
        context, targets = owner.source_context(
            project_id, expected_revision=revision, expected_hash=digest
        )
        schema = intent_response_schema([item["id"] for item in targets])
        rendered = PromptRenderer().render(
            "production_bridge_intent",
            {
                "source_context": context,
                "targets": targets,
                "json_schema": schema,
            },
        )
        job_id = owner.enqueue(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile(),
            prompt_trace=rendered.trace.model_dump(mode="json"),
            prompt_messages=[
                message.model_dump(mode="json") for message in rendered.messages
            ],
            response_schema=schema,
        )
        assert owner.mark_dispatched(project_id, job_id)
    adapter = FakeAdapter()
    restarted = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker()
    )
    try:
        restarted.inspect(project_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "outcome_unknown"
            assert state.proposal and state.proposal.revision == revision
        assert adapter.calls == 0
    finally:
        restarted.close()


def test_frozen_profile_and_attempt_evidence_never_persist_bearer_secret(
    tmp_path: Path,
) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True, expect_secret=True)
    secret = "BRIDGE_TEST_SENTINEL_NEVER_PERSIST"
    service = ProductionBridgeIntentService(
        storage,
        resolver=FakeResolver(adapter),
        secrets=RunSecretBroker(server_profile_keys={"fake": secret}),
    )
    try:
        job_id = service.create(
            project_id,
            expected_revision=revision,
            expected_hash=digest,
            profile_snapshot=_profile("bearer"),
        )
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            assert store.production_bridge_state().intent_job.status == "ready"
            database_path = store.database_path
        with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
            persisted = connection.execute(
                "SELECT profile_snapshot, prompt_trace, prompt_messages, response_evidence, candidate "
                "FROM v2_production_bridge_intent_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        assert persisted and secret not in "".join(str(value) for value in persisted)
    finally:
        service.close()
