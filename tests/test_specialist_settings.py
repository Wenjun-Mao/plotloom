"""Local bindings never bypass a native queue reservation."""
import subprocess
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.image_job_contracts import ImageJobError
from plotloom.specialist_settings import SpecialistRegistry, SpecialistSettings


def configured(tmp_path):
    registry = SpecialistRegistry(tmp_path)
    settings = SpecialistSettings.model_validate({
        "text": {"name": "文字", "taskId": str(uuid4())},
        "image": {"name": "图像", "taskId": str(uuid4())},
    })
    registry.save(settings)
    return registry, settings


def send(registry, role="text", job="ch_" + "a" * 32, **kwargs):
    registry.dispatch(role, job_id=job, package_path="/frozen/package", delivery_path="/delivery", **kwargs)


def test_settings_validate_uuid_and_distinct_roles():
    with pytest.raises(ValidationError):
        SpecialistSettings.model_validate({"text": {"name": "Text", "taskId": "a title"}})
    identity = str(uuid4())
    with pytest.raises(ValidationError):
        SpecialistSettings.model_validate({role: {"name": role, "taskId": identity} for role in ["text", "image"]})


def test_unconfigured_send_does_not_export(tmp_path):
    registry = SpecialistRegistry(tmp_path)
    with pytest.raises(ImageJobError, match="聊天 ID"):
        send(registry, before_send=lambda: pytest.fail("must not export"))
    assert not registry.view()["busy"]


def test_persistence_busy_separate_roles_and_no_resend_after_rebinding(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: calls.append(command) or subprocess.CompletedProcess(command, 0))
    registry, settings = configured(tmp_path)
    job = "ch_" + "a" * 32
    send(registry, assignment="exact text instructions", context={"projectId": "p", "stage": "characters"})
    assert calls[0][-1] == "exact text instructions"
    assert calls[0][3] == settings.text.task_id
    registry = SpecialistRegistry(tmp_path)
    assert registry.view()["activeTasks"][0]["stage"] == "characters"
    with pytest.raises(ImageJobError):
        registry.save(settings)
    with pytest.raises(ImageJobError):
        send(registry, job="ch_" + "b" * 32, before_send=lambda: pytest.fail("busy must not export"))
    send(registry, role="image", job="ij_" + "b" * 32)
    assert len(calls) == 2
    registry.complete(job)
    assert registry.view()["busy"]  # Other role is still busy.
    registry.complete("ij_" + "b" * 32)
    settings.text.task_id = str(uuid4())
    registry.save(settings)
    with pytest.raises(ImageJobError):
        send(registry)
    assert len(calls) == 2
    assert registry.status(job)["state"] == "completed"


@pytest.mark.parametrize("timeout", [False, True])
def test_unknown_transport_outcome_survives_restart(tmp_path, monkeypatch, timeout):
    def queue(command, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired("codex", 30)
        return subprocess.CompletedProcess(command, 1)
    monkeypatch.setattr(subprocess, "run", queue)
    registry, settings = configured(tmp_path)
    with pytest.raises(ImageJobError):
        send(registry)
    restored = SpecialistRegistry(tmp_path)
    assert restored.status("ch_" + "a" * 32)["state"] == "outcome_unknown"
    with pytest.raises(ImageJobError):
        restored.save(settings)
    with pytest.raises(ImageJobError):
        send(restored)


def test_bootstrap_preserves_existing_lease_and_does_not_override_ui_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: subprocess.CompletedProcess(command, 0))
    original = NativeCodexImageDispatcher(str(uuid4()), tmp_path / "original")
    original.dispatch(job_id="ij_" + "a" * 32, package_path="/p", delivery_path="/d")
    registry = SpecialistRegistry(tmp_path / "application", original)
    assert registry.view()["busy"]
    registry.complete("ij_" + "a" * 32)
    settings = SpecialistSettings()
    registry.save(settings)
    assert SpecialistRegistry(tmp_path / "application", original).view()["image"]["taskId"] is None


def test_export_precondition_failure_releases_unsent_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("must not queue"))
    registry, _ = configured(tmp_path)
    def reject():
        raise ValueError("already exported manually")
    with pytest.raises(ValueError, match="exported manually"):
        send(registry, before_send=reject)
    assert not registry.view()["busy"]
    assert registry.status("ch_" + "a" * 32)["state"] == "prepared"
