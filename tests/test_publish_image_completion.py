"""Final publication binds native Codex identity separately from ImageGen execution."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
NATIVE_TASK_ID = "01a1357a-249d-7e73-81fa-5e337d7bdfe5"
IMAGEGEN_EXECUTION_ID = "exec-101f61ef-ab1c-4dcf-a6bc-702e4bc8a81e"
JOB_ID = "ij_1234567890abcdefghij"


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _delivery_fixture(tmp_path: Path, *, native_task_id: str = NATIVE_TASK_ID):
    package = tmp_path / "jobs" / JOB_ID / "package"
    delivery = package.parent / "delivery"
    outputs = delivery / "outputs"
    package.mkdir(parents=True)
    outputs.mkdir(parents=True)
    skill_hash = hashlib.sha256((ROOT / ".agents/skills/plotloom-image-specialist/SKILL.md").read_bytes()).hexdigest()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    request_hash = "a" * 64
    request = {
        "schemaVersion": 3,
        "packageVersion": 6,
        "jobId": JOB_ID,
        "requestHash": request_hash,
        "executionContract": "codex_specialist.v3",
        "specialistPreflight": {
            "version": "p1.5-pin.v2",
            "skillVersion": "plotloom-image-specialist.v4",
            "executionContract": "codex_specialist.v3",
            "codeRevision": revision,
            "skillHash": skill_hash,
        },
        "nativeTaskBinding": {"mode": "configured_task", "taskId": native_task_id},
    }
    _write_json(package / "request.json", request)
    image = b"fixture image bytes"
    (outputs / "render.png").write_bytes(image)
    pin = {
        "jobId": JOB_ID,
        "requestHash": request_hash,
        "executionContract": "codex_specialist.v3",
        "skillVersion": "plotloom-image-specialist.v4",
        "codeRevision": revision,
        "skillHash": skill_hash,
        "nativeTaskId": NATIVE_TASK_ID,
    }
    _write_json(delivery / "executor-pin.json", pin)
    manifest = {
        "schemaVersion": 3,
        "jobId": JOB_ID,
        "requestHash": request_hash,
        "deliveryId": "delivery-fixture-1",
        "actualPrompt": "A fixture prompt submitted to ImageGen.",
        "outputs": [{"filename": "render.png", "sha256": hashlib.sha256(image).hexdigest(), "role": "original"}],
        "toolEvidence": {
            "tool": "codex_imagegen",
            "nativeTaskId": NATIVE_TASK_ID,
            "imageGenExecutionId": IMAGEGEN_EXECUTION_ID,
            "available": True,
        },
        "executorProvenance": {
            "codeRevision": revision,
            "skillVersion": "plotloom-image-specialist.v4",
            "skillHash": skill_hash,
        },
        "limitations": [],
    }
    draft = delivery / "completion-draft.json"
    _write_json(draft, manifest)
    return package, delivery, draft, manifest


def _run_publisher(package: Path, draft: Path, *, task_id: str | None = NATIVE_TASK_ID):
    environment = os.environ.copy()
    if task_id is None:
        environment.pop("CODEX_THREAD_ID", None)
    else:
        environment["CODEX_THREAD_ID"] = task_id
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/publish_image_completion.py"), "--package", str(package), "--manifest", str(draft)],
        cwd=ROOT,
        check=False,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_publisher_writes_valid_completion_once_with_distinct_native_and_imagegen_ids(tmp_path: Path) -> None:
    package, delivery, draft, _manifest = _delivery_fixture(tmp_path)

    result = _run_publisher(package, draft)

    assert result.returncode == 0, result.stderr
    completion = json.loads((delivery / "completion.json").read_text(encoding="utf-8"))
    assert completion["toolEvidence"]["nativeTaskId"] == NATIVE_TASK_ID
    assert completion["toolEvidence"]["imageGenExecutionId"] == IMAGEGEN_EXECUTION_ID
    assert "taskId" not in completion["toolEvidence"]
    assert not draft.exists()
    assert _run_publisher(package, delivery / "completion-draft.json").returncode != 0


def test_publisher_preserves_explicit_manual_current_task_binding(tmp_path: Path) -> None:
    package, delivery, draft, manifest = _delivery_fixture(tmp_path)
    current_task = str(uuid4())
    request_path = package / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["nativeTaskBinding"] = {"mode": "current_task"}
    _write_json(request_path, request)
    pin_path = delivery / "executor-pin.json"
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    pin["nativeTaskId"] = current_task
    _write_json(pin_path, pin)
    manifest["toolEvidence"]["nativeTaskId"] = current_task
    _write_json(draft, manifest)

    result = _run_publisher(package, draft, task_id=current_task)

    assert result.returncode == 0, result.stderr
    completion = json.loads((delivery / "completion.json").read_text(encoding="utf-8"))
    assert completion["toolEvidence"]["nativeTaskId"] == current_task


def test_publisher_rejects_configured_binding_that_differs_from_the_pin(tmp_path: Path) -> None:
    package, delivery, draft, _manifest = _delivery_fixture(tmp_path)
    request_path = package / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["nativeTaskBinding"]["taskId"] = str(uuid4())
    _write_json(request_path, request)

    result = _run_publisher(package, draft)

    assert result.returncode != 0
    assert not (delivery / "completion.json").exists()
    assert draft.is_file()


@pytest.mark.parametrize(
    ("native_id", "execution_id", "task_id"),
    [
        (IMAGEGEN_EXECUTION_ID, IMAGEGEN_EXECUTION_ID, NATIVE_TASK_ID),
        # Keep the foreign UUID random without changing the native test inventory.
        pytest.param(str(uuid4()), IMAGEGEN_EXECUTION_ID, NATIVE_TASK_ID, id="foreign-native-task"),
        (NATIVE_TASK_ID, NATIVE_TASK_ID, NATIVE_TASK_ID),
        (NATIVE_TASK_ID, IMAGEGEN_EXECUTION_ID, None),
    ],
)
def test_publisher_rejects_missing_or_mismatched_identity_before_final_marker(
    tmp_path: Path, native_id: str, execution_id: str, task_id: str | None,
) -> None:
    package, delivery, draft, manifest = _delivery_fixture(tmp_path)
    manifest["toolEvidence"]["nativeTaskId"] = native_id
    manifest["toolEvidence"]["imageGenExecutionId"] = execution_id
    _write_json(draft, manifest)

    result = _run_publisher(package, draft, task_id=task_id)

    assert result.returncode != 0
    assert not (delivery / "completion.json").exists()
    assert draft.is_file()
