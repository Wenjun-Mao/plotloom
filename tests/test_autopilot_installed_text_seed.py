"""Installed text reuse retains history while every continuation owns fresh work."""
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from plotloom.project_storage import ProjectStorageCorruptionError
from tests.autopilot_controller_fixtures import default_brief, environment, run_text
from tests.autopilot_geometry_fixtures import first_geometry_frame, mismatch
from tests.autopilot_installed_text_fixtures import (
    assert_installed_text_boundary,
    copy_installed_text_prefix,
)
from tests.autopilot_seed_fixtures import (
    copy_closed_autopilot_seed,
    freeze_closed_autopilot_seed,
    seed_files,
    run_facts,
)


def _identity(copied):
    with closing(copied.storage.projects.open(copied.view.project_id)) as store, store.repository.engine.connect() as connection:
        claim = connection.exec_driver_sql("SELECT claim FROM v2_autopilot_runs").scalar_one()
        texts = connection.exec_driver_sql(
            "SELECT id,snapshot,receipt FROM v2_autopilot_exec_attempts WHERE domain='text' ORDER BY id"
        ).all()
    return claim, tuple(tuple(row) for row in texts)


def test_two_copies_keep_text_history_but_claim_and_continue_independently(
    tmp_path, monkeypatch, installed_text_prefix,
):
    seed = installed_text_prefix
    roots = [tmp_path / name for name in ("left", "right")]
    left = copy_installed_text_prefix(seed, roots[0], monkeypatch)
    right = None
    try:
        right = copy_installed_text_prefix(seed, roots[1], monkeypatch)
        for copied in (left, right):
            assert run_facts(copied.claim_view, exclude=("created_at", "updated_at")) == run_facts(
                copied.view, exclude=("created_at", "updated_at"))
        assert left.view.id == right.view.id == seed.run_id
        assert left.registry is not right.registry and left.service is not right.service
        assert left.registry._codex_exec_test_host is not right.registry._codex_exec_test_host
        assert left.service.claim != right.service.claim
        for copied in (left, right):
            claim, texts = _identity(copied)
            assert claim == copied.service.claim and texts == seed.text_records
            assert not copied.text_calls and not copied.image_calls
            assert not copied.registry._codex_exec_test_host.statuses
        for relative, _digest in seed.project.files:
            files = [root / relative for root in (seed.project.root, *roots)]
            assert len({(path.stat().st_dev, path.stat().st_ino) for path in files}) == 3
        # A live destination owns its controller lease; it cannot become a seed.
        with pytest.raises(ValueError, match="active resources"):
            freeze_closed_autopilot_seed(roots[0], seed.project.project_id, seed.project.home_name)
        results = []
        for copied in (left, right):
            copied.registry._codex_exec_test_host.image_geometry = mismatch
            result = first_geometry_frame(copied.storage, copied.service, copied.view)
            assert len(copied.image_calls) == 3 and not copied.text_calls
            assert len(result.frames) == 1 and result.frames[0].geometry_preparation is not None
            assert _identity(copied)[1] == seed.text_records
            with closing(copied.storage.projects.open(result.project_id)) as store:
                with store.repository.engine.connect() as connection:
                    images = connection.exec_driver_sql(
                        "SELECT id,job_id,receipt FROM v2_autopilot_exec_attempts WHERE domain='image'"
                    ).all()
                assert len(images) == 3 and all(row.receipt is not None for row in images)
                assert {row.job_id for row in images} == set(copied.image_calls)
            results.append((result, images))
        assert set(left.image_calls).isdisjoint(right.image_calls)
        assert {row.id for row in results[0][1]}.isdisjoint(row.id for row in results[1][1])
        a, b = (item[0].frames[0].geometry_preparation for item in results)
        assert a.source.asset.asset_id != b.source.asset.asset_id
        assert a.output.asset_id != b.output.asset_id
        assert a.preparation_hash != b.preparation_hash
        # Refusal uses a valid, ordinarily admitted post-cut project, not damaged evidence.
        left.service.close()
        later = freeze_closed_autopilot_seed(roots[0], seed.project.project_id, seed.project.home_name)
        with pytest.raises(ValueError, match="exact current installation cut|image/material review work"):
            copy_installed_text_prefix(replace(seed, project=later), tmp_path / "too-late", monkeypatch)
        right.service.close()
        right_files = seed_files(roots[1])
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
            pytest.fail("altered copy was admitted")
        assert seed_files(roots[1]) == right_files
        assert seed_files(seed.project.root) == seed.project.files
    finally:
        left.service.close()
        if right is not None:
            right.service.close()


def test_unresolved_text_history_is_refused_by_ordinary_admission(tmp_path, monkeypatch, installed_text_prefix):
    seed = installed_text_prefix
    root = tmp_path / "unresolved"
    storage, view = copy_closed_autopilot_seed(seed.project, root)
    with closing(storage.projects.open(view.project_id)) as store:
        database = store.database_path
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE v2_autopilot_exec_attempts SET state='running'")
    altered = freeze_closed_autopilot_seed(root, seed.project.project_id, seed.project.home_name)
    with pytest.raises(ProjectStorageCorruptionError):
        copy_installed_text_prefix(replace(seed, project=altered), tmp_path / "refused", monkeypatch)
    assert seed_files(seed.project.root) == seed.project.files


@pytest.mark.parametrize("member", ["package", "input", "report", "completion"])
def test_retained_package_and_delivery_bytes_are_bound_before_freezing(
    tmp_path, monkeypatch, installed_text_prefix, member,
):
    seed = installed_text_prefix
    root = tmp_path / "altered-evidence"
    storage, view = copy_closed_autopilot_seed(seed.project, root)
    with closing(storage.projects.open(view.project_id)) as store:
        job = store.creative_handoff_exchange().root / "jobs" / next(
            item["evidence"]["jobId"] for item in view.checkpoints if item["operationKey"] == "characters")
    if member == "completion":
        (job / "delivery/completion.json").unlink()
    else:
        path = (next((job / "package/inputs").iterdir()) if member == "input"
                else job / ("package/request.json" if member == "package" else "delivery/report.html"))
        path.write_bytes(path.read_bytes() + b"\n")
    altered = freeze_closed_autopilot_seed(root, seed.project.project_id, seed.project.home_name)
    # The bytes are physically quiescent and ordinary SQL admission succeeds.
    # Eligibility must still invoke the retained-evidence owner, not bless hashes
    # calculated after corruption or waive missing exported evidence.
    with pytest.raises(ProjectStorageCorruptionError):
        copy_installed_text_prefix(replace(seed, project=altered), tmp_path / "refused", monkeypatch)
    assert seed_files(seed.project.root) == seed.project.files


@pytest.mark.parametrize("nondefault", ["brief", "policy"])
def test_valid_nondefault_inputs_are_not_prefix_eligible(tmp_path, monkeypatch, nondefault):
    options = ({"brief": default_brief().model_copy(update={"aspect_ratio": "9:16"})}
               if nondefault == "brief" else {"limits": {"max_images": 79}})
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, **options)
    try:
        installed = run_text(service, view)
        assert installed.state == "running" and installed.phase == "references" and len(calls) == 8
        with closing(storage.projects.open(view.project_id)) as store, pytest.raises(
            ValueError, match="unchanged default Brief|unchanged default policy",
        ):
            assert_installed_text_boundary(store, registry)
    finally:
        service.close()
