"""Synthetic admission envelopes preserve evidence; no native/model execution."""
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom import native_bridge_request as budget
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.creative_handoff_identity import canonical_json
from plotloom.creative_handoff_package_exchange import _json_file_limit
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.production_bridge_intent import (
    ProductionBridgeIntentPersistence,
)
from plotloom.runtime_secrets import RunSecretBroker
from plotloom.production_bridge_intent_contract import MAX_INTENT_CONTEXT_BYTES
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from tests.native_bridge_runtime_fixtures import (
    create_native_intent_runtime,
    create_native_presentation_runtime,
)
from tests.production_bridge_intent_fixtures import FakeAdapter, FakeResolver, _profile


def _request(stage):
    return CreativeHandoffRequest(job_id="ch_" + "b" * 32, project_id="project", section_id="bridge",
        stage=stage, expected_stage_revision=1, source={"evidence": ""},
        input_artifacts={"schema.json": {"required": ["entries"]}}, creative_brief="完整冻结证据")


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
@pytest.mark.parametrize("difference", [-1, 0, 1])
def test_complete_request_byte_boundary_is_inclusive_and_nonmutating(stage, difference):
    request = _request(stage)
    size = len(canonical_json(request.model_dump(mode="json", by_alias=True)))
    request.source["evidence"] = "x" * (budget.MAX_NATIVE_BRIDGE_REQUEST_BYTES + difference - size)
    encoded = canonical_json(request.model_dump(mode="json", by_alias=True))
    assert len(encoded) == 1_048_576 + difference
    if difference > 0:
        with pytest.raises(InvalidTransitionError, match="bounded"):
            budget.assert_native_bridge_request_size(request)
    else:
        budget.assert_native_bridge_request_size(request)
    assert canonical_json(request.model_dump(mode="json", by_alias=True)) == encoded


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
def test_budget_counts_utf8_schema_identity_and_brief(stage, monkeypatch):
    request = _request(stage)
    request.source["evidence"] = "中文🙂" * 100
    request.input_artifacts["schema.json"]["description"] = "完整响应约束" * 100
    encoded = canonical_json(request.model_dump(mode="json", by_alias=True))
    assert len(encoded) > len(encoded.decode())
    assert len(encoded) > len(canonical_json(request.source))
    monkeypatch.setattr(budget, "MAX_NATIVE_BRIDGE_REQUEST_BYTES", len(encoded) - 1)
    with pytest.raises(InvalidTransitionError, match="bounded"):
        budget.assert_native_bridge_request_size(request)
    monkeypatch.setattr(budget, "MAX_NATIVE_BRIDGE_REQUEST_BYTES", len(encoded))
    budget.assert_native_bridge_request_size(request)


def test_native_budget_does_not_apply_to_other_stages():
    with pytest.raises(ValueError, match="intent or presentation"):
        budget.assert_native_bridge_request_size(_request("outline"))
    assert _json_file_limit(_request("outline")) == 1_000_000


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
@pytest.mark.parametrize("backend", ["specialist_chat", "codex_exec"])
def test_exact_budget_request_survives_package_metadata_and_readback(tmp_path, stage, backend):
    request = _request(stage)
    request.source["evidence"] = "x" * (budget.MAX_NATIVE_BRIDGE_REQUEST_BYTES - len(
        canonical_json(request.model_dump(mode="json", by_alias=True))))
    budget.assert_native_bridge_request_size(request)
    exchange = CreativeHandoffExchange(tmp_path)
    pin = {"upstreamRevision": "b" * 40, "upstreamSkillHash": "c" * 64, "specialistSkillHash": "d" * 64}
    options = {"executor_backend": backend}
    if backend == "codex_exec":
        options["plotloom_code_revision"] = "e" * 40
    paths = exchange.write_package(request, pin, **options)
    assert exchange.verified_package_paths(request, pin, **options) == paths
    assert _json_file_limit(request) == 2_000_000


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
def test_metadata_ceiling_refuses_before_any_package_publication(tmp_path, monkeypatch, stage):
    request = _request(stage)
    exchange = CreativeHandoffExchange(tmp_path)
    original = exchange._projection

    def oversized(*args, **kwargs):
        projected, instructions, template, expected = original(*args, **kwargs)
        projected["syntheticMetadata"] = "x" * budget.MAX_NATIVE_BRIDGE_PACKAGE_JSON_BYTES
        return projected, instructions, template, expected

    monkeypatch.setattr(exchange, "_projection", oversized)
    pin = {"upstreamRevision": "b" * 40, "upstreamSkillHash": "c" * 64, "specialistSkillHash": "d" * 64}
    with pytest.raises(ValueError, match="exceeds its file limit"):
        exchange.write_package(request, pin)
    assert not exchange._job_root(request.job_id).exists()


@pytest.mark.parametrize("stage,previous_limit", [("intent", 60_000), ("presentation", 180_000)])
def test_complete_native_file_evidence_exceeds_old_prompt_budget_without_truncation(
    tmp_path, monkeypatch, stage, previous_limit,
):
    if stage == "intent":
        storage, project, revision, digest, service, original, calls = create_native_intent_runtime(tmp_path, monkeypatch)
    else:
        storage, project, proposal, service, original, calls = create_native_presentation_runtime(tmp_path, monkeypatch)
        revision, digest = proposal.revision, proposal.content_hash
    with closing(storage.projects.open(project)) as store:
        request, _ = service._request(store, project, original)
        context, targets = store.repository.production_bridge_intent.source_context(
            project, expected_revision=revision, expected_hash=digest)
    service.cancel(project, original)
    context = deepcopy(context)
    context["scenes"][0]["cuts"][0]["frame"] = "保留完整动作与构图证据。" * (previous_limit // 12)
    assert previous_limit < len(canonical_json(context)) < 1_048_576
    monkeypatch.setattr(ProductionBridgeIntentPersistence, "source_context", lambda *_args, **_kwargs: (context, targets))
    job = service.create(project, expected_revision=revision, expected_hash=digest)
    with closing(storage.projects.open(project)) as store:
        prepared, _ = service._request(store, project, job)
        assert prepared.source["scenes"] == context["scenes"]
        assert prepared.source["brief"] == context["brief"]
        assert prepared.source["proposal"] == context["proposal"]
        assert prepared.input_artifacts == request.input_artifacts
    assert calls == []


@pytest.mark.parametrize("stage", ["intent", "presentation"])
def test_oversize_refuses_before_pin_enqueue_or_package_publication(tmp_path, monkeypatch, stage):
    if stage == "intent":
        storage, project, revision, digest, service, original, calls = create_native_intent_runtime(tmp_path, monkeypatch)
    else:
        storage, project, proposal, service, original, calls = create_native_presentation_runtime(tmp_path, monkeypatch)
        revision, digest = proposal.revision, proposal.content_hash
    service.cancel(project, original)
    with closing(storage.projects.open(project)) as store:
        before = store.production_bridge_state()
    settings = service.registry.path.read_bytes()
    monkeypatch.setattr(budget, "MAX_NATIVE_BRIDGE_REQUEST_BYTES", 1)
    forbidden = lambda *_args, **_kwargs: pytest.fail("oversize request crossed admission boundary")
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", forbidden)
    monkeypatch.setattr(CreativeHandoffExchange, "write_package", forbidden)
    monkeypatch.setattr(ProductionBridgeIntentPersistence, "enqueue", forbidden)
    with pytest.raises(InvalidTransitionError, match="bounded"):
        service.create(project, expected_revision=revision, expected_hash=digest)
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state() == before
    assert service.registry.path.read_bytes() == settings
    assert calls == []


def test_api_prompt_evidence_limit_is_unchanged(tmp_path, monkeypatch):
    storage, project, revision, digest, native, original, calls = create_native_intent_runtime(tmp_path, monkeypatch)
    native.cancel(project, original)
    with closing(storage.projects.open(project)) as store:
        context, targets = store.repository.production_bridge_intent.source_context(
            project, expected_revision=revision, expected_hash=digest)
    context["scenes"][0]["cuts"][0]["frame"] = "完整证据。" * 10_000
    assert MAX_INTENT_CONTEXT_BYTES == 60_000
    assert len(canonical_json({"context": context, "targets": targets})) > MAX_INTENT_CONTEXT_BYTES
    monkeypatch.setattr(ProductionBridgeIntentPersistence, "source_context", lambda *_args, **_kwargs: (context, targets))
    adapter = FakeAdapter()
    api = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        with pytest.raises(InvalidTransitionError, match="bounded"):
            api.create(project, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
    finally:
        api.close()
    assert adapter.calls == 0 and calls == []
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().intent_job.id == original
