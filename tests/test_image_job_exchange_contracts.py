"""Stable exchange projections retained across image package versions."""

from __future__ import annotations

import json
import os
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from plotloom.image_job_contracts import (
    ImageDeliveryManifest,
    ImageJobError,
    NativeTaskBinding,
)
from plotloom.image_job_exchange import ImageJobExchange
from plotloom.managed_media import ManagedMediaLimits


def test_legacy_v1_package_remains_recheckable_without_a_template(tmp_path: Path) -> None:
    """Historic package bytes remain readable without reviving a V1 runtime."""

    request = {
        "schemaVersion": 1,
        "jobId": "ij_" + "a" * 20,
        "kind": "original",
    }
    request_hash = sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())

    copied = exchange.write_package(
        job_id=request["jobId"],
        request=request,
        request_hash=request_hash,
        references=[],
    )
    package = Path(copied["packagePath"])

    assert {item.name for item in package.iterdir()} == {
        "COPY_ASSIGNMENT.txt",
        "request.json",
    }
    exchange.verify_package(
        job_id=request["jobId"],
        request=request,
        request_hash=request_hash,
        references=[],
    )


@pytest.mark.parametrize(
    ("schema_version", "kind", "target", "manifest_version"),
    [
        (2, "original", "image_job", 1),
        (3, "original", "image_job", 2),
        (3, "character_reference", "character_reference_proposal", 2),
        (3, "art_reference", "art_reference_proposal", 2),
    ],
)
def test_emitted_package_requires_returned_basename_in_both_primary_instructions(
    tmp_path: Path, schema_version: int, kind: str, target: str, manifest_version: int
) -> None:
    request = {
        "schemaVersion": schema_version,
        "jobId": "ij_" + "b" * 20,
        "kind": kind,
        "target": target,
        "specialistPreflight": {
            "version": "p1.5-pin.v1",
            "skillVersion": "plotloom-image-specialist.v3",
        },
    }
    request_hash = sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    arguments = {
        "job_id": request["jobId"],
        "request": request,
        "request_hash": request_hash,
        "references": [],
    }
    copied = exchange.write_package(**arguments)
    package = Path(copied["packagePath"])
    emitted = json.loads((package / "request.json").read_text())
    assignment = (package / "COPY_ASSIGNMENT.txt").read_text()
    template = json.loads((package / "completion-manifest.example.json").read_text())

    for instruction in (emitted["deliveryInstruction"], assignment):
        assert "unchanged using its exact returned basename" in instruction
        assert "declare that same basename in outputs[].filename" in instruction
        assert "placeholders, never required output names" in instruction
    assert template["outputs"] == [{
        "filename": "replace-with-exact-returned-basename.png",
        "sha256": "0" * 64,
        "role": kind,
    }]
    assert template["schemaVersion"] == manifest_version
    assert template["jobId"] == request["jobId"]
    assert template["requestHash"] == request_hash
    assert emitted["packageVersion"] == (2 if schema_version == 2 else 4)
    if schema_version == 3:
        assert emitted["deliveryInstruction"].endswith(
            "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. "
            "Do not write SQLite, modify this package, or include sensitive values."
        )
        assert "Before ImageGen, run: uv run python scripts/pin_image_specialist.py --package " in assignment
        assert "Disclose the exact actual prompt and publish completion.json only after every declared output is complete." in assignment
    assert exchange.write_package(**arguments) == copied
    exchange.verify_package(**arguments)


@pytest.mark.parametrize("schema_version", [1, 2])
def test_retained_manifest_hash_projection_omits_new_identity_members(schema_version: int) -> None:
    manifest = ImageDeliveryManifest.model_validate({
        "schemaVersion": schema_version,
        "jobId": "ij_" + "a" * 20,
        "requestHash": "b" * 64,
        "deliveryId": "delivery-legacy",
        "actualPrompt": "legacy prompt",
        "outputs": [{"filename": "render.png", "sha256": "c" * 64, "role": "original"}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "legacy-codex-task", "available": True},
    })

    expected_payload = {
        "schemaVersion": schema_version,
        "jobId": "ij_" + "a" * 20,
        "requestHash": "b" * 64,
        "deliveryId": "delivery-legacy",
        "actualPrompt": "legacy prompt",
        "outputs": [{"filename": "render.png", "sha256": "c" * 64, "role": "original"}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "legacy-codex-task", "available": True},
        "referenceUse": None,
        "executorProvenance": None,
        "limitations": [],
    }
    actual_payload = manifest.canonical_payload()
    assert actual_payload == expected_payload
    assert sha256(json.dumps(actual_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == {
        1: "4dbccd0ec10c64a27a740f4a6980c77e7d8a93ec72a9c93c0b4a04a5d20de49e",
        2: "2921d2e2052498a0fce7cf90c86178d6c19764a492362d409dfe8305d920baa9",
    }[schema_version]


def test_retained_v5_package_instructions_remain_byte_compatible(tmp_path: Path) -> None:
    request = {
        "schemaVersion": 3,
        "jobId": "ij_" + "d" * 20,
        "kind": "original",
        "target": "image_job",
        "specialistPreflight": {
            "version": "p1.5-pin.v1",
            "skillVersion": "plotloom-image-specialist.v3",
        },
        "frozenSnapshot": {"presentationContract": "physical-visible-runtime.v1"},
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    copied = exchange.write_package(job_id=request["jobId"], request=request, request_hash=request_hash, references=[])
    package = Path(copied["packagePath"])
    emitted = json.loads((package / "request.json").read_text())
    assignment = (package / "COPY_ASSIGNMENT.txt").read_text()

    assert emitted["packageVersion"] == 5
    assert emitted["deliveryInstruction"].endswith(
        "Write complete JPEG or PNG files to delivery/outputs, then publish delivery/completion.json once. "
        "Do not write SQLite, modify this package, or include sensitive values."
    )
    assert "Before ImageGen, run: uv run python scripts/pin_image_specialist.py --package " in assignment
    assert "Disclose the exact actual prompt and publish completion.json only after every declared output is complete." in assignment
    exchange.verify_package(job_id=request["jobId"], request=request, request_hash=request_hash, references=[])


def test_identity_package_freezes_native_task_binding_and_uses_schema_v3_template(tmp_path: Path) -> None:
    task_id = "01a1357a-249d-7e73-81fa-5e337d7bdfe5"
    request = {
        "schemaVersion": 3,
        "executionContract": "codex_specialist.v3",
        "jobId": "ij_" + "e" * 20,
        "kind": "original",
        "target": "image_job",
        "specialistPreflight": {
            "version": "p1.5-pin.v2",
            "skillVersion": "plotloom-image-specialist.v4",
            "executionContract": "codex_specialist.v3",
        },
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    binding = NativeTaskBinding(mode="configured_task", task_id=task_id)
    arguments = {
        "job_id": request["jobId"],
        "request": request,
        "request_hash": request_hash,
        "references": [],
        "native_task_binding": binding,
    }

    package_path = Path(exchange.write_package(**arguments)["packagePath"])
    package_request = json.loads((package_path / "request.json").read_text())
    template = json.loads((package_path / "completion-manifest.example.json").read_text())
    assignment = (package_path / "COPY_ASSIGNMENT.txt").read_text()

    assert package_request["packageVersion"] == 6
    assert package_request["nativeTaskBinding"] == {"mode": "configured_task", "taskId": task_id}
    assert template["schemaVersion"] == 3
    assert template["toolEvidence"]["nativeTaskId"] == task_id
    assert "imageGenExecutionId" in template["toolEvidence"]
    assert "taskId" not in template["toolEvidence"]
    assert "publish_image_completion.py" in assignment
    assert f"{Path(__file__).resolve().parents[1]}/scripts/pin_image_specialist.py" in assignment
    assert f"{Path(__file__).resolve().parents[1]}/scripts/publish_image_completion.py" in assignment
    exchange.verify_package(**arguments)

    with pytest.raises(ImageJobError, match="does not match the frozen image request"):
        exchange.verify_package(**(arguments | {"native_task_binding": NativeTaskBinding(mode="current_task")}))


def test_identity_package_requires_an_explicit_task_binding_before_publication(tmp_path: Path) -> None:
    request = {
        "schemaVersion": 3,
        "executionContract": "codex_specialist.v3",
        "jobId": "ij_" + "f" * 20,
        "kind": "original",
        "specialistPreflight": {
            "version": "p1.5-pin.v2",
            "skillVersion": "plotloom-image-specialist.v4",
            "executionContract": "codex_specialist.v3",
        },
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())

    with pytest.raises(ImageJobError, match="explicit native task binding"):
        exchange.write_package(job_id=request["jobId"], request=request, request_hash=request_hash, references=[])

    assert not (tmp_path / "exchange" / "jobs" / request["jobId"]).exists()


def test_schema_v3_delivery_matches_native_uuid_to_pin_and_frozen_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = "01a1357a-249d-7e73-81fa-5e337d7bdfe5"
    request = {
        "schemaVersion": 3,
        "executionContract": "codex_specialist.v3",
        "jobId": "ij_" + "9" * 20,
        "kind": "original",
        "target": "image_job",
        "specialistPreflight": {
            "version": "p1.5-pin.v2",
            "skillVersion": "plotloom-image-specialist.v4",
            "executionContract": "codex_specialist.v3",
        },
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    binding = NativeTaskBinding(mode="configured_task", task_id=task_id)
    paths = exchange.write_package(job_id=request["jobId"], request=request, request_hash=request_hash,
        references=[], native_task_binding=binding)
    delivery = Path(paths["deliveryPath"])
    outputs = delivery / "outputs"
    outputs.mkdir(parents=True)
    image_bytes = BytesIO()
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(image_bytes, format="PNG")
    content = image_bytes.getvalue()
    (outputs / "render.png").write_bytes(content)
    provenance = {
        "codeRevision": "a" * 40,
        "skillVersion": "plotloom-image-specialist.v4",
        "skillHash": "b" * 64,
    }
    (delivery / "executor-pin.json").write_text(json.dumps({
        "jobId": request["jobId"], "requestHash": request_hash,
        "executionContract": "codex_specialist.v3", "nativeTaskId": task_id, **provenance,
    }))
    manifest = {
        "schemaVersion": 3, "jobId": request["jobId"], "requestHash": request_hash,
        "deliveryId": "delivery-v3-fixture", "actualPrompt": "A test prompt.",
        "outputs": [{"filename": "render.png", "sha256": sha256(content).hexdigest(), "role": "original"}],
        "toolEvidence": {"tool": "codex_imagegen", "nativeTaskId": task_id,
            "imageGenExecutionId": "exec-101f61ef-ab1c-4dcf-a6bc-702e4bc8a81e", "available": True},
        "executorProvenance": provenance,
        "limitations": [],
    }
    (delivery / "completion.json").write_text(json.dumps(manifest))

    accepted = exchange.read_delivery(job_id=request["jobId"], request_hash=request_hash,
        require_executor_provenance=True, require_executor_pin=True,
        expected_executor_skill_version="plotloom-image-specialist.v4",
        expected_executor_contract="codex_specialist.v3", expected_native_task_binding=binding)
    assert accepted is not None
    assert str(accepted.manifest.tool_evidence.native_task_id) == task_id
    assert accepted.manifest.tool_evidence.image_gen_execution_id == "exec-101f61ef-ab1c-4dcf-a6bc-702e4bc8a81e"

    draft_path = delivery / "completion-draft.json"
    draft_path.write_text(json.dumps(manifest))
    assert exchange.read_delivery(job_id=request["jobId"], request_hash=request_hash,
        require_executor_provenance=True, require_executor_pin=True,
        expected_executor_skill_version="plotloom-image-specialist.v4",
        expected_executor_contract="codex_specialist.v3", expected_native_task_binding=binding) is not None

    original_listdir = os.listdir
    removed_draft = False

    def remove_draft_after_listing(path: int | str | bytes | os.PathLike[str] = ".") -> list[str]:
        nonlocal removed_draft
        listed = original_listdir(path)
        if not removed_draft and isinstance(path, int) and "completion-draft.json" in listed:
            draft_path.unlink()
            removed_draft = True
        return listed

    monkeypatch.setattr("plotloom.image_job_exchange.os.listdir", remove_draft_after_listing)
    raced_read = exchange.read_delivery(
        job_id=request["jobId"], request_hash=request_hash,
        require_executor_provenance=True, require_executor_pin=True,
        expected_executor_skill_version="plotloom-image-specialist.v4",
        expected_executor_contract="codex_specialist.v3", expected_native_task_binding=binding,
    )
    assert removed_draft
    assert not draft_path.exists()
    assert raced_read is not None

    wrong_binding = NativeTaskBinding(mode="configured_task", task_id="6d1218af-044c-426a-99d2-18b76c5c6331")
    with pytest.raises(ImageJobError, match="differs from the configured specialist binding"):
        exchange.read_delivery(job_id=request["jobId"], request_hash=request_hash,
            require_executor_provenance=True, require_executor_pin=True,
            expected_executor_skill_version="plotloom-image-specialist.v4",
            expected_executor_contract="codex_specialist.v3", expected_native_task_binding=wrong_binding)


@pytest.mark.parametrize("mode", [None, "popped_out_draft", "popped_out_send"])
def test_message_treatment_excludes_only_runtime_branching_ui(tmp_path: Path, mode: str | None) -> None:
    snapshot = {"presentationContract": "physical-visible-runtime.v1"}
    if mode:
        snapshot["shotPresentation"] = {"review": {"messagePresentation": mode}}
    request = {
        "schemaVersion": 3,
        "jobId": "ij_" + "c" * 20,
        "kind": "original",
        "executionContract": "codex_specialist.v3",
        "specialistPreflight": {
            "version": "p1.5-pin.v2",
            "skillVersion": "plotloom-image-specialist.v4",
            "executionContract": "codex_specialist.v3",
        },
        "frozenSnapshot": snapshot,
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    arguments = {
        "job_id": request["jobId"],
        "request": request,
        "request_hash": request_hash,
        "references": [],
        "native_task_binding": NativeTaskBinding(mode="current_task"),
    }
    package = Path(exchange.write_package(**arguments)["packagePath"])
    emitted = json.loads((package / "request.json").read_text())
    assignment = (package / "COPY_ASSIGNMENT.txt").read_text()
    assert emitted["packageVersion"] == 6
    assert json.loads((package / "completion-manifest.example.json").read_text())["schemaVersion"] == 3
    for instruction in (emitted["deliveryInstruction"], assignment):
        if mode is None:
            assert "Never generate player choice questions, option buttons or UI;" in instruction
            assert "runtime branching-choice UI" not in instruction
        else:
            assert "Never generate runtime branching-choice UI" in instruction
            assert "Nonverbal interface cues must follow the frozen physical presentation." in instruction
            assert "do not invent additional message text or replies" in instruction
            assert "complete exact UNSENT draft" in instruction
            assert "never the first image; no already-sent first image" in instruction
            assert "option buttons or UI;" not in instruction
    exchange.verify_package(**arguments)
