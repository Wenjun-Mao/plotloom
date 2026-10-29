"""Trusted semantic findings become constrained existing correction facts."""
import json
from hashlib import sha256
from types import SimpleNamespace

from .content_language_contract import CHECK_INPUT, identity
from .content_language_persistence import verified_check
from .creative_handoff_identity import request_hash
from .text_correction_contracts import (
    LanguageRejectionProof,
    TextContentIssue,
    TextContentRejection,
)


def _language_issues(request, result):
    inventory = request.input_artifacts[CHECK_INPUT]["inventory"]
    failures = {item.span.path for item in result.findings if item.code != "uncertain_language"}
    paths = tuple(item["path"] for item in inventory if item["path"] in failures and item["role"] == "authored_prose")
    return (TextContentIssue(code="content_language_mismatch", field_paths=paths,
        repair_facts={"contentLocale": request.input_artifacts[CHECK_INPUT]["languageContract"]["contentLocale"]}),)


def assert_language_rejection(connection, rejection, parent, attempt):
    proof = rejection.language_check
    if proof is None:
        raise ValueError("semantic rejection requires its retained native checking proof")
    cursor = connection.execute("SELECT * FROM v2_source_outline_candidates WHERE job_id=? AND project_id=?",
                                (proof.check_job_id, parent.project_id))
    raw = cursor.fetchone()
    if raw is None:
        raise ValueError("semantic rejection checking row is missing")
    values = dict(zip((column[0] for column in cursor.description), raw, strict=True))
    for name in ("request", "outline"):
        values[name] = json.loads(values[name])
    request, _data, checking, _profile, receipt, result = verified_check(SimpleNamespace(**values))
    frozen = request.input_artifacts[CHECK_INPUT]
    if (result is None or result.verdict != "reject" or receipt is None
            or frozen["originalRequest"] != parent.model_dump(mode="json", by_alias=True)
            or frozen["originalRequestHash"] != request_hash(parent)
            or proof.check_attempt_id != checking.attempt_id or checking.attempt_id == attempt.attempt_id
            or checking.run_id != attempt.run_id
            or proof.check_receipt_hash != receipt.evidence_hash or proof.binding_hash != frozen["bindingHash"]
            or proof.result_hash != identity(result.model_dump(mode="json", by_alias=True))
            or rejection.validation_evidence_hash != receipt.text_validation.evidence_hash
            or rejection.issues != _language_issues(request, result)):
        raise ValueError("language correction differs from exact distinct completed semantic rejection")
    rejection.assert_attempt(attempt)


def rejection_for_check(store, original, attempt, check_job_id, prior):
    with store.repository._read() as session:
        from .persistence.schema import SourceOutlineCandidateRow
        request, _data, checking, _profile, receipt, result = verified_check(session.get(SourceOutlineCandidateRow, check_job_id))
        if result is None or result.verdict != "reject" or receipt is None:
            raise ValueError("only genuine semantic language rejection can create correction feedback")
        if json.loads(prior) != request.input_artifacts[CHECK_INPUT]["candidate"]:
            raise ValueError("rejected original candidate bytes differ from the checked complete candidate")
        rejection = TextContentRejection(source_attempt_id=attempt.attempt_id, run_id=attempt.run_id,
            stage=original.stage, job_id=original.job_id, candidate_hash=sha256(prior).hexdigest(),
            validation_evidence_hash=receipt.text_validation.evidence_hash, request_hash=attempt.request_hash,
            package_hash=attempt.package_hash, plan_hash=attempt.validation_plan_hash,
            profile_hash=attempt.profile_hash, source_revision=attempt.plotloom_code_revision,
            language_check=LanguageRejectionProof(check_job_id=check_job_id, check_attempt_id=checking.attempt_id,
                check_receipt_hash=receipt.evidence_hash, binding_hash=request.source["bindingHash"],
                result_hash=identity(result.model_dump(mode="json", by_alias=True))),
            issues=_language_issues(request, result), display_diagnostics=tuple(
                f"{item.span.path}: {item.explanation}"[:1000] for item in result.findings[:32]))
        assert_language_rejection(session.connection().connection.driver_connection, rejection, original, attempt)
        return rejection


def retained_language_rejection(store, original, attempt):
    if attempt is None or attempt.terminal_result != "success":
        return None
    from .codex_exec_files import read_confined_regular_file
    from .content_language_persistence import check_rows
    from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
    root = store.creative_handoff_exchange().root / "jobs" / original.job_id
    with store.repository._read() as session:
        jobs = [(row.job_id, verified_check(row)[-1])
                for row in check_rows(session, original.project_id, original.job_id)]
    if not any(result is not None and result.verdict == "reject" for _job, result in jobs):
        return None
    prior = read_confined_regular_file(root, "delivery/" + CREATIVE_CANDIDATE_FILENAMES[original.stage], max_bytes=500_000)
    for job, result in jobs:
        if result is not None and result.verdict == "reject":
            request, _data = store.repository.content_language.load(original.project_id, job)
            if request.input_artifacts[CHECK_INPUT]["candidate"] == json.loads(prior):
                return rejection_for_check(store, original, attempt, job, prior)
    return None
