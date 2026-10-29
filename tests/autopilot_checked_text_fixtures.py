"""Exact creative/checker proof owners for closed natural fixture prefixes."""
from dataclasses import dataclass

from plotloom.autopilot_launch import CREATIVE_STAGES
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt, assert_receipt_matches_attempt
from plotloom.content_language_contract import CHECK_INPUT, is_language_check
from plotloom.content_language_persistence import check_rows, verified_check


@dataclass(frozen=True)
class CheckedTextFixture:
    creative_jobs: frozenset[str]
    checker_jobs: frozenset[str]
    creative_attempts: frozenset[str]
    checker_attempts: frozenset[str]


def checked_text_fixture(store):
    """Retain eight creative rows; bind their eight separate checker envelopes."""
    with store.repository.engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT snapshot,receipt FROM v2_autopilot_exec_attempts WHERE domain='text'").all()
    count = len(CREATIVE_STAGES)
    if len(rows) != count:
        raise ValueError('fixture requires exactly eight creative text attempts')
    creative = {}
    operations = set()
    for raw_attempt, raw_receipt in rows:
        attempt = CodexExecAttempt.model_validate_json(raw_attempt)
        receipt = CodexExecReceipt.model_validate_json(raw_receipt)
        assert_receipt_matches_attempt(attempt, receipt)
        if (attempt.domain != 'text' or attempt.state not in {'completed', 'settled'}
                or attempt.terminal_result != 'success' or receipt.text_validation is None
                or attempt.image_budget_state != 'none' or attempt.reserved_image_outputs != 0):
            raise ValueError('fixture creative proof is unresolved or reserves images')
        creative[attempt.job_id] = (attempt, receipt)
        operations.add(attempt.operation_key)
    if len(creative) != count or operations != set(CREATIVE_STAGES):
        raise ValueError('fixture must cover every creative stage exactly once')
    with store.repository._read() as session:
        checks = [verified_check(row) for row in check_rows(session, store.manifest.project_id)]
    if len(checks) != count:
        raise ValueError('fixture requires exactly eight distinct checker envelopes')
    checked = set()
    for request, _data, attempt, _profile, receipt, result in checks:
        frozen = request.input_artifacts[CHECK_INPUT]
        parent_id = request.source['candidateJobId']
        parent = creative.get(parent_id)
        if (not is_language_check(request) or parent is None or parent_id in checked
                or result is None or result.verdict != 'pass' or receipt is None
                or attempt.domain != 'text' or attempt.state not in {'completed','settled'}
                or attempt.terminal_result != 'success' or request.stage != parent[0].operation_key
                or attempt.run_id != parent[0].run_id
                or frozen['originalRequestHash'] != parent[0].request_hash
                or frozen['candidateHash'] != parent[1].text_validation.candidate_hash):
            raise ValueError('fixture checker proof does not bind its distinct creative source/bytes')
        checked.add(parent_id)
    facts = CheckedTextFixture(frozenset(creative), frozenset(item[0].job_id for item in checks),
        frozenset(str(item[0].attempt_id) for item in creative.values()), frozenset(str(item[2].attempt_id) for item in checks))
    if (len(facts.checker_jobs) != count or len(facts.checker_attempts) != count
            or facts.creative_jobs & facts.checker_jobs or facts.creative_attempts & facts.checker_attempts):
        raise ValueError('fixture creative/checker native identities must be distinct')
    return facts


def assert_checked_fixture_host(host, facts, *, images=()):
    """Host accounting includes checkers; the creative execution table does not."""
    images = frozenset(images)
    expected_jobs = facts.creative_jobs | facts.checker_jobs | images
    expected_attempts = facts.creative_attempts | facts.checker_attempts
    if (host.pending or host.admissions != len(expected_jobs) or len(host.statuses) != len(expected_jobs)
            or len(host.calls) != len(facts.creative_jobs | facts.checker_jobs)
            or set(host.calls) != facts.creative_jobs | facts.checker_jobs
            or len(host.image_calls) != len(images) or set(host.image_calls) != images):
        raise ValueError('fixture host admissions must exactly cover creative, checker and image owners')
    observed_jobs = set()
    for identifier, status in host.statuses.items():
        attempt, receipt = status.attempt, status.receipt
        if (attempt is None or receipt is None or identifier != str(attempt.attempt_id)
                or status.state not in {'completed','settled'} or attempt.terminal_result != 'success'
                or (attempt.domain == 'image') != (attempt.job_id in images)
                or attempt.domain == 'text' and identifier not in expected_attempts):
            raise ValueError('fixture host lacks completed native proof for its exact owner')
        assert_receipt_matches_attempt(attempt,receipt)
        observed_jobs.add(attempt.job_id)
    if observed_jobs != expected_jobs:
        raise ValueError('fixture host native jobs differ from retained proof owners')
