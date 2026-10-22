"""Compact prefix eligibility first; all safety continuation remains copy-local."""
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from plotloom.project_storage import ProjectStorageCorruptionError
from tests import autopilot_controller_fixtures
from tests.autopilot_compact_text_fixtures import (
    assert_compact_two_cut_text_boundary,
    copy_compact_two_cut_text_prefix,
)
from tests.autopilot_controller_fixtures import candidate as natural_candidate
from tests.autopilot_controller_fixtures import (
    default_brief,
    environment,
    run_text,
    runtime,
)
from tests.autopilot_image_fixtures import handoff_image_environment
from tests.autopilot_installed_text_fixtures import assert_installed_text_boundary
from tests.autopilot_seed_fixtures import (
    copy_closed_autopilot_seed,
    freeze_closed_autopilot_seed,
    seed_files,
    run_facts,
)
from tests.test_autopilot_image_safety import reach
from tests.test_autopilot_installed_text_seed import _identity


def test_cold_compact_prefix_is_exact_closed_natural_text_only(compact_two_cut_text_prefix, tmp_path, monkeypatch):
    seed = compact_two_cut_text_prefix
    assert autopilot_controller_fixtures.candidate is natural_candidate
    assert len(seed.text_records) == 8 and len({row[0] for row in seed.text_records}) == 8
    for identifier, snapshot, raw_receipt in seed.text_records:
        attempt = CodexExecAttempt.model_validate_json(snapshot)
        receipt = CodexExecReceipt.model_validate_json(raw_receipt)
        assert str(attempt.attempt_id) == identifier and attempt.domain == "text"
        assert attempt.terminal_result == "success"
        assert_receipt_matches_attempt(attempt, receipt)
    storage, view = copy_closed_autopilot_seed(seed.project, tmp_path / "inspect")
    registry, service, host = runtime(storage, monkeypatch)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            checked, policy, records = assert_compact_two_cut_text_boundary(store, registry)
            assert (str(checked.id), policy, records) == (seed.run_id, seed.policy_text, seed.text_records)
            assert checked.phase == "references" and not checked.frames and checked.bundle is None
        assert not host.calls and not host.image_calls and not host.statuses and not host.pending
        assert host.admissions == 0 and not registry.view()["busy"]
    finally:
        service.close()
    assert seed_files(seed.project.root) == seed.project.files
    assert freeze_closed_autopilot_seed(seed.project.root, seed.project.project_id, seed.project.home_name) == seed.project


def test_compact30s_wrong_aspect_refuses_at_exact_brief_value_boundary(
    tmp_path, monkeypatch, compact_two_cut_text_prefix,
):
    """Isolate Brief value/error priority; persisted text remains valid and unchanged."""
    seed = compact_two_cut_text_prefix
    storage, view = copy_closed_autopilot_seed(seed.project, tmp_path / "brief-value")
    registry, service, host = runtime(storage, monkeypatch)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            actual = store.project()
            assert actual.brief.target_playthrough_seconds == 30 and actual.brief.aspect_ratio != "9:16"
            wrong_brief = actual.brief.model_copy(update={"aspect_ratio": "9:16"})
            altered = actual.model_copy(update={"brief": wrong_brief})
            assert altered.model_dump(exclude={"brief"}) == actual.model_dump(exclude={"brief"})
            assert wrong_brief.model_dump(exclude={"aspect_ratio"}) == actual.brief.model_dump(exclude={"aspect_ratio"})
            with monkeypatch.context() as value_only:
                value_only.setattr(store, "project", lambda: altered)
                with pytest.raises(ValueError, match="^compact two-cut text prefix requires the exact compact30s Brief$"):
                    assert_compact_two_cut_text_boundary(store, registry)
            assert store.project() == actual
        assert host.admissions == 0 and not host.calls and not host.image_calls and not host.statuses and not host.pending
    finally:
        service.close()
    assert seed_files(seed.project.root) == seed.project.files


def test_default_and_compact_boundaries_remain_mutually_exclusive(
    tmp_path, monkeypatch, compact_two_cut_text_prefix, installed_text_prefix,
):
    pairs = ((compact_two_cut_text_prefix, assert_installed_text_boundary, "unchanged default Brief"),
        (installed_text_prefix, assert_compact_two_cut_text_boundary, "exact compact30s Brief"))
    for index, (seed, boundary, error) in enumerate(pairs):
        storage, view = copy_closed_autopilot_seed(seed.project, tmp_path / str(index))
        registry, service, host = runtime(storage, monkeypatch)
        try:
            with closing(storage.projects.open(view.project_id)) as store, pytest.raises(ValueError, match=error):
                boundary(store, registry)
            assert host.admissions == 0 and not host.calls and not host.image_calls
        finally:
            service.close()


@pytest.mark.parametrize("variant", ["four-cut", "brief", "policy"])
def test_valid_other_text_cuts_are_ineligible(tmp_path, monkeypatch, variant):
    if variant == "brief":
        storage, registry, service, view, calls = environment(tmp_path, monkeypatch,
            brief=default_brief().model_copy(update={"aspect_ratio": "9:16"}))
        view = run_text(service, view)
    else:
        storage, registry, service, view, images, calls = handoff_image_environment(
            tmp_path, monkeypatch, cuts_per_scene=4 if variant == "four-cut" else 2,
            limits={"max_images": 79} if variant == "policy" else None)
        assert not images
    try:
        assert len(calls) == 8 and view.phase == "references"
        error = {"four-cut": "exactly two5s cuts", "brief": "exact compact30s Brief",
            "policy": "unchanged compact policy"}[variant]
        with closing(storage.projects.open(view.project_id)) as store, pytest.raises(ValueError, match=error):
            assert_compact_two_cut_text_boundary(store, registry)
    finally:
        service.close()


def test_two_copies_fresh_claim_hosts_receipts_and_isolation(
    tmp_path, monkeypatch, compact_two_cut_text_prefix,
):
    seed = compact_two_cut_text_prefix
    roots = [tmp_path / name for name in ("left", "right")]
    left = copy_compact_two_cut_text_prefix(seed, roots[0], monkeypatch)
    right = None
    try:
        right = copy_compact_two_cut_text_prefix(seed, roots[1], monkeypatch)
        assert left.view.id == right.view.id == seed.run_id
        assert left.registry is not right.registry and left.service is not right.service
        assert left.registry._codex_exec_test_host is not right.registry._codex_exec_test_host
        assert left.service.claim != right.service.claim
        for copied in (left, right):
            claim, records = _identity(copied)
            assert claim == copied.service.claim and records == seed.text_records
            host = copied.registry._codex_exec_test_host
            assert not copied.text_calls and not copied.image_calls and not host.statuses and not host.pending
            assert host.admissions == 0 and not copied.registry.view()["busy"]
            times = {"created_at", "updated_at"}
            assert run_facts(copied.claim_view, exclude=times) == run_facts(copied.view, exclude=times)
        for relative, _digest in seed.project.files:
            paths = [root / relative for root in (seed.project.root, *roots)]
            assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
        with pytest.raises(ValueError, match="active resources"):
            freeze_closed_autopilot_seed(roots[0], seed.project.project_id, seed.project.home_name)
        attempt_ids = []
        for copied in (left, right):
            result, _checkpoint = reach(copied.storage, copied.service, copied.view, "image", "delivered")
            assert len(copied.image_calls) == 3 and not copied.text_calls and not result.frames
            assert _identity(copied)[1] == seed.text_records
            with closing(copied.storage.projects.open(result.project_id)) as store, store.repository.engine.connect() as connection:
                rows = connection.exec_driver_sql(
                    "SELECT id,job_id,snapshot,receipt FROM v2_autopilot_exec_attempts WHERE domain='image'").all()
                assert len(rows) == 3 and all(row.receipt is not None for row in rows)
                assert {row.job_id for row in rows} == set(copied.image_calls)
            attempt_ids.append({row.id for row in rows})
        assert set(left.image_calls).isdisjoint(right.image_calls) and attempt_ids[0].isdisjoint(attempt_ids[1])
        left.service.close()
        later = freeze_closed_autopilot_seed(roots[0], seed.project.project_id, seed.project.home_name)
        with pytest.raises(ValueError, match="installation cut|inventory/image|image/material"):
            copy_compact_two_cut_text_prefix(replace(seed, project=later), tmp_path / "post-image", monkeypatch)
        right.service.close()
        sibling_files = seed_files(roots[1])
        with closing(left.storage.projects.open(seed.project.project_id)) as store:
            before = store.repository.autopilot.current(seed.project.project_id)
            with pytest.raises(RuntimeError, match="rollback"), store.repository.engine.begin() as connection:
                connection.exec_driver_sql("UPDATE v2_autopilot_runs SET revision=revision+1")
                raise RuntimeError("rollback")
            assert run_facts(store.repository.autopilot.current(seed.project.project_id)) == run_facts(before)
            database = store.database_path
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("UPDATE v2_autopilot_runs SET policy_hash=?", ("0" * 64,))
        with pytest.raises(ProjectStorageCorruptionError), closing(left.storage.projects.open(seed.project.project_id)):
            pytest.fail("altered destination was admitted")
        assert seed_files(roots[1]) == sibling_files and seed_files(seed.project.root) == seed.project.files
        assert autopilot_controller_fixtures.candidate is natural_candidate
    finally:
        left.service.close()
        if right is not None:
            right.service.close()


def test_completed_handoff_pack_is_not_a_text_prefix(tmp_path, monkeypatch, compact_two_cut_text_prefix, awaiting_handoff_seed):
    seed = replace(compact_two_cut_text_prefix, project=awaiting_handoff_seed.project)
    with pytest.raises(ValueError, match="exact current installation cut"):
        copy_compact_two_cut_text_prefix(seed, tmp_path / "completed-pack", monkeypatch)
    assert seed_files(compact_two_cut_text_prefix.project.root) == compact_two_cut_text_prefix.project.files


def test_unresolved_retained_text_is_refused_by_ordinary_admission(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    seed = compact_two_cut_text_prefix
    root = tmp_path / "unresolved"
    storage, view = copy_closed_autopilot_seed(seed.project, root)
    with closing(storage.projects.open(view.project_id)) as store:
        database = store.database_path
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE v2_autopilot_exec_attempts SET state='running'")
    altered = freeze_closed_autopilot_seed(root, seed.project.project_id, seed.project.home_name)
    with pytest.raises(ProjectStorageCorruptionError):
        copy_compact_two_cut_text_prefix(replace(seed, project=altered), tmp_path / "refused", monkeypatch)
    assert seed_files(seed.project.root) == seed.project.files


@pytest.mark.parametrize("member", ["package", "input", "report", "completion"])
def test_corrupt_retained_text_bytes_are_refused_by_existing_owner(
    tmp_path, monkeypatch, compact_two_cut_text_prefix, member,
):
    seed = compact_two_cut_text_prefix
    root = tmp_path / "corrupt"
    storage, view = copy_closed_autopilot_seed(seed.project, root)
    with closing(storage.projects.open(view.project_id)) as store:
        job = store.creative_handoff_exchange().root / "jobs" / next(
            item["evidence"]["jobId"] for item in view.checkpoints if item["operationKey"] == "characters")
    if member == "completion":
        (job / "delivery/completion.json").unlink()
    else:
        path = next((job / "package/inputs").iterdir()) if member == "input" else job / (
            "package/request.json" if member == "package" else "delivery/report.html")
        path.write_bytes(path.read_bytes() + b"\n")
    altered = freeze_closed_autopilot_seed(root, seed.project.project_id, seed.project.home_name)
    with pytest.raises(ProjectStorageCorruptionError):
        copy_compact_two_cut_text_prefix(replace(seed, project=altered), tmp_path / "refused", monkeypatch)
    assert seed_files(seed.project.root) == seed.project.files
