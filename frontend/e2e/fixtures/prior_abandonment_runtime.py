"""Only host acknowledgment/one erasure fault are offline seams; routes are real."""
import json
import shutil
import fcntl
import os
from contextlib import asynccontextmanager
from pathlib import Path

from plotloom.project_abandonment_contracts import AbandonmentPreview
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecHostStatus


def install(app, application_root):
    path = application_root / "prior-abandonment-fixture.json"

    def load():
        return json.loads(path.read_text(encoding="utf-8"))

    def save(value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def host(packet, *, revoke=False):
        value = load()
        assert packet.project_id == value["projectId"] and packet.project_home == value["home"]
        assert [attempt.model_dump(mode="json", by_alias=True) for attempt in sorted(packet.attempts, key=lambda item: str(item.attempt_id))] == value["attempts"]
        value["calls"].append("revoke" if revoke else "preview")
        if revoke:
            assert packet.expected_preview_hash == value["previewHash"] and not value["blocked"]
            value["revoked"] = True
        save(value)
        return AbandonmentPreview(project_id=packet.project_id, preview_hash=value["previewHash"],
            eligible=not value["blocked"], blockers=["exact-original-task: local ownership unresolved"] if value["blocked"] else [],
            unknown_attempt_ids=[str(attempt.attempt_id) for attempt in packet.attempts if attempt.state not in {"completed", "failed", "settled"}],
            revoked=value["revoked"])

    app.state.autopilot_service.registry.codex_exec_abandonment = host
    if load().get("currentState") is not None:
        # Hold the normal leader lease for this disposable application's lifetime.
        # Background advancement stays quiescent; genuine manual control and
        # final project-exclusive erasure retain all production admission guards.
        controller_lock = application_root / ".autopilot-controller.lock"
        descriptor = os.open(controller_lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(descriptor)
            raise
        value = load()
        value["controllerLease"] = {"path": str(controller_lock), "held": True}
        save(value)
        base_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def quiescent_fixture(owned_app):
            try:
                async with base_lifespan(owned_app) as state:
                    yield state
            finally:
                try:
                    value = load()
                    value["controllerLease"]["held"] = False
                    save(value)
                finally:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                    os.close(descriptor)

        app.router.lifespan_context = quiescent_fixture

        def retained(attempt_id):
            value = load()
            assert Path(value["home"]).parent == app.state.project_folder_storage.projects.outputs_root
            attempt = next(item for item in value["attempts"] if item["attemptId"] == str(attempt_id))
            assert attempt["projectId"] == value["projectId"]
            return value, CodexExecAttempt.model_validate(attempt)

        def status(attempt_id):
            _value, attempt = retained(attempt_id)
            return CodexExecHostStatus(state=attempt.state, attempt=attempt)

        def cancel(attempt):
            value, original = retained(attempt.attempt_id)
            assert attempt == original
            value["cancelAttemptIds"].append(str(attempt.attempt_id))
            save(value)
            # This fixture acknowledges only the exact local host response. Its
            # original UNKNOWN/attempt evidence remains unchanged.
            return CodexExecHostStatus(state=original.state, attempt=original)

        app.state.autopilot_service.registry.codex_exec_status = status
        app.state.autopilot_service.registry.codex_exec_cancel = cancel
    original = shutil.rmtree

    def erase(target, *args, **kwargs):
        value = load()
        if Path(target) == Path(value["home"]):
            value["eraseCount"] += 1
            save(value)
        if Path(target) == Path(value["home"]) and value["fault"] and not value["faultConsumed"]:
            assert value["revoked"]
            value["faultConsumed"] = True
            save(value)
            raise PermissionError("test-owned fault after ACK and manifest withdrawal")
        return original(target, *args, **kwargs)

    erase.avoids_symlink_attacks = original.avoids_symlink_attacks
    shutil.rmtree = erase
