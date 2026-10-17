"""Shared closed-installation history and fresh runtime claims, without eligibility dispatch."""
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC

from plotloom.autopilot_contracts import LaunchRequest
from plotloom.autopilot_launch import CREATIVE_STAGES, freeze_launch_policy
from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from plotloom.project_storage.creative_evidence_inventory import creative_evidence_paths
from tests.autopilot_handoff_seed_fixtures import assert_no_human_facts
from tests.autopilot_seed_fixtures import ClosedAutopilotSeed


@dataclass(frozen=True)
class InstalledTextPrefix:
    project: ClosedAutopilotSeed
    run_id: str
    policy_text: str
    text_records: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class InstalledTextCopy:
    storage: object
    registry: object
    service: object
    claim_view: object
    view: object
    image_calls: list
    text_calls: list


def installed_text_view(store):
    view = store.repository.autopilot.current(store.manifest.project_id)
    if view is None or (view.state, view.phase) != ("running", "references") or not view.material_current:
        raise ValueError("installed-text prefix requires the exact current installation cut")
    if view.frames or view.bundle is not None or view.bundle_hash is not None or view.handoff is not None:
        raise ValueError("installed-text prefix cannot contain image/material review work")
    return view


def focused_installation_policy(store, registry):
    expected = freeze_launch_policy(store, registry, LaunchRequest(
        expected_brief_revision=1, render_style="realistic", art_render_style="realistic"))
    return expected.model_copy(update={"early_reference_limit": 0})


def installed_text_history(store, view):
    checkpoints = {item["operationKey"]: item for item in view.checkpoints}
    if set(checkpoints) != {"source", "bridge.prepare", "installation", *CREATIVE_STAGES}:
        raise ValueError("installed-text prefix cannot contain inventory/image/geometry checkpoints")
    if any(item["state"] != "adopted" for item in checkpoints.values()):
        raise ValueError("installed-text prefix requires completed adopted text/installation history")
    assert_no_human_facts(store)
    # This owner binds confined retained package/input/output/completion bytes
    # to their original requests, attempts and receipts. No restored omissions.
    evidence = creative_evidence_paths(store.home, store.database_path, prior_snapshot_omissions={})
    completed_jobs = {path.parts[3] for path in evidence if path.parts[-2:] == ("delivery", "completion.json")}
    with store.repository.engine.connect() as connection:
        for table in ("v2_image_jobs", "v2_character_reference_proposals", "v2_art_reference_proposals",
                      "v2_autopilot_frames", "v2_production_units", "v2_managed_asset_provenance"):
            if connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar():
                raise ValueError("installed-text prefix cannot contain image/reference/geometry work")
        for table in ("v2_source_outline_source_revisions", "v2_production_bridge_revisions",
                      "v2_production_bridge_admissions"):
            if not connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar():
                raise ValueError("installed-text prefix lacks source/Bridge installation history")
        rows = connection.exec_driver_sql(
            "SELECT id,snapshot,receipt FROM v2_autopilot_exec_attempts ORDER BY id").all()
        if len(rows) != 8:
            raise ValueError("installed-text prefix requires exactly eight text attempts")
        expected_jobs = set()
        for identifier, snapshot, raw_receipt in rows:
            attempt = CodexExecAttempt.model_validate_json(snapshot)
            receipt = CodexExecReceipt.model_validate_json(raw_receipt)
            if (attempt.domain != "text" or attempt.state not in {"completed", "settled"}
                    or attempt.terminal_result != "success" or attempt.image_budget_state != "none"
                    or attempt.reserved_image_outputs != 0):
                raise ValueError("installed-text prefix has unresolved or non-text work")
            assert_receipt_matches_attempt(attempt, receipt)
            expected_jobs.add(attempt.job_id)
            checkpoint = checkpoints[attempt.operation_key]
            if checkpoint["evidence"]["executorAttemptId"] != identifier:
                raise ValueError("installed-text prefix text identity differs")
        if completed_jobs != expected_jobs or len(expected_jobs) != 8:
            raise ValueError("installed-text prefix requires eight complete retained native jobs")
        decision_ids = set(connection.exec_driver_sql(
            "SELECT checkpoint_id FROM v2_autopilot_decisions").scalars())
        if not {checkpoints[key]["id"] for key in (*CREATIVE_STAGES, "installation")} <= decision_ids:
            raise ValueError("installed-text prefix lacks retained text/installation decisions")
        policy_text = connection.exec_driver_sql(
            "SELECT policy FROM v2_autopilot_runs WHERE id=?", (str(view.id),)).scalar_one()
    return view, policy_text, tuple(tuple(row) for row in rows)



def claim_installed_text_copy(storage, registry, service, host, before):
    assert not host.calls and not host.image_calls and not host.statuses and not host.pending
    assert host.admissions == 0 and not registry.view()["busy"]
    assert service.acquire_controller()
    with closing(storage.projects.open(before.project_id)) as store:
        claimed = store.repository.autopilot.claim(before.project_id, service.claim)
        current = store.repository.autopilot.current(before.project_id)
        # claim() returns the live UTC timestamps; SQLite's following read
        # returns naive UTC. Keep both actual views and compare their same
        # persisted meaning without changing production timestamp behavior.
        times = {"created_at", "updated_at"}
        assert claimed.model_dump(exclude=times) == current.model_dump(exclude=times)
        for field in times:
            assert getattr(claimed, field).replace(tzinfo=UTC) == getattr(current, field).replace(tzinfo=UTC)
        assert current.id == before.id and current.revision > before.revision
    return InstalledTextCopy(storage, registry, service, claimed, current, host.image_calls, host.calls)
