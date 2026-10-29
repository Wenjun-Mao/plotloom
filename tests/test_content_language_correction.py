"""All eight correction registries bind a distinct semantic receipt, offline."""
from copy import deepcopy
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import (
    CheckpointEvidence,
    CommandAuthority,
    OperationScope,
)
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.content_language_candidates import candidate_row, row_request
from plotloom.content_language_classifier import STAGES
from plotloom.content_language_contract import CHECK_INPUT
from plotloom.content_language_rejection import (
    assert_language_rejection,
    rejection_for_check,
)
from plotloom.content_language_service import ContentLanguageService
from plotloom.contract_identity import utc_now
from plotloom.creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
from plotloom.creative_handoff_identity import canonical_json, request_hash
from plotloom.persistence.project.autopilot_closure import material_closure
from plotloom.persistence.project.autopilot_text_correction import (
    HEADS,
    superseded_text_failure,
)
from plotloom.persistence.project.creative_execution_pins import freeze_execution_pin
from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.persistence.schema import AutopilotCheckpointRow, AutopilotExecAttemptRow
from tests.autopilot_fixtures import policy_for
from tests.codex_exec_fixtures import PROFILE
from tests.content_language_fixtures import (
    completed_check,
    original_request,
    result_for,
    synthetic_text_receipt,
)
from tests.test_codex_exec_validation import PIN
from tests.test_content_language_contract import CANDIDATES
from tests.test_content_language_persistence import (
    check_environment as _check_environment,
)

check_environment = _check_environment


def _original_owner(session, original, candidate):
    stage, now = original.stage, utc_now()
    common = {"project_id": original.project_id, "created_at": now}
    if stage.startswith("bridge-"):
        values = common | {"id": original.job_id, "native_request": original.model_dump(mode="json", by_alias=True),
            "transport": "codex_native", "status": "dispatched", "updated_at": now, "dispatched_at": now,
            "proposal_revision": 0, "proposal_content_hash": "1"*64, "inputs": {}, "profile_snapshot": {},
            "prompt_trace": {"prompt_version": "synthetic-fixture", "rendered_hash": request_hash(original)},
            "prompt_messages": [], "response_schema": {}, "expected_entries": [], "candidate": candidate}
    else:
        values = common | {"job_id": original.job_id, "request": original.model_dump(mode="json", by_alias=True),
            "status": "ready", "manifest_hash": "1"*64, "delivery_id": "original", "report_html": "original report",
            "delivered_at": now}
        if stage in {"outline", "branches"}:
            values |= {"source_revision": 0, "expected_outline_revision": 0, "outline": candidate}
        else:
            field, revision = {"characters": ("cast", "expected_cast_revision"),
                "art": ("art", "expected_art_revision"), "script": ("script", "expected_script_revision"),
                "storyboard": ("storyboard", "expected_review_revision")}[stage]
            values |= {field: candidate, revision: 0, "binding": {}}
    row = CANDIDATE_ROWS[stage](**values)
    session.add(row)
    if HEADS[stage] is not None:
        head = session.get(HEADS[stage], original.project_id)
        head.candidate_job_id = original.job_id
    freeze_execution_pin(session, original, PIN)
    return row


@pytest.mark.parametrize("stage", STAGES)
def test_semantic_reject_creates_existing_stage_correction_without_rewriting_creation_receipt(check_environment, stage):
    _storage, store, registry = check_environment
    owner, project_id = store.repository.autopilot, store.manifest.project_id
    original = original_request(stage, project_id=project_id)
    candidate = deepcopy(CANDIDATES[stage])
    policy = policy_for(store).model_copy(update={"executor_binding": PROFILE,
        "execution_pins": {name: PIN for name in (*STAGES, "image")}, "text_correction_limit": 1})
    view = owner.start(project_id, expected_brief_revision=1, policy=policy)
    owner.claim(project_id, "fixture-controller")
    attempt = CodexExecAttempt(attempt_id=uuid4(), run_id=view.id, project_id=project_id,
        job_id=original.job_id, operation_key=stage, domain="text", request_hash=request_hash(original),
        package_hash="2"*64, profile_hash=PROFILE.profile_hash, plotloom_code_revision=policy.code_revision,
        validation_plan_hash="3"*64, reserved_image_outputs=0, image_budget_state="none", state="spawn_intent")
    prior = canonical_json(candidate)
    creation, creation_receipt = synthetic_text_receipt(attempt, PROFILE, CREATIVE_CANDIDATE_FILENAMES[stage], prior,
                                                      b"<!doctype html><title>synthetic original</title>")
    now = utc_now()
    evidence = CheckpointEvidence(owner=stage, subject_id=original.job_id, job_id=original.job_id,
        request_hash=request_hash(original), execution_pin=PIN, executor_attempt_id=creation.attempt_id,
        executor_receipt_hash=creation.evidence_hash, delivery_hash="1"*64)
    with store.repository._write() as session:
        old_row = _original_owner(session, original, candidate)
        session.add(AutopilotExecAttemptRow(id=str(creation.attempt_id), run_id=view.id, project_id=project_id,
            operation_key=stage, job_id=original.job_id, domain="text", state="completed", image_budget_state="none",
            reserved_image_outputs=0, revision=1, snapshot=creation.model_dump(mode="json", by_alias=True),
            receipt=creation_receipt.model_dump(mode="json", by_alias=True), created_at=now, updated_at=now))
        checkpoint = AutopilotCheckpointRow(id=str(uuid4()), run_id=view.id, project_id=project_id,
            operation_key=stage, revision=1, state="delivered", evidence=evidence.model_dump(mode="json", by_alias=True),
            created_at=now, updated_at=now)
        session.add(checkpoint)
        session.flush()
        run = owner.row(session, project_id)
        run.expected_closure = material_closure(session, project_id)
        before_request = row_request(old_row)
    service = ContentLanguageService(registry)
    check = service.prepare(store, original, candidate, code_revision=policy.code_revision, run_id=view.id)
    request, _data = store.repository.content_language.load(project_id, check)
    path = next(item["path"] for item in request.input_artifacts[CHECK_INPUT]["inventory"] if item["role"] == "authored_prose")
    checking, checking_receipt = completed_check(store, check, result_for(request, rejected_path=path))
    rejection = rejection_for_check(store, original, creation, check, prior)
    with store.repository.autopilot_command(CommandAuthority(view.id, "fixture-controller", OperationScope.TEXT)):
        corrective = owner.prepare_text_correction(original, rejection, prior.decode())
    assert corrective.stage == stage and corrective.job_id != original.job_id
    assert corrective.text_correction.rejection.issues[0].field_paths == (path,)
    assert corrective.text_correction.rejection.issues[0].repair_facts == {"contentLocale": "zh-CN"}
    assert corrective.text_correction.rejection.language_check.check_attempt_id == checking.attempt_id
    with store.repository._read() as session:
        current = candidate_row(session, stage, corrective.job_id)
        assert row_request(candidate_row(session, stage, original.job_id)) == before_request
        assert current.status == ("queued" if stage.startswith("bridge-") else "prepared")
        original_attempt = session.get(AutopilotExecAttemptRow, str(creation.attempt_id))
        assert original_attempt.snapshot == creation.model_dump(mode="json", by_alias=True)
        assert original_attempt.receipt == creation_receipt.model_dump(mode="json", by_alias=True)
        assert superseded_text_failure(session, owner.row(session, project_id), original_attempt, checkpoint)
        with pytest.raises(ValueError, match="exact distinct"):
            forged = rejection.model_copy(update={"language_check": rejection.language_check.model_copy(update={"result_hash": "0"*64})})
            assert_language_rejection(session.connection().connection.driver_connection, forged, original, creation)
    data = store.repository.content_language.load(project_id, check)[1]
    assert data["receipt"] == checking_receipt.model_dump(mode="json", by_alias=True)
    assert creation.terminal_result == "success" and creation.content_rejection is None
