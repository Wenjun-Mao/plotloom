"""Small SQLite provenance graph for profile-construction boundary tests only."""
import json
from dataclasses import dataclass
from uuid import UUID, uuid5

from plotloom.autopilot_contracts import CheckpointEvidence, LaunchPolicy, MachineDecision
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import request_hash
from plotloom.persistence.codec import stable_hash
from tests.codex_exec_fixtures import PROFILE

RUN_ID = "11111111-1111-4111-8111-111111111111"
PROJECT_ID = "22222222-2222-4222-8222-222222222222"
PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}

# Only columns read by the real validators are needed; no product schema changes.
SCHEMA = {
    "v2_autopilot_runs": "id,project_id,policy,policy_hash,brief_hash,state,bundle,bundle_hash,handoff",
    "v2_autopilot_checkpoints": "id,run_id,project_id,operation_key,state,evidence",
    "v2_autopilot_exec_attempts": "id,run_id,project_id,operation_key,job_id,domain,state,image_budget_state,reserved_image_outputs,snapshot,receipt",
    "v2_autopilot_decisions": "id,run_id,project_id,scope,checkpoint_id,decision",
    "v2_autopilot_frames": "run_id,project_id,shot_id,job_id,asset_id,decision_id,frame",
    "v2_autopilot_handoffs": "id,run_id,project_id,approval_id,receipt,receipt_hash",
    "v2_source_outline_candidates": "job_id,project_id,request,manifest_hash",
    "v2_creative_handoff_execution_pins": "job_id,project_id,stage,request_hash,execution_pin",
    "v2_production_bridge_revisions": "project_id,revision,content_hash,inputs,proposal,conflicts",
    "v2_approval_decisions": "id,reviewer",
    "v2_same_person_reviews": "id,reviewer",
}


@dataclass
class ProfileGraph:
    run_id: str
    project_id: str
    checkpoint_id: str
    policy: LaunchPolicy
    evidence: CheckpointEvidence
    attempt: CodexExecAttempt


def insert(connection, table, **values):
    columns = ",".join(values)
    placeholders = ",".join("?" for _ in values)
    connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))


def seed_profile_graph(connection, *, run_id=RUN_ID, project_id=PROJECT_ID, profile=PROFILE):
    for table, columns in SCHEMA.items():
        connection.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
    policy = LaunchPolicy(version="plotloom.pre-video.v4", render_style="live-action",
        art_render_style="live-action", code_revision="d" * 40, image_width=1280,
        image_height=720, executor_binding=profile, execution_pins={"outline": PIN},
        brief=FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=False))
    job_id = "ch_" + UUID(run_id).hex
    request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="opening",
        stage="outline", expected_stage_revision=0, source={"text": "One frozen source."},
        creative_brief="Preserve the exact frozen source.")
    plan_hash = (build_text_validation_plan(request, execution_pin=PIN,
        source_revision=policy.code_revision).plan_hash
        if profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"} else None)
    attempt = CodexExecAttempt(attempt_id=uuid5(UUID(run_id), "attempt"), run_id=run_id,
        project_id=project_id, job_id=job_id, operation_key="outline", domain="text",
        request_hash=request_hash(request), package_hash="e" * 64,
        profile_hash=profile.profile_hash, plotloom_code_revision=policy.code_revision,
        validation_plan_hash=plan_hash, reserved_image_outputs=0, state="reserved")
    evidence = CheckpointEvidence(owner="outline", subject_id=job_id, job_id=job_id,
        request_hash=attempt.request_hash, execution_pin=PIN, executor_attempt_id=attempt.attempt_id)
    checkpoint_id = str(uuid5(UUID(run_id), "checkpoint"))
    raw_policy = policy.model_dump(mode="json", by_alias=True)
    insert(connection, "v2_autopilot_runs", id=run_id, project_id=project_id,
        policy=json.dumps(raw_policy), policy_hash=stable_hash(raw_policy),
        brief_hash=stable_hash(policy.brief), state="running")
    insert(connection, "v2_autopilot_checkpoints", id=checkpoint_id, run_id=run_id,
        project_id=project_id, operation_key="outline", state="prepared",
        evidence=evidence.model_dump_json(by_alias=True))
    insert(connection, "v2_autopilot_exec_attempts", id=str(attempt.attempt_id), run_id=run_id,
        project_id=project_id, operation_key="outline", job_id=job_id, domain="text",
        state="reserved", image_budget_state="none", reserved_image_outputs=0,
        snapshot=attempt.model_dump_json(by_alias=True))
    decision = MachineDecision(scope="text_adoption", policy_hash=stable_hash(raw_policy),
        subject={}, upstream_hash="f" * 64, evidence=evidence, rationale="Bounded provenance fixture.")
    insert(connection, "v2_autopilot_decisions", id=str(uuid5(UUID(run_id), "decision")),
        run_id=run_id, project_id=project_id, scope=decision.scope.value,
        checkpoint_id=checkpoint_id, decision=decision.model_dump_json(by_alias=True))
    insert(connection, "v2_source_outline_candidates", job_id=job_id, project_id=project_id,
        request=request.model_dump_json(by_alias=True))
    insert(connection, "v2_creative_handoff_execution_pins", job_id=job_id,
        project_id=project_id, stage="outline", request_hash=attempt.request_hash,
        execution_pin=json.dumps(PIN))
    connection.commit()
    return ProfileGraph(run_id, project_id, checkpoint_id, policy, evidence, attempt)


def observe_constructions(monkeypatch):
    from plotloom.codex_exec_contracts import CodexExecProfile
    calls, original = [], CodexExecProfile.model_validate

    def validate(cls, value, **options):
        calls.append(value)
        return original(value, **options)

    monkeypatch.setattr(CodexExecProfile, "model_validate", classmethod(validate))
    return calls
