"""View-local derivations retain real SQL, typed validation and failure order."""
import json
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from plotloom.autopilot_contracts import (
    CheckpointEvidence,
    LaunchPolicy,
    ProvisionalFrame,
)
from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project import autopilot
from plotloom.persistence.schema import (
    AutopilotCheckpointRow,
    AutopilotExecAttemptRow,
    AutopilotFrameRow,
)
from tests.codex_exec_fixtures import PROFILE

RUN = "11111111-1111-4111-8111-111111111111"
PROJECT = "22222222-2222-4222-8222-222222222222"
JOB = "ch_" + UUID(RUN).hex
NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def geometry_payload():
    asset = {"assetId": "asset", "originalHash": "a" * 64, "width": 1280, "height": 720}
    recipe = {"version": "center-cover-rgb-lanczos-png.v1", "exifOrientation": 1,
        "orientedWidth": 1280, "orientedHeight": 720, "cropBox": [0.0, 0.0, 1280.0, 720.0],
        "targetWidth": 1280, "targetHeight": 720}
    payload = {"version": "geometry-preparation.v1", "preparationId": "b" * 64,
        "projectId": PROJECT, "runId": RUN, "policyHash": "c" * 64, "claim": "controller",
        "shotId": "shot", "source": {"asset": asset, "checkpointId": "checkpoint",
            "decisionId": "decision", "candidateId": "candidate", "jobId": "job",
            "requestHash": "d" * 64, "deliveryRowId": "delivery-row", "deliveryId": "delivery",
            "manifestHash": "e" * 64, "executionPin": {"contract": "fixture"}},
        "recipe": recipe, "recipeHash": stable_hash(recipe),
        "runtime": {"pillowVersion": "fixture", "transformHash": "f" * 64}, "output": asset}
    return payload | {"preparationHash": stable_hash(payload)}


@pytest.fixture
def view_context(monkeypatch):
    # Only the three queried tables are needed here; real storage/authority owners
    # below this boundary are covered by the separately selected integration files.
    engine = create_engine("sqlite://")
    for model in (AutopilotCheckpointRow, AutopilotExecAttemptRow, AutopilotFrameRow):
        model.__table__.create(engine)
    policy = LaunchPolicy(version="plotloom.pre-video.v4", render_style="live-action",
        art_render_style="live-action", image_width=1280, image_height=720,
        code_revision="a" * 40, executor_binding=PROFILE, execution_pins={},
        brief=FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=False))
    row = SimpleNamespace(id=RUN, project_id=PROJECT, revision=1, state="running",
        phase="outline", expected_closure="closure", policy=policy.model_dump(mode="json", by_alias=True),
        blocker=None, bundle=None, bundle_hash=None, handoff=None, created_at=NOW, updated_at=NOW)
    attempt = CodexExecAttempt(attempt_id=UUID("33333333-3333-4333-8333-333333333333"),
        run_id=RUN, project_id=PROJECT, job_id=JOB, operation_key="outline", domain="text",
        request_hash="1" * 64, package_hash="2" * 64, profile_hash=PROFILE.profile_hash,
        reserved_image_outputs=0, state="queued")
    evidence = [CheckpointEvidence(owner="outline", subject_id="outline", job_id=JOB,
                    executor_attempt_id=attempt.attempt_id, result={"nested": ["初稿", None, {"count": 2}]}),
        CheckpointEvidence(owner="source", subject_id="no-job"),
        CheckpointEvidence(owner="geometry-preparation", subject_id="geometry", job_id="geometry-job",
            geometry_preparation=geometry_payload())]
    frame = dict(shotId="shot", sceneId="scene", jobId="image-job", assetId="asset",
        originalHash="a" * 64, storyboardRevision=1, storyboardHash="b" * 64,
        requestHash="c" * 64, width=1280, height=720, characterIdentity=[])
    with Session(engine) as session:
        checkpoints = [AutopilotCheckpointRow(id=str(index), run_id=RUN, project_id=PROJECT,
            operation_key=key, revision=1, state="sent", evidence=value.model_dump(mode="json", by_alias=True),
            created_at=NOW, updated_at=NOW) for index, (key, value) in enumerate(
                zip(("outline", "source", "geometry"), evidence))]
        retained_attempt = AutopilotExecAttemptRow(id=str(attempt.attempt_id), run_id=RUN, project_id=PROJECT,
            operation_key="outline", job_id=attempt.job_id, domain="text", state="queued",
            image_budget_state="none", reserved_image_outputs=0, revision=1,
            snapshot=attempt.model_dump(mode="json", by_alias=True), receipt=None, created_at=NOW, updated_at=NOW)
        retained_frame = AutopilotFrameRow(id="frame", run_id=RUN, project_id=PROJECT, shot_id="shot",
            job_id="image-job", asset_id="asset", decision_id="decision", frame=frame, created_at=NOW)
        session.add_all([*checkpoints, retained_attempt, retained_frame])
        session.flush()
        events, queries = [], []

        def closure(current, project):
            assert current is session and project == PROJECT
            events.append("closure")
            current.flush()
            return "closure"

        monkeypatch.setattr(autopilot, "material_closure", closure)
        owner = autopilot.AutopilotPersistence(None, claim_write=None)
        yield SimpleNamespace(owner=owner, session=session, row=row, events=events, queries=queries,
            checkpoints=checkpoints, attempt=retained_attempt, frame=retained_frame,
            evidence=evidence, policy=policy, frame_payload=frame)
    engine.dispose()


def observe(context, monkeypatch):
    for model, label in ((LaunchPolicy, "policy"), (CheckpointEvidence, "parse"),
                         (CodexExecAttempt, "attempt"), (ProvisionalFrame, "frame")):
        original = model.model_validate

        def validate(cls, value, _original=original, _label=label, **options):
            suffix = ":" + value.get("subjectId", "missing") if _label == "parse" else ""
            context.events.append(_label + suffix)
            return _original(value, **options)

        monkeypatch.setattr(model, "model_validate", classmethod(validate))
    original_dump = CheckpointEvidence.model_dump

    def dump(value, **options):
        context.events.append("dump:" + value.subject_id)
        return original_dump(value, **options)

    monkeypatch.setattr(CheckpointEvidence, "model_dump", dump)
    original_scalars = Session.scalars

    def scalars(session, statement, *args, **kwargs):
        model = statement.column_descriptions[0]["entity"]
        context.events.append("select:" + model.__tablename__)
        context.queries.append((str(statement), statement.compile().params))
        return original_scalars(session, statement, *args, **kwargs)

    monkeypatch.setattr(Session, "scalars", scalars)
    original_activities = autopilot.run_activities

    def activities(*args):
        result = original_activities(*args)
        context.events.append("activities")
        return result

    monkeypatch.setattr(autopilot, "run_activities", activities)


def render(context):
    return context.owner.view_in_session(context.session, context.row)


PREFIX = ["select:v2_autopilot_checkpoints", "select:v2_autopilot_frames", "closure", "policy"]
# SQL orders by created_at and operation_key, rather than fixture insertion order.
PROJECTION = ["parse:geometry", "dump:geometry", "parse:outline", "dump:outline", "parse:no-job", "dump:no-job"]
SUCCESS = PREFIX + PROJECTION + ["select:v2_autopilot_exec_attempts", "attempt", "activities", "frame"]


def test_each_loaded_checkpoint_parses_once_and_keeps_canonical_output(view_context, monkeypatch):
    context = view_context
    expected = [{"id": row.id, "operationKey": row.operation_key, "revision": 1, "state": "sent",
        "evidence": evidence.model_dump(mode="json", by_alias=True)}
        for row, evidence in sorted(zip(context.checkpoints, context.evidence), key=lambda pair: pair[0].operation_key)]
    observe(context, monkeypatch)
    view = render(context)
    assert context.events == SUCCESS
    assert len(context.queries) == 3
    assert all(query[1] == {"run_id_1": RUN} for query in context.queries)
    canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert canonical(view.checkpoints) == canonical(expected)
    assert [item.model_dump(mode="json", by_alias=True) for item in view.activities] == [{
        "operationKey": "outline", "owner": "outline", "subjectId": "outline",
        "jobId": JOB, "domain": "text", "state": "queued"}]
    assert view.policy == context.policy and view.material_current
    assert view.frames[0].model_dump(mode="json", by_alias=True) == context.frame_payload


@pytest.mark.parametrize("failure", ["policy", "geometry", "checkpoint", "dump", "attempt", "frame"])
def test_failure_priority_and_failed_view_cannot_prime_next(view_context, monkeypatch, failure):
    context = view_context
    saved = deepcopy((context.row.policy, [row.evidence for row in context.checkpoints],
        context.attempt.snapshot, context.frame.frame))
    if failure == "policy":
        context.row.policy = {}
    elif failure == "geometry":
        context.checkpoints[2].evidence = context.checkpoints[2].evidence | {
            "geometryPreparation": geometry_payload() | {"preparationHash": "0" * 64}}
    elif failure == "checkpoint":
        context.checkpoints[0].evidence = {"subjectId": "outline"}
    elif failure == "attempt":
        context.attempt.snapshot = {}
    elif failure == "frame":
        context.frame.frame = {}
    observe(context, monkeypatch)
    original_dump = CheckpointEvidence.model_dump
    if failure == "dump":
        def fail_dump(value, **options):
            if value.subject_id == "geometry":
                context.events.append("dump:geometry")
                raise OSError("serialization failed")
            return original_dump(value, **options)
        monkeypatch.setattr(CheckpointEvidence, "model_dump", fail_dump)
    endpoint = {"policy": "policy", "geometry": "parse:geometry", "checkpoint": "parse:outline",
        "dump": "dump:geometry", "attempt": "attempt", "frame": "frame"}[failure]
    with pytest.raises(OSError if failure == "dump" else ValidationError):
        render(context)
    assert context.events == SUCCESS[:SUCCESS.index(endpoint) + 1]
    context.row.policy = saved[0]
    for row, evidence in zip(context.checkpoints, saved[1]):
        row.evidence = evidence
    context.attempt.snapshot, context.frame.frame = saved[2:]
    monkeypatch.setattr(CheckpointEvidence, "model_dump", original_dump)
    context.events.clear()
    assert render(context).activities[0].state == "queued"
    assert context.events == SUCCESS


def test_successive_views_reparse_changed_evidence_and_fresh_attempt_status(view_context, monkeypatch):
    context = view_context
    observe(context, monkeypatch)
    first = render(context)
    first_queries = context.queries[:]
    context.checkpoints[0].evidence = context.checkpoints[0].evidence | {"subjectId": "changed"}
    context.attempt.snapshot = context.attempt.snapshot | {"state": "running"}
    context.events.clear()
    second = render(context)
    assert context.events == [event.replace(":outline", ":changed") for event in SUCCESS]
    assert context.queries[3:] == first_queries
    assert first.activities[0].state == "queued" and first.activities[0].subject_id == "outline"
    assert second.activities[0].state == "generating" and second.activities[0].subject_id == "changed"
    assert first.checkpoints[1]["evidence"]["subjectId"] == "outline"
    assert second.checkpoints[1]["evidence"]["subjectId"] == "changed"


def test_reentrant_view_has_independent_derivations(view_context, monkeypatch):
    context = view_context
    observe(context, monkeypatch)
    original_dump = CheckpointEvidence.model_dump
    nested = []

    def dump(value, **options):
        if value.subject_id == "geometry" and not nested:
            nested.append(None)
            nested[0] = render(context)
        return original_dump(value, **options)

    monkeypatch.setattr(CheckpointEvidence, "model_dump", dump)
    outer = render(context)
    assert outer == nested[0]
    assert outer is not nested[0]
    assert context.events.count("parse:geometry") == context.events.count("parse:outline") == 2
    assert context.events.count("parse:no-job") == context.events.count("attempt") == 2
    assert len(context.queries) == 6
