"""Validate and publish one schema-v3 image completion marker."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plotloom.image_job_contracts import (
    ImageDeliveryManifest,
    NativeTaskBinding,
)

EXECUTION_CONTRACT = "codex_specialist.v3"
PREFLIGHT_VERSION = "p1.5-pin.v2"
SKILL_VERSION = "plotloom-image-specialist.v4"


def _read_json(path: Path) -> dict:
    details = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise ValueError(f"Expected a regular, non-symlink file: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object: {path.name}")
    return value


def _canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _publish_once(directory: Path, filename: str, content: bytes) -> None:
    directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    temporary_path: Path | None = None
    file_fd = None
    try:
        file_fd, temporary_name = tempfile.mkstemp(prefix=".completion-publish-", dir=directory.parent)
        temporary_path = Path(temporary_name)
        view = memoryview(content)
        while view:
            view = view[os.write(file_fd, view):]
        os.fsync(file_fd)
        os.close(file_fd)
        file_fd = None
        # A hard link publishes fully written bytes atomically and fails if a
        # completion marker already exists. The temporary file is outside the
        # delivery directory, so observers never see a partial marker.
        os.link(temporary_path, filename, dst_dir_fd=directory_fd, follow_symlinks=False)
        os.fsync(directory_fd)
    except FileExistsError as error:
        raise ValueError("completion.json already exists; never overwrite a published receipt") from error
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
        os.close(directory_fd)


def publish(package: Path, manifest_path: Path) -> Path:
    package = package.resolve(strict=True)
    delivery = package.parent / "delivery"
    if manifest_path.parent.resolve(strict=True) != delivery.resolve(strict=True) or manifest_path.name != "completion-draft.json":
        raise ValueError("manifest must be delivery/completion-draft.json")
    if delivery.is_symlink() or not delivery.is_dir():
        raise ValueError("delivery must be a regular directory")

    request = _read_json(package / "request.json")
    if (
        request.get("schemaVersion") != 3
        or request.get("packageVersion") != 6
        or request.get("executionContract") != EXECUTION_CONTRACT
        or request.get("specialistPreflight", {}).get("version") != PREFLIGHT_VERSION
        or request.get("specialistPreflight", {}).get("skillVersion") != SKILL_VERSION
    ):
        raise ValueError("package does not use the schema-v3 image identity contract")
    binding = NativeTaskBinding.model_validate(request.get("nativeTaskBinding"))

    pin = _read_json(delivery / "executor-pin.json")
    if set(pin) != {"jobId", "requestHash", "executionContract", "skillVersion", "codeRevision", "skillHash", "nativeTaskId"}:
        raise ValueError("executor pin has an unsupported shape")
    native_task_id = str(UUID(pin["nativeTaskId"]))
    current_task_id = str(UUID(os.environ["CODEX_THREAD_ID"]))
    if native_task_id != current_task_id:
        raise ValueError("current CODEX_THREAD_ID differs from the pre-generation executor pin")
    if binding.mode == "configured_task" and str(binding.task_id) != native_task_id:
        raise ValueError("pre-generation executor pin differs from the configured native task UUID")
    if (
        pin["jobId"] != request.get("jobId")
        or pin["requestHash"] != request.get("requestHash")
        or pin["executionContract"] != EXECUTION_CONTRACT
        or pin["skillVersion"] != SKILL_VERSION
        or request["specialistPreflight"].get("codeRevision") not in {None, pin["codeRevision"]}
        or request["specialistPreflight"].get("skillHash") not in {None, pin["skillHash"]}
    ):
        raise ValueError("executor pin does not match the frozen image package")

    raw_manifest = _read_json(manifest_path)
    manifest = ImageDeliveryManifest.model_validate(raw_manifest)
    manifest.assert_secret_free()
    evidence = manifest.tool_evidence
    provenance = manifest.executor_provenance
    if (
        manifest.schema_version != 3
        or manifest.job_id != request.get("jobId")
        or manifest.request_hash != request.get("requestHash")
        or str(evidence.native_task_id) != native_task_id
        or evidence.image_gen_execution_id == native_task_id
        or provenance is None
        or provenance.code_revision != pin["codeRevision"]
        or provenance.skill_version != pin["skillVersion"]
        or provenance.skill_hash != pin["skillHash"]
    ):
        raise ValueError("completion draft does not match the native task, ImageGen execution, package, or pin")

    outputs = delivery / "outputs"
    if outputs.is_symlink() or not outputs.is_dir():
        raise ValueError("delivery/outputs must be a regular directory")
    declared = {item.filename: item.sha256 for item in manifest.outputs}
    if {item.name for item in outputs.iterdir()} != set(declared):
        raise ValueError("output files must exactly match the completion draft")
    for filename, expected_hash in declared.items():
        path = outputs / filename
        details = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise ValueError(f"Output must be a regular, non-symlink file: {filename}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Output hash differs from completion draft: {filename}")

    expected_entries = {"outputs", "executor-pin.json", "completion-draft.json"}
    if {item.name for item in delivery.iterdir()} != expected_entries:
        raise ValueError("delivery contains unexpected files before completion publication")
    target = delivery / "completion.json"
    if target.exists() or target.is_symlink():
        raise ValueError("completion.json already exists; never overwrite a published receipt")

    encoded = _canonical_json(manifest.model_dump(mode="json", by_alias=True, exclude_none=True))
    _publish_once(delivery, target.name, encoded)
    # The marker is already complete and authoritative. Keep the draft if
    # cleanup is interrupted; schema-v3 readers recognize only an equivalent
    # leftover draft as publisher staging.
    try:
        manifest_path.unlink()
    except OSError:
        pass
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and publish one pinned Plotloom image completion manifest.")
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        target = publish(args.package, args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Image completion was not published: {error}") from error
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
