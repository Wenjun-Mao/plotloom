"""Real host acknowledgment shape stays pending without false blocking/resends."""
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from plotloom.autopilot_content_language import ensure_content_language
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.content_language_service import ContentLanguageService
from plotloom.image_job_contracts import ImageJobError
from tests.content_language_fixtures import completed_check, result_for
from tests.test_codex_exec_validation import SOURCE_REVISION
from tests.test_content_language_service import _ready
from tests.test_content_language_service import check_environment as _check_environment

check_environment = _check_environment


def controller_view(registry):
    @contextmanager
    def command(*_args):
        yield
    controller = SimpleNamespace(registry=registry, command=command)
    view = SimpleNamespace(id=str(uuid4()), policy=SimpleNamespace(code_revision=SOURCE_REVISION))
    return controller, view


def test_spawn_intent_ack_then_running_then_completed_never_blocks_or_resends(check_environment, monkeypatch):
    _storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    controller, view = controller_view(registry)
    statuses, admissions = {}, []

    def admit(attempt):
        admissions.append(attempt)
        status = CodexExecHostStatus(state="spawn_intent", attempt=attempt)
        statuses[str(attempt.attempt_id)] = status
        return status

    registry.codex_exec_admit = admit
    registry.codex_exec_status = lambda identifier: statuses.get(str(identifier), CodexExecHostStatus(state="not_found"))
    checkpoint = {"operationKey": "outline"}
    assert ensure_content_language(controller, store, view, "claim", original, candidate, checkpoint) is False
    service = ContentLanguageService(registry)
    job = store.repository.content_language.find(original, candidate)
    assert service.status(store, job)["state"] == "spawn_intent"
    _request, data = store.repository.content_language.load(original.project_id, job)
    assert data["admissionAcknowledged"] and not service.status(store, job)["executionPending"]
    attempt = admissions[0]
    running = transition_exec_attempt(attempt, state="running", process_id=123,
        process_group_id=123, process_birth_identity="explicit-fake-host-ack")
    statuses[str(attempt.attempt_id)] = CodexExecHostStatus(state="running", attempt=running)
    assert ensure_content_language(controller, store, view, "claim", original, candidate, checkpoint) is False
    request, _data = store.repository.content_language.load(original.project_id, job)
    done, receipt = completed_check(store, job, result_for(request))
    statuses[str(attempt.attempt_id)] = CodexExecHostStatus(state="completed", attempt=done, receipt=receipt)
    assert ensure_content_language(controller, store, view, "claim", original, candidate, checkpoint) is True
    assert len(admissions) == 1


@pytest.mark.parametrize("category,expected", [("transient", "content_language_check_pending"),
                                               ("permission", "content_language_check_blocked")])
def test_unknown_without_positive_stop_waits_only_under_repeatable_authority(check_environment, monkeypatch, category, expected):
    _storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    controller, view = controller_view(registry)
    service = ContentLanguageService(registry)
    job = service.prepare(store, original, candidate, code_revision=SOURCE_REVISION, run_id=view.id)
    _request, data = store.repository.content_language.load(original.project_id, job)
    from plotloom.codex_exec_contracts import CodexExecAttempt
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    unknown = transition_exec_attempt(attempt, state="outcome_unknown", execution_failure=category)
    registry.codex_exec_status = lambda _identifier: CodexExecHostStatus(state="outcome_unknown", attempt=unknown)
    registry.codex_exec_admit = lambda _attempt: pytest.fail("must not admit while local ownership is unproven")
    with pytest.raises(ImageJobError) as error:
        ensure_content_language(controller, store, view, "claim", original, candidate, {"operationKey": "outline"})
    assert error.value.code == expected
    assert service.status(store, job)["retry"]["retryCount"] == 0
