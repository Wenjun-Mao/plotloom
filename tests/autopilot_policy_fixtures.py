"""Small current-request SQLite graph for policy-decode binding guards only."""
import json
from types import SimpleNamespace
from uuid import UUID, uuid5

from plotloom.autopilot_contracts import CheckpointEvidence, LaunchPolicy
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecProfile
from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_exchange import request_hash
from tests.autopilot_controller_fixtures import UPSTREAM_PIN
from tests.codex_exec_fixtures import PROFILE
from tests.source_outline_fixtures import _material, _request

RUN_ID = "11111111-1111-4111-8111-111111111111"
PROJECT_ID = "22222222-2222-4222-8222-222222222222"
SCHEMA = {
    "v2_autopilot_inheritance": "run_id,operation_key,origin_checkpoint_id,evidence_hash,project_id",
    "v2_autopilot_runs": "id,project_id,policy",
    "v2_autopilot_exec_attempts": "id,run_id,project_id,operation_key,job_id,domain,state,image_budget_state,reserved_image_outputs,snapshot,receipt",
    "v2_source_outline_candidates": "job_id,project_id,request,manifest_hash",
    "v2_creative_handoff_execution_pins": "job_id,project_id,stage,request_hash,execution_pin",
}


def versioned_profile(version):
    value = PROFILE.model_dump(mode="json", by_alias=True)
    value.update(contractVersion=f"plotloom.codex-exec.v{version}", maxProcesses=1)
    for name in ("maxTextProcesses", "maxImageProcesses", "maxQueuedJobs"):
        value.pop(name, None)
    permission = {5: 3, 6: 4, 7: 5, 8: 5}[version]
    value["permissionProfile"] = f"plotloom_autopilot_delivery_v{permission}"
    value["textValidatorRuntimeProfile"] = {
        5: "node_openssl_and_private_zsh_tmp_v1",
        6: "node_openssl_private_zsh_tmp_and_validator_aliases_v2",
        7: "node_openssl_private_zsh_tmp_and_checked_python_v3",
        8: "node_openssl_private_zsh_tmp_and_checked_python_v3",
    }[version]
    if version == 8:
        value.update(maxTextProcesses=1, maxImageProcesses=1, maxQueuedJobs=1)
    return CodexExecProfile.model_validate(value)


def seed_text_graph(connection, *, version):
    """Real current binding/plan validators; no stubbed validator or live host."""
    for table, columns in SCHEMA.items():
        connection.execute(f"CREATE TABLE {table} ({columns})")
    profile = versioned_profile(version)
    policy = LaunchPolicy(version="plotloom.pre-video.v4", render_style="live-action",
        art_render_style="live-action", code_revision="d" * 40, image_width=1280,
        image_height=720, executor_binding=profile, execution_pins={"outline": UPSTREAM_PIN},
        brief=FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=False))
    request = _request(PROJECT_ID, _material())
    plan_hash = (build_text_validation_plan(request, execution_pin=UPSTREAM_PIN,
        source_revision=policy.code_revision).plan_hash if version >= 6 else None)
    attempt = CodexExecAttempt(attempt_id=uuid5(UUID(RUN_ID), "attempt"), run_id=RUN_ID,
        project_id=PROJECT_ID, job_id=request.job_id, operation_key="outline", domain="text",
        request_hash=request_hash(request), package_hash="e" * 64,
        profile_hash=profile.profile_hash, plotloom_code_revision=policy.code_revision,
        validation_plan_hash=plan_hash, reserved_image_outputs=0, state="reserved")
    evidence = CheckpointEvidence(owner="outline", subject_id=request.job_id, job_id=request.job_id,
        request_hash=attempt.request_hash, execution_pin=UPSTREAM_PIN, executor_attempt_id=attempt.attempt_id)

    def insert(table, **values):
        columns = ",".join(values)
        placeholders = ",".join("?" for _ in values)
        connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))

    insert("v2_autopilot_runs", id=RUN_ID, project_id=PROJECT_ID, policy=policy.model_dump_json(by_alias=True))
    insert("v2_autopilot_exec_attempts", id=str(attempt.attempt_id), run_id=RUN_ID,
        project_id=PROJECT_ID, operation_key="outline", job_id=request.job_id, domain="text",
        state="reserved", image_budget_state="none", reserved_image_outputs=0,
        snapshot=attempt.model_dump_json(by_alias=True))
    insert("v2_source_outline_candidates", job_id=request.job_id, project_id=PROJECT_ID,
        request=request.model_dump_json(by_alias=True))
    insert("v2_creative_handoff_execution_pins", job_id=request.job_id, project_id=PROJECT_ID,
        stage="outline", request_hash=attempt.request_hash, execution_pin=json.dumps(UPSTREAM_PIN))
    connection.commit()
    return SimpleNamespace(run_id=RUN_ID, project_id=PROJECT_ID, evidence=evidence,
        state="prepared", operation_key="outline")
