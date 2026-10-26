"""Nullable aggregate policy preserves finite authority and safe admission."""
from contextlib import closing
from dataclasses import asdict, replace
import json
import sqlite3

import pytest
from pydantic import ValidationError

from plotloom.autopilot_contracts import LaunchPolicy, LaunchRequest
from plotloom.delegated_qa import SCOPES
from plotloom.persistence.codec import stable_hash
from plotloom.provider_budgets import budget_within_authority, exceeds_budget
from plotloom.video_batch_contracts import BatchControl, BatchSetup
from tests.autopilot_profile_fixtures import SCHEMA, insert
from tests.codex_exec_fixtures import PROFILE
from tests.test_autopilot_brief_style import _policy
from tests.video_batch_fixtures import batch_environment


def frozen_policy(version):
    value = _policy(authority="preset").model_dump(mode="json", by_alias=True)
    value["version"] = f"plotloom.pre-video.v{version}"
    if version == 1:
        value["geometryPreparation"] = None
    if version == 4:
        value.pop("specialistBindings")
        value["executorBinding"] = PROFILE.model_dump(mode="json", by_alias=True)
    return LaunchPolicy.model_validate(value).model_dump(mode="json", by_alias=True)


def policy_database(connection, policy):
    # Existing portable-admission fixture schema, with no jobs or provider work.
    for table, columns in SCHEMA.items():
        connection.execute(f"CREATE TABLE {table} ({columns})")
    insert(connection, "v2_autopilot_runs", id="frozen-run", project_id="test-project",
        policy=json.dumps(policy), policy_hash=stable_hash(policy),
        brief_hash=stable_hash(policy["brief"]), state="paused")


@pytest.mark.parametrize("version", [1, 2, 3, 4])
@pytest.mark.parametrize("missing", [("maxImages",), ("maxJobs",), ("maxImages", "maxJobs")])
def test_frozen_policy_rejects_missing_caps_even_with_matching_raw_hash(version, missing):
    from plotloom.project_storage.autopilot_validation import assert_autopilot_contracts
    from plotloom.project_storage.format import ProjectStorageCorruptionError
    policy = frozen_policy(version)
    for key in missing:
        policy.pop(key)
    with pytest.raises(ValidationError) as direct:
        LaunchPolicy.model_validate(policy)
    assert {item["loc"][0] for item in direct.value.errors()} == set(missing)
    with closing(sqlite3.connect(":memory:")) as connection:
        policy_database(connection, policy)
        before = connection.execute("SELECT policy,policy_hash FROM v2_autopilot_runs").fetchone()
        with pytest.raises(ProjectStorageCorruptionError, match="persisted autopilot authority") as corrupt:
            assert_autopilot_contracts(connection)
        assert isinstance(corrupt.value.__cause__, ValidationError)
        assert connection.execute("SELECT policy,policy_hash FROM v2_autopilot_runs").fetchone() == before


@pytest.mark.parametrize("version", [1, 2, 3, 4])
@pytest.mark.parametrize("caps", [(None, None), (80, 96)])
def test_frozen_explicit_policy_caps_admit_without_changing_hash(version, caps):
    from plotloom.project_storage.autopilot_validation import assert_autopilot_contracts
    policy = frozen_policy(version) | {"maxImages": caps[0], "maxJobs": caps[1]}
    assert LaunchPolicy.model_validate(policy).model_dump(mode="json", by_alias=True) == policy
    with closing(sqlite3.connect(":memory:")) as connection:
        policy_database(connection, policy)
        before = connection.execute("SELECT policy,policy_hash FROM v2_autopilot_runs").fetchone()
        assert_autopilot_contracts(connection)
        assert connection.execute("SELECT policy,policy_hash FROM v2_autopilot_runs").fetchone() == before


@pytest.mark.parametrize("missing", [("maxJobs",), ("maxRequestedSeconds",), ("maxJobs", "maxRequestedSeconds")])
def test_frozen_batch_rejects_missing_caps_even_with_matching_raw_hash(tmp_path, missing):
    from plotloom.project_storage.video_batch_validation import assert_video_batch_contracts
    from plotloom.project_storage.format import ProjectStorageCorruptionError
    storage, client, service, provider, project, view = batch_environment(tmp_path)
    with closing(storage.projects.open(project)) as store, store.repository.engine.begin() as session:
        connection = session.connection.driver_connection
        manifest = view["manifest"]
        for key in missing:
            manifest["setup"].pop(key)
        connection.execute("UPDATE v2_video_batches SET manifest=?,manifest_hash=? WHERE id=?",
            (json.dumps(manifest), stable_hash(manifest), view["id"]))
        before = connection.execute("SELECT manifest,manifest_hash FROM v2_video_batches").fetchone()
        with pytest.raises(ProjectStorageCorruptionError, match="unsupported or corrupt") as corrupt:
            assert_video_batch_contracts(connection)
        assert "requires explicit maxJobs and maxRequestedSeconds" in str(corrupt.value.__cause__)
        assert connection.execute("SELECT manifest,manifest_hash FROM v2_video_batches").fetchone() == before
    assert not provider.submits


@pytest.mark.parametrize("model,base,fields", [
    (LaunchRequest, {"expectedBriefRevision": 1}, ("maxImages", "maxJobs")),
    (BatchSetup, {"profileId": "test-profile"}, ("maxJobs", "maxRequestedSeconds")),
])
def test_new_budgets_default_and_explicit_null_are_unlimited(model, base, fields):
    default = model.model_validate(base).model_dump(mode="json", by_alias=True)
    explicit = model.model_validate(base | dict.fromkeys(fields)).model_dump(mode="json", by_alias=True)
    assert default == explicit
    assert all(default[field] is None for field in fields)


@pytest.mark.parametrize("model,base,field", [
    (LaunchRequest, {"expectedBriefRevision": 1}, "maxImages"),
    (LaunchRequest, {"expectedBriefRevision": 1}, "maxJobs"),
    (BatchSetup, {"profileId": "test-profile"}, "maxJobs"),
    (BatchSetup, {"profileId": "test-profile"}, "maxRequestedSeconds"),
])
@pytest.mark.parametrize("invalid", [True, False, "", "100", "unlimited", 0, -1, 12.5, 100.0, float("nan"), float("inf")])
def test_invalid_budget_never_becomes_unlimited(model, base, field, invalid):
    with pytest.raises(ValidationError):
        model.model_validate(base | {field: invalid})


def test_explicit_finite_caps_have_no_artificial_upper_ceiling():
    launch = LaunchRequest(expectedBriefRevision=1, maxImages=300, maxJobs=400)
    batch = BatchSetup(profileId="test-profile", maxJobs=300, maxRequestedSeconds=3000)
    assert (launch.max_images, launch.max_jobs) == (300, 400)
    assert (batch.max_jobs, batch.max_requested_seconds) == (300, 3000)


def test_frozen_finite_policy_and_scope_hashes_stay_exact():
    # Explicit finite payloads retain their fixed encodings and hashes.
    policy = _policy().model_dump(mode="json", by_alias=True)
    assert stable_hash(policy) == "ce3780c35e6bfb59836eb1eb0bc221fe775c9ce81ca792fc85a8d4c08ca13e42"
    assert LaunchPolicy.model_validate(policy).model_dump(mode="json", by_alias=True) == policy
    assert stable_hash(asdict(SCOPES[0])) == "cd85ea471974c84485028f4471912d45877ddcb226067e0f64e72f3ebcd5a080"
    unlimited = LaunchPolicy.model_validate(policy | {"maxImages": None, "maxJobs": None})
    assert unlimited.max_images is None and unlimited.max_jobs is None
    assert LaunchPolicy.model_validate_json(unlimited.model_dump_json()).model_dump() == unlimited.model_dump()


@pytest.mark.parametrize("cap,authority,allowed", [(None, None, True), (10, None, True),
    (None, 10, False), (11, 10, False), (10, 10, True), (9, 10, True)])
def test_budget_containment_distinguishes_unlimited_from_finite(cap, authority, allowed):
    assert budget_within_authority(cap, authority) is allowed


def test_uncapped_prospective_qa_does_not_widen_the_frozen_scope():
    original = SCOPES[0]
    prospective = replace(original, id="test-prospective", max_submissions=None, max_requested_seconds=None)
    assert (prospective.max_submissions, prospective.max_requested_seconds) == (None, None)
    assert (original.max_submissions, original.max_requested_seconds) == (2, 10)
    for field in ("max_submissions", "max_requested_seconds"):
        for invalid in (True, "10", 0, -1, 10.0, float("nan")):
            with pytest.raises(ValueError):
                replace(original, **{field: invalid})
    assert exceeds_budget(10**12, None) is False
    assert exceeds_budget(11, 10) is True
    assert exceeds_budget(10, 10) is False


def test_real_api_persists_default_null_and_explicit_finite_manifest_without_dispatch(tmp_path):
    storage, client, service, provider, project, original = batch_environment(tmp_path)
    prefix = f"/api/v2/projects/{project}/video-batch"
    def cancel(view):
        response = client.post(prefix + "/control", json={"batchId": view["id"],
            "expectedControlRevision": view["controlRevision"], "action": "cancel"})
        assert response.status_code == 200, response.text
    cancel(original)
    for limits in ({}, {"maxJobs": None, "maxRequestedSeconds": None}, {"maxJobs": 6, "maxRequestedSeconds": 30}):
        response = client.post(prefix + "/setup", json={"profileId": original["manifest"]["setup"]["profileId"]} | limits)
        assert response.status_code == 200, response.text
        view = response.json()
        assert not view["manifest"]["blockers"]
        assert view["manifest"]["setup"]["maxJobs"] == limits.get("maxJobs")
        assert view["manifest"]["setup"]["maxRequestedSeconds"] == limits.get("maxRequestedSeconds")
        assert client.get(prefix).json()["manifestHash"] == view["manifestHash"]
        with closing(storage.projects.open(project)) as store:
            persisted = store.repository.video_batches.current(project)
            assert persisted["manifest"] == view["manifest"]
            assert stable_hash(persisted["manifest"]) == view["manifestHash"]
        cancel(view)
    assert not provider.submits


@pytest.mark.parametrize("scope_caps,batch_caps,allowed", [
    ((None, None), (None, None), True),
    ((None, None), (6, 30), True),
    ((6, None), (None, 30), False),
    ((None, 30), (6, None), False),
    ((6, None), (6, None), True),
    ((None, 30), (None, 30), True),
    ((6, 30), (None, None), False),
    ((6, 30), (7, 30), False),
    ((6, 30), (6, 31), False),
])
def test_qa_batch_caps_intersect_each_frozen_authority_independently(tmp_path, monkeypatch, scope_caps, batch_caps, allowed):
    from plotloom.exceptions import InvalidTransitionError
    from tests.delegated_qa_fixtures import qa_environment, qa_start
    from tests.video_batch_fixtures import ready_batch
    storage, client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch, limits=scope_caps)
    service.control(project, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    setup = service.setup(project, BatchSetup(profileId=view["manifest"]["setup"]["profileId"],
        aspectPolicy="cover_center_crop", maxJobs=batch_caps[0], maxRequestedSeconds=batch_caps[1]))
    ready = ready_batch(service, project, setup)
    if allowed:
        started = qa_start(service, project, ready, actor)
        with closing(storage.projects.open(project)) as store:
            assert store.repository.video_batches.current(project)["manifestHash"] == started["manifestHash"]
    else:
        with pytest.raises(InvalidTransitionError, match="caps"):
            qa_start(service, project, ready, actor)
    assert not provider.submits


@pytest.mark.parametrize("state", ["failed", "outcome_unknown"])
@pytest.mark.parametrize("unlimited", [False, True])
def test_cumulative_qa_counts_failed_unknown_and_uncapped_still_blocks_unsettled(tmp_path, monkeypatch, state, unlimited):
    from copy import deepcopy
    from sqlalchemy import select
    from plotloom.contract_identity import new_id
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.delegated_qa_video import assert_dispatch
    from plotloom.persistence.schema import VideoJobRow, ProjectVideoDispatchRow
    from tests.delegated_qa_fixtures import qa_environment, qa_start
    storage, client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch,
        limits=(None, None) if unlimited else "finite")
    qa_start(service, project, view, actor)
    service.step(project)  # prepare only
    with closing(storage.projects.open(project)) as store, store.repository._write() as session:
        original = session.scalar(select(VideoJobRow))
        fields = {column.name: deepcopy(getattr(original, column.name)) for column in VideoJobRow.__table__.columns}
        # Retain six prior failed/UNKNOWN dispatch claims without invoking a provider.
        for index in range(6):
            identifier = new_id()
            session.add(VideoJobRow(**(fields | {"id": identifier, "idempotency_key": f"spent-{index}", "state": state})))
            session.flush()  # Insert the native job before its FK-only claim row.
            session.add(ProjectVideoDispatchRow(video_job_id=identifier, dispatch_identity=new_id(), claimed_at=original.created_at))
        session.flush()
        if unlimited and state == "failed":
            assert_dispatch(session, project, original)
        else:
            with pytest.raises(InvalidTransitionError, match="unsettled QA" if unlimited else "cumulative QA"):
                assert_dispatch(session, project, original)
    assert not provider.submits


@pytest.mark.parametrize("caps", [(5, None), (None, 25)])
def test_finite_batch_still_blocks_under_uncapped_qa_authority(tmp_path, monkeypatch, caps):
    from plotloom.exceptions import InvalidTransitionError
    from tests.delegated_qa_fixtures import qa_environment
    storage, client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch, limits=(None, None))
    service.control(project, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    limited = service.setup(project, BatchSetup(profileId=view["manifest"]["setup"]["profileId"],
        aspectPolicy="cover_center_crop", maxJobs=caps[0], maxRequestedSeconds=caps[1]))
    assert limited["manifest"]["blockers"]
    with pytest.raises(InvalidTransitionError):
        service.draft(project, limited["revision"])
    assert not provider.submits
