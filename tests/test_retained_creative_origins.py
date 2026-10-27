"""Snapshot inventory binds inherited jobs to their exact original authority."""
import json
import sqlite3
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import CheckpointEvidence, LaunchPolicy
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.persistence.codec import stable_hash
from plotloom.project_storage import ProjectStorageCorruptionError
from plotloom.project_storage.creative_evidence_inventory import _codex_creative_jobs
from tests.codex_exec_fixtures import PROFILE


@pytest.fixture
def retained_origin():
    connection = sqlite3.connect(":memory:")
    for sql in (
        "CREATE TABLE v2_autopilot_runs(id,project_id,predecessor_run_id,policy)",
        "CREATE TABLE v2_autopilot_checkpoints(id,run_id,project_id,operation_key,state,evidence)",
        "CREATE TABLE v2_autopilot_inheritance(run_id,operation_key,origin_checkpoint_id,evidence_hash,project_id)",
        "CREATE TABLE v2_autopilot_exec_attempts(run_id,project_id,operation_key,job_id,snapshot,receipt)",
    ):
        connection.execute(sql)
    project, parent, child = (str(uuid4()) for _ in range(3))
    policy = LaunchPolicy(version="plotloom.pre-video.v4", max_images=None, max_jobs=None,
        render_style="live-action", art_render_style="live-action", code_revision="a" * 40,
        image_width=1280, image_height=720, executor_binding=PROFILE,
        execution_pins={"image": {"contract": "codex_exec.v1"}}, brief={})
    successor = policy.model_copy(update={"code_revision": "b" * 40,
        "executor_binding": PROFILE.model_copy(update={"instruction_hash": "d" * 64})})
    for run, predecessor, frozen in ((parent, None, policy), (child, parent, successor)):
        connection.execute("INSERT INTO v2_autopilot_runs VALUES(?,?,?,?)",
            (run, project, predecessor, frozen.model_dump_json(by_alias=True)))
    evidence = CheckpointEvidence(owner="storyboard", subject_id="opening", job_id="ch_" + "a" * 20)
    for checkpoint, run in (("parent-checkpoint", parent), ("child-checkpoint", child)):
        connection.execute("INSERT INTO v2_autopilot_checkpoints VALUES(?,?,?,?,?,?)",
            (checkpoint, run, project, "storyboard", "adopted", evidence.model_dump_json(by_alias=True)))
    connection.execute("INSERT INTO v2_autopilot_inheritance VALUES(?,?,?,?,?)",
        (child, "storyboard", "parent-checkpoint", stable_hash(evidence.model_dump(mode="json", by_alias=True)), project))
    attempt = CodexExecAttempt(attempt_id=uuid4(), run_id=parent, project_id=project,
        operation_key="storyboard", job_id=evidence.job_id, domain="text", request_hash="a" * 64,
        package_hash="b" * 64, profile_hash=PROFILE.profile_hash, plotloom_code_revision=policy.code_revision,
        state="reserved", reserved_image_outputs=0)
    connection.execute("INSERT INTO v2_autopilot_exec_attempts VALUES(?,?,?,?,?,?)",
        (parent, project, "storyboard", evidence.job_id, attempt.model_dump_json(by_alias=True), None))
    yield connection, project, parent, child, policy, evidence, attempt
    connection.close()


def test_inherited_references_coalesce_only_to_exact_origin_policy(retained_origin):
    connection, project, parent, child, policy, evidence, attempt = retained_origin
    original = list(connection.iterdump())
    binding = _codex_creative_jobs(connection)[evidence.job_id]
    assert binding["run_id"] == parent != child
    assert binding["project_id"] == project
    assert binding["profile"] == policy.executor_binding
    assert binding["plotloom_code_revision"] == policy.code_revision
    assert binding["attempt"] == attempt
    assert list(connection.iterdump()) == original
    # SQL row order cannot decide the owner.
    connection.execute("UPDATE v2_autopilot_checkpoints SET id='z-parent' WHERE id='parent-checkpoint'")
    connection.execute("UPDATE v2_autopilot_inheritance SET origin_checkpoint_id='z-parent'")
    assert _codex_creative_jobs(connection)[evidence.job_id] == binding


@pytest.mark.parametrize("mutation", ["missing-link", "missing-origin", "malformed-evidence", "hash",
    "foreign-project", "wrong-operation", "unadopted", "wrong-predecessor", "cycle"])
def test_inherited_origin_corruption_never_rebinds_to_child(retained_origin, mutation):
    connection, project, parent, child, _policy, evidence, _attempt = retained_origin
    if mutation == "missing-link":
        connection.execute("DELETE FROM v2_autopilot_inheritance")
    elif mutation == "missing-origin":
        connection.execute("DELETE FROM v2_autopilot_checkpoints WHERE id='parent-checkpoint'")
    elif mutation == "malformed-evidence":
        connection.execute("UPDATE v2_autopilot_checkpoints SET evidence='{}' WHERE id='child-checkpoint'")
    elif mutation == "hash":
        connection.execute("UPDATE v2_autopilot_inheritance SET evidence_hash=?", ("f" * 64,))
    elif mutation == "foreign-project":
        connection.execute("UPDATE v2_autopilot_inheritance SET project_id=?", (str(uuid4()),))
    elif mutation == "wrong-operation":
        connection.execute("UPDATE v2_autopilot_checkpoints SET operation_key='script' WHERE id='parent-checkpoint'")
    elif mutation == "unadopted":
        connection.execute("UPDATE v2_autopilot_checkpoints SET state='prepared' WHERE id='parent-checkpoint'")
    elif mutation == "wrong-predecessor":
        connection.execute("UPDATE v2_autopilot_runs SET predecessor_run_id=? WHERE id=?", (str(uuid4()), child))
    else:
        connection.execute("UPDATE v2_autopilot_runs SET predecessor_run_id=? WHERE id=?", (child, parent))
        connection.execute("INSERT INTO v2_autopilot_inheritance VALUES(?,?,?,?,?)",
            (parent, "storyboard", "child-checkpoint", stable_hash(evidence.model_dump(mode="json", by_alias=True)), project))
    with pytest.raises((ProjectStorageCorruptionError, ValueError)):
        _codex_creative_jobs(connection)


@pytest.mark.parametrize("same_authority", [False, True])
def test_unrelated_duplicate_job_refused_even_with_identical_profile_and_source(retained_origin, same_authority):
    connection, project, parent, child, policy, evidence, _attempt = retained_origin
    unrelated = str(uuid4())
    frozen = policy if same_authority else policy.model_copy(update={"code_revision": "c" * 40})
    connection.execute("INSERT INTO v2_autopilot_runs VALUES(?,?,?,?)",
        (unrelated, project, None, frozen.model_dump_json(by_alias=True)))
    connection.execute("INSERT INTO v2_autopilot_checkpoints VALUES(?,?,?,?,?,?)",
        ("unrelated-checkpoint", unrelated, project, "storyboard", "adopted", evidence.model_dump_json(by_alias=True)))
    with pytest.raises(ProjectStorageCorruptionError, match="conflicting origin owners"):
        _codex_creative_jobs(connection)


@pytest.mark.parametrize("difference", ["row-run", "snapshot-run", "profile", "source", "operation"])
def test_attempt_must_bind_original_run_not_merely_equal_profile(retained_origin, difference):
    connection, _project, parent, child, _policy, _evidence, attempt = retained_origin
    value = json.loads(attempt.model_dump_json(by_alias=True))
    if difference == "row-run":
        connection.execute("UPDATE v2_autopilot_exec_attempts SET run_id=?", (child,))
    else:
        field, changed = {"snapshot-run": ("runId", child), "profile": ("profileHash", "f" * 64),
            "source": ("plotloomCodeRevision", "f" * 40), "operation": ("operationKey", "script")}[difference]
        value[field] = changed
        connection.execute("UPDATE v2_autopilot_exec_attempts SET snapshot=?", (json.dumps(value),))
    with pytest.raises(ProjectStorageCorruptionError):
        _codex_creative_jobs(connection)
