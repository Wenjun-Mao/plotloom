"""Host completion preserves distinct role/path identities with identical pixels."""
from contextlib import closing

import pytest
from codex_exec_supervisor_image import CodexExecSupervisorImageMixin

from tests.services.creator_workbench.test_codex_exec_image_failure import _execute_image
from tests.test_codex_exec_duplicate_reference_roles import duplicate_role_delivery


def test_host_matches_every_ordered_reference_even_when_original_bytes_are_identical(tmp_path):
    _exchange, arguments, _ingest = duplicate_role_delivery(tmp_path)
    assert CodexExecSupervisorImageMixin._match_image_references(
        arguments["job_root"], arguments["request"], arguments["call"].reference_paths,
    ) == arguments["reference_hashes"]


def test_real_host_completion_consumes_one_image_and_retains_both_role_views(supervisor, tmp_path, monkeypatch):
    attempt, result, session, groups, parsed = _execute_image(supervisor, tmp_path, monkeypatch, 'same-bytes')
    assert groups and parsed == [session]
    assert result.state == 'completed' and result.attempt.terminal_result == 'success'
    assert result.attempt.image_budget_state == 'consumed' and result.attempt.remote_tool_state == 'completed'
    assert result.receipt is not None and len(result.receipt.reference_views) == 2
    assert [item.role for item in result.receipt.reference_views] == ['character_identity:C01', 'parent_output']
    hashes = result.receipt.image_evidence[0].reference_hashes
    assert len(hashes) == 2 and hashes[0] == hashes[1]
    assert len({item.package_relative_path for item in result.receipt.reference_views}) == 2
    with closing(supervisor._connect()) as connection:
        assert connection.execute('SELECT * FROM exec_slot WHERE attempt_id=?', (str(attempt.attempt_id),)).fetchone() is None
        row = supervisor._row(attempt.attempt_id)
        assert row['manifest_json'] and row['receipt_json']


@pytest.mark.parametrize('defect', ['wrong-path-order', 'wrong-view-order'])
def test_same_pixels_never_allow_reordered_paths_or_reference_views(supervisor, tmp_path, monkeypatch, defect):
    _execute_image(supervisor, tmp_path, monkeypatch, 'same-bytes-' + defect)
    with closing(supervisor._connect()) as connection:
        row = connection.execute('SELECT attempt_id FROM exec_attempts').fetchone()
        result = supervisor._load(supervisor._row(row[0]))
        assert result.state == 'outcome_unknown' and result.attempt.image_budget_state == 'reserved'
        assert result.receipt is None
        assert connection.execute('SELECT * FROM exec_slot').fetchone()
