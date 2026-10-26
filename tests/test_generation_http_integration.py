"""Production adapter/HTTP proof for durable correction and response recovery."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest

from plotloom.artifacts import LocalArtifactStore
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.artifact_contracts import ArtifactKind
from plotloom.run_contracts import AttemptStatus, RunKind, RunStatus
from plotloom.stage_contracts import StageName, StageStatus
from plotloom.jobs import LifecycleJobRunner
from plotloom.persistence import stable_hash
from plotloom.pipeline import PipelineEngine
from plotloom.project_storage import ProjectFolderStorage
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from plotloom.runtime_secrets import RunSecretBroker
from plotloom.text_provider_resolution import SnapshotTextProviderResolver
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _ProcessLoss(BaseException):
    """Crash after response commit, outside ordinary exception classification."""


def test_real_http_correction_installs_reopens_and_recovers_without_wire_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    wire_requests = []
    server_errors = []
    run = None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            pass

        def do_POST(self) -> None:
            try:
                assert self.path == "/v1/chat/completions"
                assert self.headers.get("Authorization") is None
                request = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                trace = store.run_trace(run.id)
                attempt = trace.attempts[-1]
                assert attempt.dispatched_at is not None
                assert attempt.response_persisted_at is None
                assert attempt.status == AttemptStatus.RUNNING
                wire_requests.append(request)
                # Reuse the current V3 response builder as server fixture data.
                fixture = (
                    FixtureProvider()
                    .generate(
                        SimpleNamespace(
                            messages=[
                                SimpleNamespace(**message)
                                for message in request["messages"]
                            ],
                            model=request["model"],
                        ),
                        None,
                    )
                    .raw
                )
                if len(wire_requests) == 1:
                    fixture["choices"][0]["message"]["content"] = "not json"
                payload = json.dumps(
                    {**fixture, "id": f"loopback-{len(wire_requests)}"}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as error:
                server_errors.append(error)
                self.send_error(500)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    profile = fixture_profile()
    values = profile.model_dump(mode="json", by_alias=True)
    values.update(
        textBaseUrl=f"http://127.0.0.1:{server.server_port}/v1", profileHash=""
    )
    profile = type(profile).model_validate(values)
    snapshot = profile.model_dump(mode="json", by_alias=True)
    broker = RunSecretBroker()

    def execute():
        runner = LifecycleJobRunner(
            store.generation,
            PipelineEngine(store.generation, SnapshotTextProviderResolver(), broker),
            RunContext(
                providers=ProviderPorts(),
                artifacts=LocalArtifactStore(store.home / "runs"),
            ),
            max_workers=1,
            secret_registrar=broker,
        )
        try:
            return runner.submit(run.id).result()
        finally:
            runner.close()

    persist = store.generation.persist_attempt_response

    def persist_then_crash(attempt_id, content, *, provider_request_id=None):
        artifact = persist(attempt_id, content, provider_request_id=provider_request_id)
        if len(wire_requests) == 2:
            raise _ProcessLoss()
        return artifact

    thread.start()
    try:
        with store.generation.admit_provider_snapshot(snapshot):
            run = store.generation.create_run(
                store.project().id,
                RunKind.PIPELINE,
                [StageName.STORY_BIBLE],
                provider_snapshot=snapshot,
            )
        monkeypatch.setattr(
            store.generation, "persist_attempt_response", persist_then_crash
        )
        with pytest.raises(_ProcessLoss):
            execute()
        assert not server_errors
        assert len(wire_requests) == 2
        before = store.run_trace(run.id)
        assert [attempt.outcome_code for attempt in before.attempts] == [
            "response.extraction",
            None,
        ]
        recovered_id = before.attempts[-1].id
        assert before.attempts[-1].response_persisted_at is not None
        monkeypatch.setattr(store.generation, "persist_attempt_response", persist)
        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [run.id]
        assert execute().status == RunStatus.SUCCEEDED
        assert len(wire_requests) == 2
        trace = store.run_trace(run.id)
        assert trace.attempts[-1].id == recovered_id
        assert [attempt.status for attempt in trace.attempts] == [
            AttemptStatus.FAILED,
            AttemptStatus.SUCCEEDED,
        ]
        assert [attempt.source_attempt_id for attempt in trace.attempts] == [
            None,
            trace.attempts[0].id,
        ]
        assert len([a for a in trace.artifacts if a.kind == ArtifactKind.RESPONSE]) == 2
        canonical = store.authoring.list_stage_envelopes(store.project().id)
        assert [
            item.head.stage
            for item in canonical
            if item.head.status == StageStatus.READY
        ] == [StageName.STORY_BIBLE]
        canonical_hash = stable_hash(
            [item.model_dump(mode="json") for item in canonical]
        )
        project_id = store.project().id
        store.close()
        store = storage.projects.open(project_id)
        assert (
            stable_hash(
                [
                    item.model_dump(mode="json")
                    for item in store.authoring.list_stage_envelopes(project_id)
                ]
            )
            == canonical_hash
        )
        assert store.run_trace(run.id).model_dump(mode="json") == trace.model_dump(
            mode="json"
        )
    finally:
        broker.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()
