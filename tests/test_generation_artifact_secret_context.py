"""Narrow typed continuity evidence recognition preserves credential rejection."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from plotloom.artifact_contracts import ArtifactKind
from plotloom.stage_contracts import StageName
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.generation.repair_facts import parse_semantic_repair_fact
from plotloom.persistence import stable_hash
from plotloom.runtime_secrets import RunSecretBroker
from tests.project_storage_generation_support import (
    _execute_stages,
    _MutatingFixtureProvider,
    _response_payload,
    _store,
    _with_payload,
)


def _new_continuity_validation(root: Path):
    """Create actual persisted rejected evidence using the current native owners."""
    store = _store(root)
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
    return store, validation


@pytest.fixture(scope="module")
def continuity_validation(tmp_path_factory):
    store, validation = _new_continuity_validation(
        tmp_path_factory.mktemp("continuity-secret-context")
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


def test_persisted_continuity_null_authority_survives_snapshot_and_restore(
    tmp_path: Path,
) -> None:
    import json

    from plotloom.generation.continuity_repair import (
        assert_continuity_repair_fact_matches_source,
    )
    from plotloom.generation.contracts import ValidationIssue
    from plotloom.generation.repair_facts import serialize_semantic_repair_fact
    from plotloom.generation.semantic_repair import (
        assert_semantic_repair_fact_matches_issue,
    )
    from plotloom.project_storage import ProjectFolderStorage

    source, validation = _new_continuity_validation(tmp_path / "source")
    original_content = deepcopy(validation.content)
    assert original_content["repairFacts"][0]["boundaries"][0]["assignments"][0] == {
        "kind": "fact",
        "key": "weather",
        "expectedValue": None,
    }
    owner = ProjectFolderStorage(
        outputs_root=source.home.parent,
        application_data_root=source.home.parent.parent / "application",
    )
    project_id = source.project().id
    source.close()
    receipt = owner.recovery.create_snapshot(project_id)
    assert receipt.status == "complete"
    fresh = ProjectFolderStorage(
        outputs_root=tmp_path / "restored" / "outputs",
        application_data_root=tmp_path / "restored" / "application",
    )
    fresh.recovery.restore(Path(receipt.location))
    restored = fresh.projects.open(project_id)
    try:
        artifact = restored.generation.get_artifact(validation.id)
        assert artifact.content == original_content
        assert (
            artifact.content_hash
            == validation.content_hash
            == stable_hash(artifact.content)
        )
        trace = restored.run_trace(validation.run_id)
        response = next(
            item
            for item in trace.artifacts
            if item.attempt_id == validation.attempt_id
            and item.kind == ArtifactKind.RESPONSE
        )
        rejected = json.loads(
            response.content["rawResponse"]["choices"][0]["message"]["content"]
        )
        bible = restored.authoring.get_stage_payload(project_id, StageName.STORY_BIBLE)
        issues = tuple(
            ValidationIssue.model_validate(item) for item in artifact.content["issues"]
        )
        wire = json.loads(artifact.model_dump_json())["content"]["repairFacts"]
        for raw in wire:
            fact = parse_semantic_repair_fact(raw)
            assert serialize_semantic_repair_fact(fact) == raw
            assert_semantic_repair_fact_matches_issue(fact, issues)
            assert_continuity_repair_fact_matches_source(
                fact, rejected, stage=StageName.SCENE_BEATS, bible=bible
            )
    finally:
        restored.close()
