"""Profile reuse leaves every successful receipt's snapshot revalidation intact."""
from contextlib import closing
import json
import sqlite3
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import (
    CodexExecAttempt, CodexExecOutputEvidence, CodexExecReceipt,
    assert_receipt_matches_attempt, output_manifest_hash,
)
from plotloom.persistence.project import autopilot_bindings as bindings
from plotloom.project_storage import autopilot_validation as validation
from plotloom.project_storage.format import ProjectStorageCorruptionError
from tests.autopilot_profile_fixtures import observe_constructions, seed_profile_graph
from tests.test_codex_exec_contracts import profile


def complete_retained_text(connection, graph):
    output = CodexExecOutputEvidence(output_hash="a" * 64,
        output_relative_path="delivery/outline.json", size_bytes=12)
    completed = CodexExecAttempt.model_validate(graph.attempt.model_dump(mode="python") | {
        "state": "completed", "terminal_result": "success", "remote_tool_state": "not_applicable",
        "session_id": uuid4(), "process_id": 123, "process_group_id": 123,
        "process_birth_identity": "test-owned-process", "process_exit_code": 0,
        "evidence_hash": "b" * 64, "output_hash": output_manifest_hash([output]),
    })
    receipt = CodexExecReceipt(attempt_id=completed.attempt_id, session_id=completed.session_id,
        profile_hash=completed.profile_hash, request_hash=completed.request_hash,
        package_hash=completed.package_hash, plotloom_code_revision=completed.plotloom_code_revision,
        process_id=123, process_group_id=123, process_birth_identity=completed.process_birth_identity,
        process_exit_code=0, expected_image_outputs=0, evidence_hash=completed.evidence_hash,
        output_hash=completed.output_hash, outputs=[output], remote_tool_state="not_applicable")
    assert_receipt_matches_attempt(completed, receipt)
    graph.evidence = graph.evidence.model_copy(update={
        "executor_receipt_hash": completed.evidence_hash, "delivery_hash": "c" * 64})
    connection.execute("UPDATE v2_autopilot_exec_attempts SET state='completed',snapshot=?,receipt=?",
        (completed.model_dump_json(by_alias=True), receipt.model_dump_json(by_alias=True)))
    connection.execute("UPDATE v2_autopilot_checkpoints SET state='delivered',evidence=?",
        (graph.evidence.model_dump_json(by_alias=True),))
    decision = json.loads(connection.execute("SELECT decision FROM v2_autopilot_decisions").fetchone()[0])
    decision["evidence"] = graph.evidence.model_dump(mode="json", by_alias=True)
    connection.execute("UPDATE v2_autopilot_decisions SET decision=?", (json.dumps(decision),))
    connection.execute("UPDATE v2_source_outline_candidates SET manifest_hash=?", (graph.evidence.delivery_hash,))
    connection.commit()


@pytest.mark.parametrize("forgery", [None, "attempt", "receipt"])
def test_private_profile_never_substitutes_for_receipt_snapshot_revalidation(tmp_path, monkeypatch, forgery):
    with closing(sqlite3.connect(tmp_path / "receipts.sqlite3")) as connection:
        graph = seed_profile_graph(connection, profile=profile())
        complete_retained_text(connection, graph)
        connection.execute("PRAGMA query_only=ON")
        boundaries = []

        def boundary(attempt, receipt):
            boundaries.append(attempt.attempt_id)
            if forgery == "attempt":
                attempt = attempt.model_copy(update={"process_birth_identity": None})
            elif forgery == "receipt":
                receipt = receipt.model_copy(update={"output_hash": "0" * 64})
            assert_receipt_matches_attempt(attempt, receipt)

        monkeypatch.setattr(bindings, "assert_receipt_matches_attempt", boundary)
        monkeypatch.setattr(validation, "assert_receipt_matches_attempt", boundary)
        calls = observe_constructions(monkeypatch)
        before = connection.total_changes
        if forgery:
            with pytest.raises(ProjectStorageCorruptionError) as caught:
                validation.assert_autopilot_contracts(connection)
            assert isinstance(caught.value.__cause__, ValidationError)
            assert len(boundaries) == 1
        else:
            validation.assert_autopilot_contracts(connection)
            assert len(boundaries) == 3  # Checkpoint, attempt inventory, decision.
        assert len(calls) == 1
        assert connection.total_changes == before
