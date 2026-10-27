"""Immutable native qualification pauses and exact same-run resume ordering."""
import json
import os
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from pydantic import Field

from .alpha_campaign import private_directory, publish_sample_record, write_private_json
from .alpha_receipts import NativeSampleReceipt
from .autopilot_contracts import RunControlRequest, RunView
from .autopilot_exec import _identity
from .autopilot_launch import assert_frozen_execution
from .codex_exec_files import read_confined_regular_file
from .domain_base import CamelModel
from .generation.prompts import canonical_json


class QualificationResume(CamelModel):
    project_id: UUID
    run_id: UUID
    revision: int = Field(strict=True, ge=1)
    snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class PauseMetadata(CamelModel):
    runtime: dict
    elapsed_milliseconds: int = Field(strict=True, ge=0)


def read_record(path):
    path = Path(path)
    info = path.lstat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("qualification evidence must remain owner-only")
    return json.loads(read_confined_regular_file(path.parent, path.name, max_bytes=10_000_000))


def database_identity(path):
    path = Path(path)
    if not path.is_file() or path.resolve(strict=True) != path:
        raise ValueError("original qualification database is absent or aliased")
    info = path.stat()
    return {"path": str(path), "device": info.st_dev, "inode": info.st_ino}


def require_original_runtime(evidence):
    """Check incarnations before compose could initialize any missing state."""
    identity = read_record(Path(evidence) / "runtime.json")
    for item in identity["databases"].values():
        if database_identity(item["path"]) != item:
            raise ValueError("original qualification database incarnation changed")
    return identity


def pause_directories(evidence):
    root = Path(evidence) / "pauses"
    if not root.exists():
        return []
    if root.is_symlink() or root.resolve(strict=True) != root:
        raise ValueError("pause history cannot be aliased")
    # Interrupted staging has no snapshot authority and is never a pause entry.
    result = sorted((p for p in root.iterdir() if not p.name.startswith(".outcome-staging-")),
        key=lambda p: int(p.name) if p.name.isdecimal() else -1)
    if any(not p.name.isdecimal() or p.name != str(int(p.name)) or int(p.name) < 1
            or not p.is_dir() or p.is_symlink() for p in result):
        raise ValueError("invalid pause history inventory")
    return result


def pause_snapshot(path):
    path = Path(path)
    if (path.resolve(strict=True) != path or {p.name for p in path.iterdir()}
            != {"pause.json", "receipt.json", "bindings.private.json"}):
        raise ValueError("pause snapshot inventory differs")
    values = {name: read_record(path / name) for name in sorted(p.name for p in path.iterdir())}
    PauseMetadata.model_validate(values["pause.json"])
    NativeSampleReceipt.model_validate(values["receipt.json"])
    RunView.model_validate(values["bindings.private.json"]["run"])
    hashes = {name: sha256((canonical_json(value) + "\n").encode()).hexdigest() for name, value in values.items()}
    if any((path / name).read_bytes() != (canonical_json(value) + "\n").encode() for name, value in values.items()):
        raise ValueError("pause snapshot is not canonical immutable evidence")
    return values, sha256(canonical_json(hashes).encode()).hexdigest()


def recorded_duration(evidence):
    elapsed, identity = 0, None
    for path in pause_directories(evidence):
        values, _ = pause_snapshot(path)
        run, receipt, metadata = values["bindings.private.json"]["run"], values["receipt.json"], values["pause.json"]
        binding = (run["id"], run["projectId"], run["policy"], metadata["runtime"],
            receipt["commit"], receipt["contractHash"], receipt["profileHash"])
        if (receipt["sampleId"] != Path(evidence).name or run["revision"] != int(path.name)
                or run["state"] != "paused" or receipt["status"] != "incomplete"
                or identity is not None and binding != identity):
            raise ValueError("pause history sample/run/execution lineage differs")
        elapsed += metadata["elapsedMilliseconds"]
        if receipt["durationMilliseconds"] != elapsed:
            raise ValueError("pause history elapsed slices differ from cumulative receipt")
        identity = binding
    return elapsed


def publish_pause(evidence, *, receipt, bindings, runtime_identity, elapsed_ms):
    """Reuse a revision's exact bytes; host completion cannot rewrite the pause."""
    run = bindings["run"]
    if receipt["status"] != "incomplete" or run["state"] != "paused":
        raise ValueError("only a paused incomplete run is a qualification pause")
    root = private_directory(Path(evidence) / "pauses", create=True)
    target = root / str(run["revision"])
    if target.exists():
        values, digest = pause_snapshot(target)
        old = values["bindings.private.json"]["run"]
        if values["pause.json"]["runtime"] != runtime_identity or (old["id"], old["projectId"], old["revision"], old["policy"], old["checkpoints"]) != (
                run["id"], run["projectId"], run["revision"], run["policy"], run["checkpoints"]):
            raise ValueError("existing pause belongs to a different run or checkpoint")
        return target, digest
    if receipt["durationMilliseconds"] != recorded_duration(evidence) + elapsed_ms:
        raise ValueError("new pause must count each recorded elapsed slice once")
    publish_sample_record(target, {"receipt.json": receipt, "bindings.private.json": bindings,
        "pause.json": {"runtime": runtime_identity, "elapsedMilliseconds": elapsed_ms}})
    return target, pause_snapshot(target)[1]


def _same_run(view, saved):
    return (str(view.id), view.project_id, view.policy.model_dump(mode="json", by_alias=True), view.checkpoints) == (
        saved["id"], saved["projectId"], saved["policy"], saved["checkpoints"])


def _observe_sent(store, registry, view, directory):
    """Retain late host facts without adopting, settling or admitting anything."""
    observations = []
    for checkpoint in view.checkpoints:
        attempt, _ = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
        if checkpoint["state"] == "outcome_unknown" or (attempt and attempt.state == "outcome_unknown"):
            raise ValueError("UNKNOWN qualification work cannot resume")
        if attempt is None or checkpoint["state"] in {"adopted", "failed"}:
            continue
        status = registry.codex_exec_status(attempt.attempt_id)
        if (status.state in {"not_found", "outcome_unknown", "settled"} or status.attempt is None
                or _identity(status.attempt) != _identity(attempt)):
            raise ValueError("paused attempt is missing, settled, UNKNOWN or rebound")
        observations.append(status.model_dump(mode="json", by_alias=True))
    root = private_directory(directory / "drains", create=True)
    digest = sha256(canonical_json(observations).encode()).hexdigest()
    path = root / (digest + ".json")
    if path.exists():
        if read_record(path) != observations:
            raise ValueError("retained pause drain bytes differ")
    else:
        write_private_json(path, observations)


def resume_paused_sample(prefix, project_id, evidence, request, runtime_identity):
    """Durable intent → exact CAS → immutable ack, before any step or claim."""
    if prefix.service._descriptor is None:
        raise ValueError("qualification resume requires the production process lease")
    evidence = Path(evidence)
    if (evidence / "outcome").exists() or (evidence / "cancellation").exists():
        raise ValueError("terminal qualification evidence cannot resume")
    pauses = pause_directories(evidence)
    recorded_duration(evidence)
    if not pauses or pauses[-1].name != str(request.revision) or str(request.project_id) != project_id:
        raise ValueError("resume must identify the latest exact sample/project pause")
    values, digest = pause_snapshot(pauses[-1])
    saved = values["bindings.private.json"]["run"]
    receipt = values["receipt.json"]
    if (digest != request.snapshot_hash or saved["id"] != str(request.run_id)
            or saved["projectId"] != project_id or saved["revision"] != request.revision
            or saved["state"] != "paused" or receipt["status"] != "incomplete"
            or values["pause.json"]["runtime"] != runtime_identity
            or any(receipt[key] != runtime_identity[key] for key in ("commit", "profileHash", "contractHash"))):
        raise ValueError("resume snapshot/run/runtime binding differs")
    root = private_directory(evidence / "resumptions", create=True)
    directory = private_directory(root / str(request.revision), create=True)
    intent = request.model_dump(mode="json", by_alias=True)
    intent_file, ack_file = directory / "intent.json", directory / "ack.json"
    if intent_file.exists() and read_record(intent_file) != intent:
        raise ValueError("resume intent binding differs")
    with closing(prefix.storage.projects.open(project_id)) as store:
        view = store.repository.autopilot.current(project_id)
        if (view is None or view.id != str(request.run_id) or not view.material_current
                or store.repository.operational_state()[0] != "open"
                or store.project().lifecycle_status.value != "active"):
            raise ValueError("resume requires the original current active project/run")
        if receipt["sampleId"] != evidence.name or any(c["operationKey"] == "installation" for c in view.checkpoints):
            raise ValueError("resume sample binding differs or already reached installation")
        assert_frozen_execution(store, prefix.service.registry, view.policy)
        if (view.policy.code_revision != receipt["commit"]
                or view.policy.executor_binding.profile_hash != receipt["profileHash"]):
            raise ValueError("pause source/profile differs from the original launch")
        if ack_file.exists():
            ack = read_record(ack_file)
            if (not intent_file.exists() or ack != intent | {"resumedRevision": request.revision + 1}
                    or view.state not in {"running", "waiting"} or view.revision < request.revision + 1
                    or view.policy.model_dump(mode="json", by_alias=True) != saved["policy"]):
                raise ValueError("acknowledged resume no longer matches this active run")
            _observe_sent(store, prefix.service.registry, view, directory)
            return view
        if not _same_run(view, saved) or (view.state, view.revision) not in {
                ("paused", request.revision), ("running", request.revision + 1)}:
            raise ValueError("pending resume is neither its original pause nor exact CAS result")
        if not intent_file.exists() and view.state != "paused":
            raise ValueError("running run has no durable qualification resume intent")
        _observe_sent(store, prefix.service.registry, view, directory)
    if not intent_file.exists():
        write_private_json(intent_file, intent)
    if view.state == "paused":
        view = prefix.service.control(project_id,
            RunControlRequest(action="resume", expected_revision=request.revision), expected_run_id=str(request.run_id))
    write_private_json(ack_file, intent | {"resumedRevision": request.revision + 1})
    return view
