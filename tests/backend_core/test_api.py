from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from plotloom.api import create_app
from plotloom.domain import (
    STAGE_ORDER,
    Artifact,
    ArtifactKind,
    AttemptStatus,
    MediaKind,
    ProviderSettings,
    RunKind,
    StageName,
    StoryBible,
    WorkUnitFailureDisposition,
)
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse
from plotloom.generation.planning import GenerationPlan, _generation_plan_hash
from plotloom.generation.prompts import sha256_text
from plotloom.persistence import (
    EntityRevisionRow,
    GenerationPlanRow,
    SQLiteRepository,
    StageHeadRow,
    stable_hash,
)
from plotloom.pipeline import RunSecretBroker
from plotloom.text_adapters import ReadinessResult

from .conftest import all_stage_payloads


class RecordingCompiler:
    def __init__(self) -> None:
        self.context = None

    def compile(self, context, kind: MediaKind):
        self.context = context
        return "derived from canonical context", {"storyBible": context.story_bible.logline, "kind": kind.value}


class RecordingScheduler:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, str | None]] = []

    def submit(self, run_id: str, *, session_api_key: str | None = None):
        self.submissions.append((run_id, session_api_key))

    def request_cancel(self, run_id: str):
        raise AssertionError(f"unexpected cancellation for {run_id}")


class ServerKeyProbeAdapter:
    name = "server-key-probe"
    capabilities = ProviderCapabilities()

    def __init__(self) -> None:
        self.observed_keys: list[str] = []

    def generate(self, request, secret):
        assert secret is not None
        with secret.reveal() as value:
            self.observed_keys.append(value)
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            raw={
                "model": request.model,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "OK"},
                    }
                ],
            },
            final_content="OK",
            finish_reason="stop",
        )


class ServerKeyProbeResolver:
    def __init__(self, adapter: ServerKeyProbeAdapter) -> None:
        self.adapter = adapter

    def resolve(self, provider_snapshot):
        return self.adapter, str(provider_snapshot["textModel"])


class UnreachablePreflightAdapter:
    name = "controlled-preflight"
    capabilities = ProviderCapabilities()

    def check_readiness(self, expected_model, secret):
        assert expected_model
        assert secret is not None
        return ReadinessResult("unreachable", "readiness.transport_unreachable", True)

    def generate(self, request, secret):
        raise AssertionError("admission must reject before generation")


class JsonSchemaProbeAdapter:
    name = "json-schema-probe"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(self, content: str = '{"ok":"yes"}') -> None:
        self.content = content
        self.requests = []

    def generate(self, request, secret):
        self.requests.append(request)
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            raw={
                "model": request.model,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": self.content},
                    }
                ],
            },
            final_content=self.content,
            finish_reason="stop",
        )


def _quarantined_bible_work_unit(
    repository: SQLiteRepository,
    brief,
    *,
    provider_snapshot: dict | None = None,
):
    """Create exact rejected evidence without invoking an external provider."""

    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot=provider_snapshot,
    )
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(run.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(
        unit.id,
        provider="local-test",
        model="test-model",
    )
    repository.mark_attempt_dispatched(attempt.id)
    prompt = {"messages": [{"role": "user", "content": "PROMPT_SHOULD_NOT_LEAK"}]}
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.PROMPT,
            content=prompt,
            content_hash=stable_hash(prompt),
        )
    )
    repository.persist_attempt_response(
        attempt.id,
        {"rawResponse": "RAW_SHOULD_NOT_LEAK"},
        provider_request_id="provider-request-should-not-leak",
    )
    validation = {
        "accepted": False,
        "issues": [
            {"code": "schema.test_rejected", "message": "VALIDATION_SHOULD_NOT_LEAK"}
        ],
    }
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    repository.finish_attempt(
        attempt.id,
        AttemptStatus.FAILED,
        error="rejected test output",
        outcome_code="schema.test_rejected",
        failure_disposition=WorkUnitFailureDisposition.QUARANTINED,
    )
    repository.finish_run(
        run.id,
        quarantine_reason="rejected test output",
        failure_code="schema.test_rejected",
        failed_stage=StageName.STORY_BIBLE,
    )
    return project, repository.get_run(run.id), unit, attempt


def test_exact_v2_route_contract(repository: SQLiteRepository) -> None:
    app = create_app(repository)
    actual = {
        (method, route.path)
        for route in app.routes
        if route.path.startswith("/api/v2")
        for method in route.methods
    }
    assert actual == {
        ("POST", "/api/v2/projects"),
        ("GET", "/api/v2/projects"),
        ("GET", "/api/v2/projects/{project_id}"),
        ("POST", "/api/v2/projects/{project_id}/archive"),
        ("POST", "/api/v2/projects/{project_id}/restore"),
        ("POST", "/api/v2/projects/{project_id}/duplicate"),
        ("POST", "/api/v2/projects/{project_id}/permanent-delete"),
        ("PATCH", "/api/v2/projects/{project_id}"),
        ("GET", "/api/v2/projects/{project_id}/stages"),
        ("GET", "/api/v2/projects/{project_id}/runs"),
        ("GET", "/api/v2/projects/{project_id}/media-tasks"),
        ("POST", "/api/v2/projects/{project_id}/managed-assets"),
        ("GET", "/api/v2/projects/{project_id}/managed-assets"),
        ("GET", "/api/v2/projects/{project_id}/managed-assets/{asset_id}/{variant}"),
        ("POST", "/api/v2/projects/{project_id}/managed-assets/{asset_id}/visual-intents"),
        ("POST", "/api/v2/projects/{project_id}/reviewed-keyframes"),
        ("POST", "/api/v2/projects/{project_id}/still-previews"),
        ("GET", "/api/v2/projects/{project_id}/still-previews"),
        ("GET", "/api/v2/projects/{project_id}/visual-workbench"),
        ("GET", "/api/v2/projects/{project_id}/image-jobs"),
        ("POST", "/api/v2/projects/{project_id}/image-jobs"),
        ("POST", "/api/v2/projects/{project_id}/image-jobs/{job_id}/copy"),
        ("POST", "/api/v2/projects/{project_id}/image-jobs/{job_id}/refresh"),
        ("POST", "/api/v2/projects/{project_id}/image-jobs/{job_id}/cancel"),
        ("GET", "/api/v2/projects/{project_id}/character-references"),
        ("POST", "/api/v2/projects/{project_id}/character-references"),
        ("POST", "/api/v2/projects/{project_id}/character-references/{character_id}/revoke"),
        ("GET", "/api/v2/projects/{project_id}/character-reference-proposals"),
        ("POST", "/api/v2/projects/{project_id}/character-reference-proposals"),
        ("POST", "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/copy"),
        ("POST", "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/refresh"),
        ("GET", "/api/v2/projects/{project_id}/same-person-reviews"),
        ("POST", "/api/v2/projects/{project_id}/same-person-reviews"),
        ("PATCH", "/api/v2/projects/{project_id}/stages/{stage}"),
        ("GET", "/api/v2/projects/{project_id}/storyboard-review"),
        ("POST", "/api/v2/projects/{project_id}/storyboard-approval"),
        ("POST", "/api/v2/projects/{project_id}/pipeline-runs"),
        ("POST", "/api/v2/projects/{project_id}/rebuilds"),
        ("GET", "/api/v2/runs/{run_id}"),
        ("GET", "/api/v2/runs/{run_id}/trace"),
        ("GET", "/api/v2/runs/{run_id}/execution-trace"),
        ("GET", "/api/v2/runs/{run_id}/progress"),
        ("POST", "/api/v2/runs/{run_id}/resume"),
        ("POST", "/api/v2/runs/{run_id}/cancel"),
        ("POST", "/api/v2/runs/{run_id}/repairs"),
        ("POST", "/api/v2/runs/{run_id}/work-units/{work_unit_id}/repairs"),
        ("POST", "/api/v2/projects/{project_id}/shots/{shot_id}/media-tasks"),
        ("GET", "/api/v2/media-tasks/{task_id}"),
        ("GET", "/api/v2/provider-settings"),
        ("PUT", "/api/v2/provider-settings"),
        ("GET", "/api/v2/text-provider-profiles"),
        ("POST", "/api/v2/text-provider-profiles"),
        ("GET", "/api/v2/text-provider-profiles/{profile_id}"),
        ("PUT", "/api/v2/text-provider-profiles/{profile_id}"),
        ("DELETE", "/api/v2/text-provider-profiles/{profile_id}"),
        ("POST", "/api/v2/text-provider-profiles/{profile_id}/activate"),
        ("PUT", "/api/v2/text-provider-profiles/{profile_id}/availability"),
        ("POST", "/api/v2/text-provider-profiles/{profile_id}/probe"),
    }


def test_canonical_schema_errors_are_actionable_422_issues(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    bible, *_ = all_stage_payloads()
    payload = bible.model_dump(mode="json", by_alias=True)
    payload["characters"] = [{
        "id": "character-1",
        "name": "测试角色",
        "role": "lead",
        "description": "用于验证字段路径",
        "goal": "保留结构化错误",
        "traits": [],
        "visualAnchors": [],
        "soundAnchors": [],
        "voiceAnchors": [],
        "allowedStates": [{"not": "a string"}],
        "continuityRules": [],
    }]
    client = TestClient(create_app(repository), raise_server_exceptions=False)

    response = client.patch(
        f"/api/v2/projects/{project.id}/stages/story_bible",
        json={"expectedRevision": 0, "payload": payload},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "schema_validation"
    assert any(
        issue["code"] == "schema_validation"
        and issue["path"] == "characters.0.allowedStates.0"
        for issue in body["issues"]
    )


def test_request_schema_errors_are_actionable_and_never_echo_rejected_secrets(
    repository: SQLiteRepository,
    brief,
) -> None:
    client = TestClient(create_app(repository), raise_server_exceptions=False)
    rejected_secret = "request-secret-must-never-be-echoed"

    secret_response = client.post(
        "/api/v2/text-provider-profiles",
        json={
            "profileId": "secret_test",
            "displayName": "Secret test",
            "configuration": {"apiKey": rejected_secret},
        },
    )
    assert secret_response.status_code == 422
    assert secret_response.json()["code"] == "schema_validation"
    assert set(secret_response.json()) == {"code", "message", "issues"}
    assert all(set(issue) == {"code", "path", "message"} for issue in secret_response.json()["issues"])
    assert rejected_secret not in secret_response.text
    assert "input" not in secret_response.text

    settings = client.get("/api/v2/provider-settings").json()
    numeric_response = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": settings["profileId"],
            "expectedRevision": settings["revision"],
            "textMaxConcurrency": 0,
        },
    )
    assert numeric_response.status_code == 422
    assert numeric_response.json()["code"] == "schema_validation"
    assert any(
        issue["path"] == "textMaxConcurrency"
        for issue in numeric_response.json()["issues"]
    )

    project = repository.create_project(brief)
    revision_response = client.patch(
        f"/api/v2/projects/{project.id}/stages/story_bible",
        json={"expectedRevision": -1, "payload": {}},
    )
    assert revision_response.status_code == 422
    assert revision_response.json()["code"] == "schema_validation"
    assert any(
        issue["path"] == "expectedRevision"
        for issue in revision_response.json()["issues"]
    )


def test_run_progress_is_bounded_and_excludes_prompt_response_and_validation_payloads(
    repository: SQLiteRepository,
    brief,
) -> None:
    _, run, unit, attempt = _quarantined_bible_work_unit(repository, brief)
    client = TestClient(create_app(repository))

    response = client.get(f"/api/v2/runs/{run.id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runId"] == run.id
    assert payload["status"] == "quarantined"
    assert payload["failureCode"] == "schema.test_rejected"
    assert payload["actions"]["repairEligible"] is True
    assert len(payload["workUnits"]) == 1
    projected_unit = payload["workUnits"][0]
    assert projected_unit | {"latestAttempt": None} == {
        "workUnitId": unit.id,
        "stage": "story_bible",
        "sequence": 1,
        "status": "quarantined",
        "maxAttempts": 1,
        "latestAttempt": None,
        "sealed": False,
        "repairEligible": True,
        "repairReasonCode": None,
    }
    projected_attempt = projected_unit["latestAttempt"]
    assert projected_attempt["attemptId"] == attempt.id
    assert projected_attempt["attemptNumber"] == 1
    assert projected_attempt["attemptKind"] == "primary"
    assert projected_attempt["sourceAttemptId"] is None
    assert projected_attempt["status"] == "failed"
    assert projected_attempt["outcomeCode"] == "schema.test_rejected"
    assert projected_attempt["outcomeUnknown"] is False
    assert projected_attempt["inputTokens"] is None
    assert projected_attempt["outputTokens"] is None
    assert projected_attempt["startedAt"]
    assert projected_attempt["finishedAt"]
    serialized = response.text
    for forbidden in (
        "PROMPT_SHOULD_NOT_LEAK",
        "RAW_SHOULD_NOT_LEAK",
        "VALIDATION_SHOULD_NOT_LEAK",
        "provider-request-should-not-leak",
        "messages",
        "rawResponse",
        "artifacts",
    ):
        assert forbidden not in serialized


def test_exact_repair_api_projects_old_parent_plan_as_ineligible(
    repository: SQLiteRepository,
    brief,
) -> None:
    _, source, unit, _ = _quarantined_bible_work_unit(repository, brief)
    current = repository.get_generation_plan(source.id)
    historic_policy = "m1.5-p0.3"
    draft = current.model_copy(
        update={
            "planning_policy_version": historic_policy,
            "planning_policy_hash": sha256_text(historic_policy),
            "plan_hash": "",
        }
    )
    historic = GenerationPlan(
        **draft.model_dump(mode="python", exclude={"plan_hash"}),
        plan_hash=_generation_plan_hash(draft),
    )
    with repository._write() as session:
        row = session.get(GenerationPlanRow, source.id)
        assert row is not None
        row.plan = deepcopy(historic.model_dump(mode="json", by_alias=False))
        row.plan_hash = historic.plan_hash

    client = TestClient(create_app(repository))
    progress = client.get(f"/api/v2/runs/{source.id}/progress")
    rejected = client.post(
        f"/api/v2/runs/{source.id}/work-units/{unit.id}/repairs",
        json={},
        headers={"Idempotency-Key": "obsolete-parent-plan-api"},
    )

    assert progress.status_code == 200
    projected = progress.json()["workUnits"][0]
    assert projected["repairEligible"] is False
    assert projected["repairReasonCode"] == "repair.parent_plan_obsolete"
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "repair.parent_plan_obsolete"


def test_exact_work_unit_repair_uses_frozen_profile_and_rejects_client_overrides(
    repository: SQLiteRepository,
    brief,
) -> None:
    # Application bootstrap materializes the environment/default profile.
    create_app(repository)
    profile = repository.get_text_provider_profile("default")
    project, source, unit, _ = _quarantined_bible_work_unit(
        repository,
        brief,
        provider_snapshot=profile.configuration.model_dump(mode="json", by_alias=True),
    )
    scheduler = RecordingScheduler()
    client = TestClient(create_app(repository, run_scheduler=scheduler))
    endpoint = f"/api/v2/runs/{source.id}/work-units/{unit.id}/repairs"
    headers = {
        "Idempotency-Key": "repair-bible-001",
        "X-Plotloom-Session-API-Key": "session-repair-key",
    }

    created = client.post(endpoint, json={}, headers=headers)

    assert created.status_code == 202
    child = created.json()
    assert child["projectId"] == project.id
    assert child["kind"] == "repair"
    assert child["parentRunId"] == source.id
    assert child["repairStage"] == "story_bible"
    assert child["repairSource"] is None
    assert child["workUnitRepairScopeId"] == child["id"]
    assert child["providerSnapshot"] == source.provider_snapshot
    assert child["instructions"] == source.instructions
    assert scheduler.submissions == [(child["id"], "session-repair-key")]
    assert "session-repair-key" not in created.text

    replay = client.post(endpoint, json={}, headers=headers)
    assert replay.status_code == 202
    assert replay.json()["id"] == child["id"]
    assert scheduler.submissions == [(child["id"], "session-repair-key")]

    for forbidden_body in (
        {"providerProfileId": "other"},
        {"apiKey": "must-not-be-accepted"},
        {"instructions": "change the frozen contract"},
    ):
        rejected = client.post(
            endpoint,
            json=forbidden_body,
            headers={**headers, "Idempotency-Key": f"reject-{len(str(forbidden_body))}"},
        )
        assert rejected.status_code == 422
        assert "must-not-be-accepted" not in str(repository.get_work_unit_repair_scope(child["id"]))

    openapi_operation = client.get("/openapi.json").json()["paths"][
        "/api/v2/runs/{run_id}/repairs"
    ]["post"]
    assert openapi_operation["deprecated"] is True


def test_camel_case_and_revision_conflict(repository: SQLiteRepository, brief) -> None:
    client = TestClient(create_app(repository))
    created = client.post("/api/v2/projects", json={"brief": brief.model_dump(mode="json", by_alias=True)})
    assert created.status_code == 201
    project = created.json()
    assert project["revision"] == 1
    assert project["brief"]["aspectRatio"] == "16:9"
    assert [stage["head"]["stage"] for stage in project["stages"]] == [
        stage.value for stage in STAGE_ORDER
    ]
    assert all(stage["payload"] is None for stage in project["stages"])
    missing_revision = client.patch(f"/api/v2/projects/{project['id']}", json={"brief": project["brief"]})
    assert missing_revision.status_code == 422
    conflict = client.patch(
        f"/api/v2/projects/{project['id']}",
        json={"expectedRevision": 99, "brief": project["brief"]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["actualRevision"] == 1
    stages = client.get(f"/api/v2/projects/{project['id']}/stages").json()["stages"]
    assert [stage["head"]["stage"] for stage in stages] == [
        "story_bible",
        "story_graph",
        "scene_beats",
        "storyboard",
    ]
    assert all(stage["payload"] is None for stage in stages)
    disjoint = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible", "storyboard"]},
    )
    assert disjoint.status_code == 422


def test_project_bootstrap_installs_a_prefix_and_replays_an_idempotency_key(
    repository: SQLiteRepository,
    brief,
) -> None:
    client = TestClient(create_app(repository))
    payloads = all_stage_payloads()
    body = {
        "brief": brief.model_dump(mode="json", by_alias=True),
        "initialStages": [
            {
                "stage": stage.value,
                "payload": payload.model_dump(mode="json", by_alias=True),
            }
            for stage, payload in zip(STAGE_ORDER, payloads, strict=True)
        ],
    }
    headers = {"Idempotency-Key": "first-save-001"}

    created = client.post("/api/v2/projects", json=body, headers=headers)
    assert created.status_code == 201
    replay = client.post("/api/v2/projects", json=body, headers=headers)
    assert replay.status_code == 201
    assert replay.json() == created.json()
    with repository.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM v2_projects")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT COUNT(*) FROM v2_project_creation_idempotency")).scalar_one()
            == 1
        )

    project = created.json()
    stages = project["stages"]
    assert [stage["head"]["stage"] for stage in stages] == [
        stage.value for stage in STAGE_ORDER
    ]
    assert [stage["head"]["status"] for stage in stages] == ["ready"] * len(STAGE_ORDER)
    assert [stage["head"]["revision"] for stage in stages] == [1] * len(STAGE_ORDER)
    assert [stage["payload"] for stage in stages] == [
        payload.model_dump(mode="json", by_alias=True) for payload in payloads
    ]
    assert client.get(f"/api/v2/projects/{project['id']}/stages").json()["stages"] == stages
    expected_inputs = [
        {},
        {StageName.STORY_BIBLE.value: 1},
        {StageName.STORY_BIBLE.value: 1, StageName.STORY_GRAPH.value: 1},
        {
            StageName.STORY_BIBLE.value: 1,
            StageName.STORY_GRAPH.value: 1,
            StageName.SCENE_BEATS.value: 1,
        },
    ]
    for envelope, inputs in zip(stages, expected_inputs, strict=True):
        revision = repository.get_entity_revision(envelope["head"]["entityRevisionId"])
        assert revision.parent_revision_id is None
        assert revision.input_revisions == {
            StageName(stage): value for stage, value in inputs.items()
        }

    conflicting_body = {**body, "brief": {**body["brief"], "title": "不同的重试"}}
    conflict = client.post("/api/v2/projects", json=conflicting_body, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_project_bootstrap_requires_a_canonical_initial_prefix(repository: SQLiteRepository, brief) -> None:
    client = TestClient(create_app(repository))
    graph = all_stage_payloads()[1]
    response = client.post(
        "/api/v2/projects",
        json={
            "brief": brief.model_dump(mode="json", by_alias=True),
            "initialStages": [
                {
                    "stage": StageName.STORY_GRAPH.value,
                    "payload": graph.model_dump(mode="json", by_alias=True),
                }
            ],
        },
    )
    assert response.status_code == 422


def test_project_creation_contention_returns_retryable_response(tmp_path: Path, brief) -> None:
    database_url = f"sqlite:///{tmp_path / 'creation-contention.sqlite3'}"
    holder = SQLiteRepository(database_url)
    contended = SQLiteRepository(database_url, create_schema=False, sqlite_busy_timeout_ms=1)
    client = TestClient(create_app(contended))
    try:
        with holder._bootstrap_write():
            response = client.post(
                "/api/v2/projects",
                json={"brief": brief.model_dump(mode="json", by_alias=True)},
                headers={"Idempotency-Key": "retry-after-contention"},
            )
        assert response.status_code == 503
        assert response.headers["retry-after"] == "1"
        assert response.json()["code"] == "bootstrap_contention"
    finally:
        holder.close()
        contended.close()


def test_provider_and_media_request_reject_secret_fields(repository: SQLiteRepository) -> None:
    client = TestClient(create_app(repository))
    assert client.put("/api/v2/provider-settings", json={"textProvider": "openai", "apiKey": "secret"}).status_code == 422
    for unsafe_url in (
        "https://user:password@example.com/v1",
        "https://example.com/v1?api_key=secret",
        "ftp://example.com/v1",
        "https://example.com:bad/v1",
    ):
        assert (
            client.put("/api/v2/provider-settings", json={"textBaseUrl": unsafe_url}).status_code
            == 422
        )
    assert client.get("/api/v2/provider-settings").json()["textBaseUrl"] == (
        "https://api.atlascloud.ai/v1"
    )
    current_profile = client.get("/api/v2/text-provider-profiles/default").json()
    unsafe_profile = client.put(
        "/api/v2/text-provider-profiles/default",
        json={
            "expectedRevision": current_profile["revision"],
            "displayName": current_profile["displayName"],
            "configuration": {
                **current_profile["configuration"],
                "textBaseUrl": "https://example.com/v1?sig=must-not-persist",
            },
        },
    )
    assert unsafe_profile.status_code == 422
    unsupported_adapter = client.put(
        "/api/v2/text-provider-profiles/default",
        json={
            "expectedRevision": current_profile["revision"],
            "displayName": current_profile["displayName"],
            "configuration": current_profile["configuration"],
            "adapterId": "untrusted_adapter",
            "adapterVersion": "1",
        },
    )
    assert unsupported_adapter.status_code == 422
    response = client.post(
        "/api/v2/projects/unknown/shots/unknown/media-tasks",
        json={"kind": "image", "publicSettings": {"nested": {"accessToken": "secret"}}},
    )
    assert response.status_code == 422
    response = client.post(
        "/api/v2/projects/unknown/shots/unknown/media-tasks",
        json={"kind": "image", "provider": "browser-selected"},
    )
    assert response.status_code == 422
    response = client.post(
        "/api/v2/projects/unknown/shots/unknown/media-tasks",
        json={"kind": "image", "publicSettings": {"imageModel": "browser-selected"}},
    )
    assert response.status_code == 422
    response = client.post(
        "/api/v2/projects/unknown/shots/unknown/media-tasks",
        json={"kind": "image", "publicSettings": {"baseUrl": "https://example.com/v1?key=x"}},
    )
    assert response.status_code == 422


def test_definite_preflight_failure_creates_no_pipeline_run(repository: SQLiteRepository, brief) -> None:
    adapter = UnreachablePreflightAdapter()
    client = TestClient(
        create_app(
            repository,
            text_provider_resolver=ServerKeyProbeResolver(adapter),
        )
    )
    project = client.post(
        "/api/v2/projects", json={"brief": brief.model_dump(mode="json", by_alias=True)}
    ).json()

    refused = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible"]},
        headers={"X-Plotloom-Session-API-Key": "session-only"},
    )

    assert refused.status_code == 422
    assert "selected text backend is unreachable" in refused.json()["detail"]
    assert repository.list_project_runs(project["id"]) == []


def test_profile_crud_round_trips_the_trusted_adapter_selection(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    current = client.get("/api/v2/text-provider-profiles/default").json()

    saved = client.put(
        "/api/v2/text-provider-profiles/default",
        json={
            "expectedRevision": current["revision"],
            "displayName": current["displayName"],
            "configuration": current["configuration"],
            "adapterId": "openai_compatible",
            "adapterVersion": "1",
        },
    )

    assert saved.status_code == 200
    assert saved.json()["adapterId"] == "openai_compatible"
    assert saved.json()["adapterVersion"] == "1"
    assert client.get("/api/v2/text-provider-profiles").json()["trustedAdapters"] == [
        {"adapterId": "openai_compatible", "adapterVersion": "1"}
    ]


def test_provider_settings_merge_defaults_and_freeze_on_run(repository: SQLiteRepository, brief) -> None:
    defaults = ProviderSettings(
        text_provider="server-default",
        text_base_url="https://server.example/v1",
        text_model="server-model",
    )
    scheduler = RecordingScheduler()
    client = TestClient(
        create_app(
            repository,
            run_scheduler=scheduler,
            provider_defaults=defaults,
            key_availability={"text_key_available": True},
        )
    )
    initial = client.get("/api/v2/provider-settings").json()
    assert initial["textProvider"] == "server-default"
    assert initial["textKeyAvailable"] is True
    assert "apiKey" not in initial
    assert initial["profileId"] == "default"
    assert initial["redirectPolicy"] == "no_follow"
    assert len(initial["profileHash"]) == 64

    updated = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": initial["profileId"],
            "expectedRevision": initial["revision"],
            "textModel": "saved-model",
            "textTemperature": 0,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["textBaseUrl"] == "https://server.example/v1"
    assert updated.json()["textModel"] == "saved-model"
    assert updated.json()["textTemperature"] == 0
    assert updated.json()["profileVersion"] == 1
    assert len(updated.json()["profileHash"]) == 64

    project = client.post(
        "/api/v2/projects",
        json={"brief": brief.model_dump(mode="json", by_alias=True)},
    ).json()
    created = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible"]},
        headers={"X-Plotloom-Session-API-Key": "browser-only-secret"},
    )
    assert created.status_code == 202
    run = created.json()
    assert run["providerSnapshot"]["textModel"] == "saved-model"
    assert "browser-only-secret" not in str(run)
    assert scheduler.submissions == [(run["id"], "browser-only-secret")]

    client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": updated.json()["profileId"],
            "expectedRevision": updated.json()["revision"],
            "textModel": "later-model",
        },
    )
    frozen = client.get(f"/api/v2/runs/{run['id']}").json()["providerSnapshot"]
    assert frozen["textModel"] == "saved-model"
    assert "browser-only-secret" not in str(frozen)
    assert frozen["profileSchemaVersion"] == 3
    assert frozen["profileHash"] != updated.json()["profileHash"]
    listed = client.get(f"/api/v2/projects/{project['id']}/runs").json()["runs"]
    assert [item["id"] for item in listed] == [run["id"]]


def test_profile_probe_uses_its_server_key_without_a_browser_override(
    repository: SQLiteRepository,
) -> None:
    adapter = ServerKeyProbeAdapter()
    secrets = RunSecretBroker(server_profile_keys={"default": "server-profile-key"})
    client = TestClient(
        create_app(
            repository,
            text_provider_resolver=ServerKeyProbeResolver(adapter),
            text_secret_source=secrets,
        )
    )
    try:
        profile = client.get("/api/v2/text-provider-profiles/default").json()
        assert profile["serverKeyAvailable"] is True

        response = client.post("/api/v2/text-provider-profiles/default/probe")

        assert response.status_code == 200
        assert response.json()["state"] == "unverified"
        assert response.json()["reasonCode"] == "readiness.check_unsupported"
        assert adapter.observed_keys == []
        assert "server-profile-key" not in response.text
    finally:
        secrets.close()


def test_profile_probe_exercises_a_declared_json_schema_capability(
    repository: SQLiteRepository,
) -> None:
    create_app(repository)
    saved = repository.get_text_provider_profile("default")
    capabilities = saved.configuration.text_capabilities.model_copy(
        update={"json_schema": True}
    )
    repository.update_text_provider_profile(
        "default",
        saved.revision,
        display_name=saved.display_name,
        configuration=saved.configuration.model_copy(
            update={"text_capabilities": capabilities, "profile_hash": ""}
        ),
    )
    adapter = JsonSchemaProbeAdapter()
    secrets = RunSecretBroker(server_profile_keys={"default": "server-profile-key"})
    client = TestClient(
        create_app(
            repository,
            text_provider_resolver=ServerKeyProbeResolver(adapter),
            text_secret_source=secrets,
        )
    )
    try:
        response = client.post("/api/v2/text-provider-profiles/default/probe")

        assert response.status_code == 200
        assert response.json()["state"] == "unverified"
        assert response.json()["reasonCode"] == "readiness.check_unsupported"
        assert adapter.requests == []
    finally:
        secrets.close()


def test_text_run_submission_requires_auth_only_for_bearer_and_can_resume(
    repository: SQLiteRepository,
    brief,
) -> None:
    scheduler = RecordingScheduler()
    client = TestClient(create_app(repository, run_scheduler=scheduler))
    project = client.post(
        "/api/v2/projects",
        json={"brief": brief.model_dump(mode="json", by_alias=True)},
    ).json()

    missing = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible"]},
    )
    assert missing.status_code == 422
    assert repository.list_project_runs(project["id"]) == []

    queued = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible"]},
        headers={"X-Plotloom-Session-API-Key": "session-only"},
    )
    assert queued.status_code == 202
    run_id = queued.json()["id"]
    assert scheduler.submissions == [(run_id, "session-only")]

    resumed = client.post(
        f"/api/v2/runs/{run_id}/resume",
        headers={"X-Plotloom-Session-API-Key": "session-only"},
    )
    assert resumed.status_code == 202
    assert scheduler.submissions[-1] == (run_id, "session-only")

    anonymous_profile = client.get("/api/v2/text-provider-profiles/default").json()
    anonymous_profile["configuration"].update(
        {"textAuthMode": "none", "presetId": "custom"}
    )
    updated = client.put(
        "/api/v2/text-provider-profiles/default",
        json={
            "expectedRevision": anonymous_profile["revision"],
            "displayName": anonymous_profile["displayName"],
            "configuration": anonymous_profile["configuration"],
        },
    )
    assert updated.status_code == 200
    anonymous = client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs",
        json={"stages": ["story_bible"]},
        headers={"X-Plotloom-Session-API-Key": "must-be-ignored"},
    )
    assert anonymous.status_code == 202
    assert scheduler.submissions[-1] == (anonymous.json()["id"], None)


def test_provider_profile_rejects_an_impossible_text_token_budget(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    current = client.get("/api/v2/provider-settings").json()
    profile_before = repository.get_text_provider_profile(current["profileId"])
    media_before = repository.get_provider_settings()

    response = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": current["profileId"],
            "expectedRevision": current["revision"],
            "textContextWindowTokens": 4096,
            "textMaxOutputTokens": 4096,
            "imageModel": "must-roll-back-with-invalid-text",
        },
    )

    assert response.status_code == 422
    assert repository.get_text_provider_profile(current["profileId"]) == profile_before
    assert repository.get_provider_settings() == media_before
    assert "textMaxOutputTokens must be smaller" in response.text


def test_provider_profile_partial_updates_validate_after_merging_current_values(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    current = client.get("/api/v2/provider-settings").json()
    first = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": current["profileId"],
            "expectedRevision": current["revision"],
            "textContextWindowTokens": 16384,
            "textMaxOutputTokens": 1024,
        },
    )
    assert first.status_code == 200

    second = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": first.json()["profileId"],
            "expectedRevision": first.json()["revision"],
            "textContextWindowTokens": 4096,
        },
    )

    assert second.status_code == 200
    assert second.json()["textContextWindowTokens"] == 4096
    assert second.json()["textMaxOutputTokens"] == 1024


def test_legacy_provider_settings_write_obeys_active_profile_revision(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    legacy = client.get("/api/v2/provider-settings").json()
    profile = client.get("/api/v2/text-provider-profiles/default").json()
    profile["configuration"].update(
        {"textModel": "newer-named-model", "presetId": "custom"}
    )
    named_update = client.put(
        "/api/v2/text-provider-profiles/default",
        json={
            "expectedRevision": profile["revision"],
            "displayName": profile["displayName"],
            "configuration": profile["configuration"],
        },
    )
    assert named_update.status_code == 200

    stale = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": legacy["profileId"],
            "expectedRevision": legacy["revision"],
            "textModel": "stale-legacy-overwrite",
        },
    )

    assert stale.status_code == 409
    current = client.get("/api/v2/text-provider-profiles/default").json()
    assert current["configuration"]["textModel"] == "newer-named-model"


def test_legacy_provider_settings_write_rejects_a_changed_active_profile(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    legacy = client.get("/api/v2/provider-settings").json()
    created = repository.create_text_provider_profile(
        "quality",
        "Quality",
        copy_from_profile_id="default",
    )
    selection = repository.get_provider_profile_selection()
    repository.activate_text_provider_profile("quality", selection.revision)

    stale = client.put(
        "/api/v2/provider-settings",
        json={
            "expectedProfileId": legacy["profileId"],
            "expectedRevision": legacy["revision"],
            "textModel": "must-not-be-written",
        },
    )

    assert stale.status_code == 409
    assert repository.get_text_provider_profile("default").configuration.text_model != (
        "must-not-be-written"
    )
    assert repository.get_text_provider_profile("quality") == created


def test_profile_delete_accepts_the_public_camel_case_revision_query(
    repository: SQLiteRepository,
) -> None:
    client = TestClient(create_app(repository))
    created = repository.create_text_provider_profile(
        "delete_me",
        "Delete Me",
        copy_from_profile_id="default",
    )

    response = client.delete(
        f"/api/v2/text-provider-profiles/delete_me?expectedRevision={created.revision}"
    )

    assert response.status_code == 204
    assert response.content == b""


def test_static_v2_mount_serves_index(repository: SQLiteRepository, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>v2</h1>", encoding="utf-8")
    client = TestClient(create_app(repository, static_dir=static_dir))
    response = client.get("/v2/")
    assert response.status_code == 200
    assert "<h1>v2</h1>" in response.text


def test_media_api_is_hard_stopped_before_lookup_compile_persist_or_dispatch(
    repository: SQLiteRepository, brief
) -> None:
    project = repository.create_project(brief)
    compiler = RecordingCompiler()
    scheduler = RecordingScheduler()
    client = TestClient(
        create_app(
            repository,
            media_prompt_compiler=compiler,
            media_scheduler=scheduler,
            provider_defaults=ProviderSettings(
                image_provider="openai",
                image_base_url="https://images.example/v1",
                image_model="image-model",
            ),
        )
    )
    for body in (
        {"kind": "image"},
        {"kind": "image", "publicSettings": {"quality": "high"}},
        {
            "kind": "video",
            "publicSettings": {"sourceUri": "https://assets.example/keyframe.png"},
        },
        {
            "kind": "video",
            "publicSettings": {"imageUrl": "https://assets.example/keyframe.png"},
        },
        {
            "kind": "video",
            "publicSettings": {
                "referenceImages": ["https://assets.example/keyframe.png"]
            },
        },
    ):
        response = client.post(
            f"/api/v2/projects/{project.id}/shots/not-resolved/media-tasks",
            json=body,
            headers={"X-Plotloom-Session-API-Key": "ephemeral-media-key"},
        )
        assert response.status_code == 409
        assert response.json() == {
            "code": "production_pipeline_not_ready",
            "message": (
                "media production requires the future Approval and "
                "ProductionSnapshot pipeline"
            ),
        }
    assert scheduler.submissions == []
    listed = client.get(f"/api/v2/projects/{project.id}/media-tasks").json()["tasks"]
    assert listed == []
    assert compiler.context is None

    unknown = client.post(
        "/api/v2/projects/unknown/shots/unknown/media-tasks",
        json={"kind": "image"},
    )
    assert unknown.status_code == 409
    assert unknown.json()["code"] == "production_pipeline_not_ready"


def test_stage_envelopes_rehydrate_all_canonical_payloads(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    client = TestClient(create_app(repository))
    response = client.get(f"/api/v2/projects/{project.id}/stages")
    assert response.status_code == 200
    envelopes = response.json()["stages"]
    assert all(envelope["head"]["status"] == "ready" for envelope in envelopes)
    assert envelopes[0]["payload"]["narrativePromise"] == ""
    assert envelopes[1]["payload"]["startNodeId"] == "start"
    assert envelopes[2]["payload"]["beats"][0]["visibleEvent"]
    assert envelopes[3]["payload"]["shots"][0]["visualIntent"]


def test_active_v1_canonical_stage_returns_stable_schema_reset_conflict(
    repository: SQLiteRepository,
    brief,
) -> None:
    """Live authoring never interprets migrated V1 evidence as V2."""

    project = repository.create_project(brief)
    for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    legacy = StoryBible(logline="旧版故事", premise="旧版字段不能猜测升级。")
    serialized = legacy.model_dump(mode="json", by_alias=True)
    with repository._write() as session:
        head = session.get(StageHeadRow, f"{project.id}:{StageName.STORY_BIBLE.value}")
        assert head is not None and head.entity_revision_id is not None
        revision = session.get(EntityRevisionRow, head.entity_revision_id)
        assert revision is not None
        revision.payload = serialized
        revision.schema_version = 1
        revision.content_hash = stable_hash(serialized)
        head.schema_version = 1
        head.content_hash = revision.content_hash

    response = TestClient(create_app(repository)).get(f"/api/v2/projects/{project.id}/stages")

    assert response.status_code == 409
    assert response.json() == {
        "code": "data.schema_reset_required",
        "message": "data.schema_reset_required: story_bible payload has unsupported schema version 1",
        "stage": "story_bible",
        "schemaVersion": 1,
    }
