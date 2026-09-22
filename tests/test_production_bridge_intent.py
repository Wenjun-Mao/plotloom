from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName, StageStatus
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse
from plotloom.generation.exceptions import ProviderOutcomeUnknownError, ProviderRequestNotSentError
from plotloom.generation.prompts import PromptRenderer
from plotloom.pipeline import RunSecretBroker
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentUpdateRequest
from plotloom.production_bridge_intent_contract import bind_intent_suggestions, intent_response_schema
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from plotloom.provider_profiles import StageMaxOutputTokens, TextProviderProfileSnapshotV3
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.runtime import build_runtime_app
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_production_bridge import _source_shaped_review_board
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def _profile(auth_mode: str = "none") -> dict[str, Any]:
    return TextProviderProfileSnapshotV3(
        profile_id="fake", profile_version=1, text_provider="deterministic-fake",
        text_base_url="http://localhost:18888", text_model="fake-intent",
        text_auth_mode=auth_mode, text_context_window_tokens=32768,
        text_max_output_tokens=8192, text_attempt_timeout_seconds=5,
        stage_max_output_tokens=StageMaxOutputTokens(
            story_bible=4096, story_graph=4096, scene_beats=4096, storyboard=4096,
        ),
    ).model_dump(mode="json", by_alias=True)


def _pending_project(tmp_path: Path) -> tuple[ProjectFolderStorage, str, int, str]:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
        ready = store.admit_storyboard_review_delivery(
            _deliver_stage(store, request, "storyboard.json", _source_shaped_review_board(), "bridge-intent-fixture")
        )
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(
            job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding,
        ))
        proposal = store.prepare_production_bridge().proposal
        assert proposal and not proposal.installable
        return storage, store.manifest.project_id, proposal.revision, proposal.content_hash


class FakeAdapter:
    name = "deterministic-fake"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(self, mode: str = "success", *, held: bool = False, expect_secret: bool = False) -> None:
        self.mode = mode
        self.expect_secret = expect_secret
        self.started = Event()
        self.release = Event()
        if not held:
            self.release.set()
        self.calls = 0

    def generate(self, request: Any, secret: Any) -> ProviderResponse:
        self.calls += 1
        self.started.set()
        assert self.release.wait(8)
        assert (secret is not None) == self.expect_secret
        if self.mode == "unknown":
            raise ProviderOutcomeUnknownError("transport lost after dispatch")
        if self.mode == "not_sent":
            raise ProviderRequestNotSentError("request rejected before transport")
        ids = request.response_schema["properties"]["entries"]["items"]["properties"]["id"]["enum"]
        entries = [{"id": target, "suggestedText": f"角色在此推动冲突并改变局势：{target}"} for target in ids]
        if self.mode == "duplicate":
            entries[-1]["id"] = entries[0]["id"]
        raw = {"choices": [{"message": {"role": "assistant", "content": json.dumps({"entries": entries}, ensure_ascii=False)}}]}
        return ProviderResponse(provider=self.name, model=request.model, raw=raw, request_id="fake-request")


class FakeResolver:
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter

    def resolve(self, _snapshot: Any) -> tuple[FakeAdapter, str]:
        return self.adapter, "fake-intent"


def _wait_for_job(service: ProductionBridgeIntentService, adapter: FakeAdapter, job_id: str) -> None:
    assert adapter.started.wait(8)
    future = service._active.get(job_id)
    adapter.release.set()
    if future is not None:
        future.result(timeout=15)


def test_model_result_creates_only_reviewable_bridge_revision_then_explicit_install(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "ready"
            assert state.proposal and state.proposal.revision == revision + 1
            assert state.proposal.intent_package.method == "model_inference.v1"
            assert state.proposal.intent_package.provenance["jobId"] == job_id
            assert state.proposal.installable
            for entry in state.proposal.intent_package.entries:
                assert entry.text == entry.suggested_text and entry.text != ""
                assert entry.source_content_hash
            for stage in (StageName.STORY_BIBLE, StageName.SCENE_BEATS, StageName.STORYBOARD):
                assert store.authoring.get_stage_head(project_id, stage).status == StageStatus.MISSING
            accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(
                expected_proposal_revision=state.proposal.revision,
                expected_content_hash=state.proposal.content_hash,
            ))
            assert accepted.status == "accepted"
    finally:
        service.close()


@pytest.mark.parametrize("mode,expected", [("duplicate", "failed"), ("unknown", "outcome_unknown"), ("not_sent", "failed")])
def test_invalid_or_unknown_result_never_mutates_proposal(tmp_path: Path, mode: str, expected: str) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(mode, held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == expected
            if mode == "not_sent":
                assert state.intent_job.error_code == "provider.request_not_sent"
            assert state.proposal and state.proposal.revision == revision and not state.proposal.installable
        assert adapter.calls == 1
    finally:
        service.close()


def test_late_model_result_cannot_replace_author_edit_or_cancellation(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        assert adapter.started.wait(8)
        with closing(storage.projects.open(project_id)) as store:
            proposal = store.production_bridge_state().proposal
            assert proposal
            author = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
                expected_proposal_revision=revision, expected_content_hash=digest,
                entries=[{"id": entry.id, "text": f"作者写下的目的：{entry.id}"} for entry in proposal.intent_package.entries],
            )).proposal
            assert author and author.installable
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "stale"
            assert state.proposal and state.proposal.content_hash == author.content_hash
            assert state.proposal.intent_package.method == "author_reviewed.v1"

        second = FakeAdapter(held=True)
        service.resolver = FakeResolver(second)
        second_id = service.create(project_id, expected_revision=author.revision, expected_hash=author.content_hash, profile_snapshot=_profile())
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
        {"entries": [{"id": "a", "suggestedText": "意图"}, {"id": "a", "suggestedText": "目的"}]},
        {"entries": [{"id": "a", "suggestedText": "意图"}, {"id": "b", "suggestedText": "目的"}, {"id": "c", "suggestedText": "额外"}]},
        {"entries": [{"id": "a", "suggestedText": " "}, {"id": "b", "suggestedText": "目的"}]},
    ):
        with pytest.raises(ValueError):
            bind_intent_suggestions(value, ["a", "b"])


def test_stale_brief_cannot_admit_late_inference(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        assert adapter.started.wait(8)
        with closing(storage.projects.open(project_id)) as store:
            project = store.project()
            store.update_brief(project.brief.model_copy(update={"target_playthrough_seconds": project.brief.target_playthrough_seconds + 1}), expected_revision=project.revision)
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "stale"
            assert state.proposal and state.proposal.revision == revision
    finally:
        service.close()


def test_restart_marks_only_dispatched_attempt_unknown_without_resubmitting(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    with closing(storage.projects.open(project_id)) as store:
        owner = store.repository.production_bridge_intent
        context, targets = owner.source_context(project_id, expected_revision=revision, expected_hash=digest)
        schema = intent_response_schema([item["id"] for item in targets])
        rendered = PromptRenderer().render("production_bridge_intent", {
            "source_context": context, "targets": targets, "json_schema": schema,
        })
        job_id = owner.enqueue(project_id, expected_revision=revision, expected_hash=digest,
                               profile_snapshot=_profile(), prompt_trace=rendered.trace.model_dump(mode="json"),
                               prompt_messages=[message.model_dump(mode="json") for message in rendered.messages],
                               response_schema=schema)
        assert owner.mark_dispatched(project_id, job_id)
    adapter = FakeAdapter()
    restarted = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        restarted.inspect(project_id)
        with closing(storage.projects.open(project_id)) as store:
            state = store.production_bridge_state()
            assert state.intent_job and state.intent_job.status == "outcome_unknown"
            assert state.proposal and state.proposal.revision == revision
        assert adapter.calls == 0
    finally:
        restarted.close()


def test_frozen_profile_and_attempt_evidence_never_persist_bearer_secret(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True, expect_secret=True)
    secret = "BRIDGE_TEST_SENTINEL_NEVER_PERSIST"
    service = ProductionBridgeIntentService(
        storage, resolver=FakeResolver(adapter),
        secrets=RunSecretBroker(server_profile_keys={"fake": secret}),
    )
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest,
                                profile_snapshot=_profile("bearer"))
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            assert store.production_bridge_state().intent_job.status == "ready"
            database_path = store.database_path
        with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
            persisted = connection.execute(
                "SELECT profile_snapshot, prompt_trace, prompt_messages, response_evidence, candidate "
                "FROM v2_production_bridge_intent_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        assert persisted and secret not in "".join(str(value) for value in persisted)
    finally:
        service.close()


def test_runtime_http_fake_inference_review_edit_save_then_explicit_install(tmp_path: Path) -> None:
    adapter = FakeAdapter(held=True)
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<main>Fake bridge integration</main>", encoding="utf-8")
    settings = PlotloomSettings(
        repo_root=tmp_path, outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application", static_dir=static,
        text_auth_mode="none",
    )
    app = build_runtime_app(settings, text_provider_resolver=FakeResolver(adapter))
    with TestClient(app) as client:
        storage = app.state.project_folder_storage
        with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))) as store:
            _accepted_f4_script(store)
            candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
            ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", _source_shaped_review_board(), "http-fake"))
            store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
            project_id = store.manifest.project_id
        base = f"/api/v2/projects/{project_id}/production-bridge"
        prepared = client.post(f"{base}/proposals")
        assert prepared.status_code == 200, prepared.text
        first = prepared.json()["proposal"]
        assert first["installable"] is False
        refused = client.post(f"{base}/accept", json={
            "expectedProposalRevision": first["revision"], "expectedContentHash": first["contentHash"],
        })
        assert refused.status_code in {400, 409, 422}
        generated = client.post(f"{base}/intent-jobs", json={
            "expectedProposalRevision": first["revision"], "expectedContentHash": first["contentHash"],
        })
        assert generated.status_code == 202, generated.text
        job_id = generated.json()["intentJob"]["id"]
        assert adapter.started.wait(8)
        running = client.get(base)
        assert running.status_code == 200 and running.json()["intentJob"]["status"] == "dispatched"
        _wait_for_job(app.state.bridge_intent_service, adapter, job_id)
        inferred = client.get(base)
        assert inferred.status_code == 200, inferred.text
        proposal = inferred.json()["proposal"]
        assert inferred.json()["intentJob"]["status"] == "ready"
        assert proposal["intentPackage"]["method"] == "model_inference.v1"
        updates = [{"id": entry["id"], "text": "作者确认并修改：" + entry["text"]} for entry in proposal["intentPackage"]["entries"]]
        saved = client.put(f"{base}/proposals/intent", json={
            "expectedProposalRevision": proposal["revision"], "expectedContentHash": proposal["contentHash"],
            "entries": updates,
        })
        assert saved.status_code == 200, saved.text
        revised = saved.json()["proposal"]
        assert revised["intentPackage"]["method"] == "author_reviewed.v1"
        stale_accept = client.post(f"{base}/accept", json={
            "expectedProposalRevision": proposal["revision"], "expectedContentHash": proposal["contentHash"],
        })
        assert stale_accept.status_code in {400, 409, 422}
        accepted = client.post(f"{base}/accept", json={
            "expectedProposalRevision": revised["revision"], "expectedContentHash": revised["contentHash"],
        })
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "accepted"
