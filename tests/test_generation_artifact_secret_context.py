"""Narrow typed continuity evidence recognition preserves credential rejection."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from plotloom.domain import ArtifactKind, StageName
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.generation.repair_facts import parse_semantic_repair_fact
from plotloom.persistence import stable_hash
from plotloom.pipeline import RunSecretBroker
from tests.project_storage_generation_support import (
    _execute_stages,
    _MutatingFixtureProvider,
    _response_payload,
    _store,
    _with_payload,
)


@pytest.fixture(scope="module")
def continuity_validation(tmp_path_factory):
    """A real persisted rejected validation artifact, not a fabricated fact."""
    store = _store(tmp_path_factory.mktemp("continuity-secret-context"))
    corrected = None

    def reject_once(request, response):
        nonlocal corrected
        prompt = "\n".join(message.content for message in request.messages)
        if corrected is not None:
            return (
                _with_payload(response, corrected)
                if "semantic.continuity_beat_sequence_mismatch" in prompt
                else response
            )
        if "【目标故事节点】" not in prompt:
            return response
        payload = _response_payload(response)
        payload["scenes"][0]["entryState"]["facts"] = {"weather": None}
        payload["beats"][0]["entryState"]["facts"] = {"weather": "rain"}
        corrected = deepcopy(payload)
        corrected["beats"][0]["entryState"]["facts"]["weather"] = None
        return _with_payload(response, payload)

    broker = RunSecretBroker()
    try:
        run, completed = _execute_stages(
            store,
            [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
            _MutatingFixtureProvider(reject_once),
            broker,
        )
    finally:
        broker.close()
    assert completed.status.value == "succeeded"
    validation = next(
        artifact
        for artifact in store.run_trace(run.id).artifacts
        if artifact.kind == ArtifactKind.VALIDATION and artifact.content["repairFacts"]
    )
    yield store, validation
    store.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "fact_key",
        "credential_value",
        "nested_value",
        "sibling_key",
        "outside_fact",
        "extra",
        "unknown_code",
        "wrong_assignment_kind",
        "duplicate_alias",
        "malformed",
        "typed_object",
        "lookalike_object",
        "prompt",
        "response",
        "accepted",
        "missing_contract",
        "wrong_contract_unit",
        "wrong_contract_stage",
        "wrong_issue",
        "missing_attempt",
        "missing_unit",
    ],
)
def test_only_the_exact_typed_validation_slot_can_bypass_the_setting_name_scan(
    continuity_validation,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    store, original = continuity_validation
    content = deepcopy(original.content)
    fact = content["repairFacts"][0]
    assignment = fact["boundaries"][0]["assignments"][0]
    changes = {}
    if mutation == "fact_key":
        assignment["key"] = "apiKey"
    elif mutation == "credential_value":
        assignment["expectedValue"] = "Bearer fixture-credential"
    elif mutation == "nested_value":
        assignment["expectedValue"] = {"nested": {"password": "fixture-value"}}
    elif mutation == "sibling_key":
        assignment["extra"] = {"key": "fixture-value"}
    elif mutation == "outside_fact":
        content["other"] = {"key": "fixture-value"}
    elif mutation == "extra":
        fact["extra"] = "preserve-and-refuse"
    elif mutation == "unknown_code":
        fact["code"] = "semantic.lookalike"
    elif mutation == "wrong_assignment_kind":
        assignment["kind"] = "lookalike"
    elif mutation == "duplicate_alias":
        assignment["expected_value"] = assignment["expectedValue"]
    elif mutation == "malformed":
        del assignment["expectedValue"]
    elif mutation == "typed_object":
        content["repairFacts"][0] = parse_semantic_repair_fact(fact)
    elif mutation == "lookalike_object":
        content["repairFacts"][0] = SimpleNamespace(**fact)
    elif mutation in {"prompt", "response"}:
        changes["kind"] = ArtifactKind(mutation)
    elif mutation == "accepted":
        content["accepted"] = True
    elif mutation == "missing_contract":
        del content["contract"]
    elif mutation == "wrong_contract_unit":
        content["contract"]["work_unit_id"] = "foreign-unit"
    elif mutation == "wrong_contract_stage":
        changes["stage"] = StageName.STORYBOARD
    elif mutation == "wrong_issue":
        content["issues"][0]["path"] = ["scenes", 99]
    elif mutation == "missing_attempt":
        changes["attempt_id"] = None
    elif mutation == "missing_unit":
        changes["work_unit_id"] = None
    before = deepcopy(content)
    candidate = original.model_copy(
        update={"id": str(uuid4()), "content": content, **changes}
    )

    def forbidden_write():
        raise AssertionError("credential evidence reached a persistence lease")

    with monkeypatch.context() as context:
        context.setattr(
            store.generation._evidence,
            "_access",
            replace(
                store.generation._evidence._access,
                leases=replace(
                    store.generation._evidence._access.leases, write=forbidden_write
                ),
            ),
        )
        with pytest.raises(
            InvalidTransitionError, match="secret-shaped|canonical typed"
        ):
            store.generation.add_artifact(candidate)
    assert content == before
    with pytest.raises(NotFoundError):
        store.generation.get_artifact(candidate.id)
    assert store.generation.get_artifact(original.id).content == original.content


def test_raw_response_persistence_has_no_validation_artifact_exemption(
    continuity_validation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, artifact = continuity_validation

    def forbidden_write():
        raise AssertionError("raw response credential evidence reached persistence")

    with monkeypatch.context() as context:
        context.setattr(
            store.generation._attempts,
            "_access",
            replace(
                store.generation._attempts._access,
                leases=replace(
                    store.generation._attempts._access.leases, write=forbidden_write
                ),
            ),
        )
        with pytest.raises(InvalidTransitionError, match="secret-shaped"):
            store.generation.persist_attempt_response(
                artifact.attempt_id, deepcopy(artifact.content)
            )


def test_generic_redaction_remains_accepted_without_rewriting_evidence(
    continuity_validation,
) -> None:
    store, artifact = continuity_validation
    content = {"authorization": "[redacted]", "nested": {"key": "[redacted]"}}
    candidate = artifact.model_copy(
        update={
            "id": str(uuid4()),
            "kind": ArtifactKind.PROMPT,
            "attempt_id": None,
            "work_unit_id": None,
            "stage": None,
            "content": content,
            "content_hash": stable_hash(content),
        }
    )
    stored = store.generation.add_artifact(candidate)
    assert stored.content == content == store.generation.get_artifact(stored.id).content
