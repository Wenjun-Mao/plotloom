"""Actual shared v3 receiver contracts; all process/handle data are synthetic fixtures."""
import copy
import os
from pathlib import Path

import pytest

from tests.cli_handoff_fixtures import (
    capsule_bundle as _capsule_bundle,  # noqa: F401 -- explicit named pytest fixture registration
)
from tests.cli_handoff_fixtures import (
    capsule_modules as _capsule_modules,  # noqa: F401
)
from tests.cli_handoff_fixtures import (
    receiver_context as _receiver_context,  # noqa: F401
)


def test_receiver_valid_complete_commit_publishes_correlated_witness(receiver_context):
    c = receiver_context
    c["commit"]()
    value, witness = c["accept"]()
    assert value["nativeExecHandle"] == 42
    assert witness["phaseSha256"] == c["phase_sha"]
    assert int(witness["acceptedMonotonicNs"]) < int(witness["deadlineMonotonicNs"])
    assert witness["productionAuthority"] is False and witness["providerAuthority"] is False
    assert witness["syntheticEvidence"] is True
    assert all(witness[key] == c["value"][key] for key in ("anchorSha256", "planSha256", "argvSha256", "intentSha256"))
    assert witness["sourceRoot"] == str(c["bundle"]) and witness["phaseRoot"] == str(c["root"])
    assert (c["root"] / "receiver-accepted.json").is_file()


@pytest.mark.parametrize("scenario", ["partial", "complete", "absent"])
def test_receiver_payload_without_commit_is_never_read(receiver_context, monkeypatch, scenario):
    c = receiver_context
    if scenario != "absent":
        c["files"].exclusive_bytes(c["root"], "attendance.json", b"{" if scenario == "partial" else c["files"].canonical(c["value"]))
    actual = c["receiver"].read_owned

    def guarded(path, **kwargs):
        assert Path(path).name != "attendance.json", "uncommitted payload was read"
        return actual(path, **kwargs)

    monkeypatch.setattr(c["receiver"], "read_owned", guarded)
    with pytest.raises(TimeoutError):
        c["accept"]()
    assert not (c["root"] / "receiver-accepted.json").exists()


@pytest.mark.parametrize("field", ["anchorSha256", "planSha256", "argvSha256", "authority"])
def test_receiver_rejects_new_anchor_plan_argv_authority_drift(receiver_context, field):
    c = receiver_context
    value = copy.deepcopy(c["value"])
    value[field] = "wrong"
    c["commit"](value)
    with pytest.raises(RuntimeError, match="authority mismatch"):
        c["accept"]()


@pytest.mark.parametrize("scenario", ["boolean-version", "boolean-identity", "source-root", "paid-runtime-entry", "settlement"])
def test_shared_descriptor_rejects_invalid_source_runtime_contract(receiver_context, scenario):
    c = receiver_context
    phase = copy.deepcopy(c["phase"])
    if scenario == "boolean-version":
        phase["version"] = True
    elif scenario == "boolean-identity":
        phase["rootIdentity"][0] = True
    elif scenario == "source-root":
        phase["sourceRoot"] = str(c["root"])
    elif scenario == "paid-runtime-entry":
        phase["entryArgvTemplate"][2] = str(c["root"] / "launch.py")
    else:
        phase["settlementAuthority"] = "complete"
    with pytest.raises(RuntimeError):
        c["binding"].validate_descriptor(phase, c["root"], "handoff_proof_only", c["phase"]["rootIdentity"])


def test_registered_paid_entry_cannot_use_proof_authority(receiver_context):
    c = receiver_context
    for kind, name in (("handoff_proof_only", "proof_launch.py"), ("paid_outline", "paid_launch.py")):
        argv = c["binding"].entry_argv(kind, c["root"], c["phase_sha"])
        assert argv[1:] == ["-B", str(c["bundle"] / name), "--phase-root", str(c["root"]), "--phase-sha", c["phase_sha"]]
    phase = copy.deepcopy(c["phase"])
    phase["kind"], phase["settlementAuthority"] = "paid_outline", "hold_only"
    phase["entryArgvTemplate"] = c["binding"].entry_argv("paid_outline", c["root"], "@PHASE_SHA256@")
    raw = c["files"].canonical(phase)
    (c["root"] / "phase.json").write_bytes(raw)
    with pytest.raises(RuntimeError, match="proof and paid allocation authority must remain distinct"):
        c["binding"].load_phase(c["root"], c["files"].digest(raw), expected_kind="paid_outline")
    assert (c["bundle"] / "paid_launch.py").is_file()
    assert (c["bundle"] / "paid_receiver.py").is_file()


@pytest.mark.parametrize("field,value", [("invocationCount", True), ("version", True), ("argvSha256", "0" * 64), ("capsuleSha256", "0" * 64)])
def test_intent_strict_identity_and_argv(receiver_context, field, value):
    c = receiver_context
    intent = copy.deepcopy(c["intent"])
    intent[field] = value
    with pytest.raises(RuntimeError):
        c["binding"].validate_intent(intent, c["phase"], c["phase_sha"])


@pytest.mark.parametrize("scenario", ["nonempty", "symlink", "hardlink", "mode", "owner", "hash", "multiple", "malformed", "directory"])
def test_receiver_rejects_marker_metadata(receiver_context, monkeypatch, scenario):
    c = receiver_context
    marker = c["commit"]()
    if scenario == "nonempty":
        marker.write_bytes(b"x")
    elif scenario == "symlink":
        marker.unlink()
        target = c["root"] / "empty-target"
        target.write_bytes(b"")
        target.chmod(0o600)
        marker.symlink_to(target)
    elif scenario == "hardlink":
        os.link(marker, c["root"] / "second-link")
    elif scenario == "mode":
        marker.chmod(0o644)
    elif scenario == "owner":
        original = Path.lstat

        def changed_owner(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if path == marker:
                fields = list(info)
                fields[4] = info.st_uid + 1
                return os.stat_result(fields)
            return info

        monkeypatch.setattr(Path, "lstat", changed_owner)
    elif scenario == "hash":
        marker.rename(c["root"] / ("attendance.commit-" + "0" * 64))
    elif scenario == "multiple":
        c["files"].exclusive_bytes(c["root"], "attendance.commit-" + "0" * 64, b"")
    elif scenario == "malformed":
        marker.rename(c["root"] / "attendance.commit-invalid")
    elif scenario == "directory":
        marker.unlink()
        marker.mkdir(mode=0o700)
    with pytest.raises((RuntimeError, OSError)):
        c["accept"]()
    assert not (c["root"] / "receiver-accepted.json").exists()


@pytest.mark.parametrize("scenario", ["boolean-version", "float-version", "string-version", "extra-field", "missing-field",
    "wrong-phase", "paid-kind", "namespace", "nonce", "intent", "launch", "driver", "controls", "critical-body", "helper-body",
    "boolean-handle", "zero-handle", "boolean-process-scalar"])
def test_receiver_rejects_payload_contract(receiver_context, scenario):
    c = receiver_context
    value = copy.deepcopy(c["value"])
    fields = {"wrong-phase": "phaseSha256", "namespace": "namespace", "nonce": "nonce", "intent": "intentSha256",
        "launch": "launchSha256", "driver": "driverProcessSha256", "controls": "controlsSha256",
        "critical-body": "capsuleSha256", "helper-body": "helperSha256"}
    if scenario in fields:
        value[fields[scenario]] = "wrong"
    elif scenario == "boolean-version":
        value["version"] = True
    elif scenario == "float-version":
        value["version"] = 1.0
    elif scenario == "string-version":
        value["version"] = "1"
    elif scenario == "extra-field":
        value["extra"] = True
    elif scenario == "missing-field":
        del value["nonce"]
    elif scenario == "paid-kind":
        value["phaseKind"] = "paid_outline"
    elif scenario == "boolean-handle":
        value["nativeExecHandle"] = True
    elif scenario == "zero-handle":
        value["nativeExecHandle"] = 0
    elif scenario == "boolean-process-scalar":
        value["observedTree"]["launcher"]["ppid"] = True
    c["commit"](value)
    with pytest.raises(RuntimeError):
        c["accept"]()
    assert not (c["root"] / "receiver-accepted.json").exists()


@pytest.mark.parametrize("scenario", ["mutation", "symlink", "hardlink", "mode", "duplicate-json"])
def test_receiver_rejects_payload_storage(receiver_context, scenario):
    c = receiver_context
    if scenario == "duplicate-json":
        c["commit"](raw=c["files"].canonical(c["value"]).replace(b'"version":3', b'"version":3,"version":3'))
    else:
        c["commit"]()
        payload = c["root"] / "attendance.json"
        if scenario == "mutation":
            payload.write_bytes(b"{}\n")
        elif scenario == "symlink":
            payload.rename(c["root"] / "payload-target")
            payload.symlink_to(c["root"] / "payload-target")
        elif scenario == "hardlink":
            os.link(payload, c["root"] / "payload-link")
        elif scenario == "mode":
            payload.chmod(0o644)
    with pytest.raises((RuntimeError, OSError)):
        c["accept"]()
    assert not (c["root"] / "receiver-accepted.json").exists()


@pytest.mark.parametrize("scenario", ["before-read", "arriving-late", "after-marker", "after-payload"])
def test_receiver_deadline_never_accepts_late_authority(receiver_context, monkeypatch, scenario):
    c = receiver_context
    if scenario != "arriving-late":
        c["commit"]()
    if scenario == "before-read":
        c["state"]["now"] = 61_000_000_000
    original = c["receiver"].read_owned

    def advance_after_read(path, **kwargs):
        result = original(path, **kwargs)
        if (scenario == "after-marker" and Path(path).name.startswith("attendance.commit-")) or (
                scenario == "after-payload" and Path(path).name == "attendance.json"):
            c["state"]["now"] = 61_000_000_000
        return result

    monkeypatch.setattr(c["receiver"], "read_owned", advance_after_read)

    def late(_seconds):
        c["commit"]()
        c["state"]["now"] = 61_000_000_000

    with pytest.raises(TimeoutError):
        c["accept"](wait=late if scenario == "arriving-late" else None)
    assert not (c["root"] / "receiver-accepted.json").exists()


def test_receiver_rejects_marker_identity_change_during_payload_read(receiver_context, monkeypatch):
    c = receiver_context
    marker = c["commit"]()
    original = c["receiver"].read_owned

    def change_after_read(path, **kwargs):
        result = original(path, **kwargs)
        if Path(path).name == "attendance.json":
            marker.unlink()
            c["files"].exclusive_bytes(c["root"], marker.name, b"")
        return result

    monkeypatch.setattr(c["receiver"], "read_owned", change_after_read)
    with pytest.raises(RuntimeError, match="identity changed"):
        c["accept"]()


def test_receiver_rejects_second_marker_during_actual_payload_read(receiver_context, monkeypatch):
    c = receiver_context
    c["commit"]()
    original = c["receiver"].read_owned

    def insert_marker(path, **kwargs):
        result = original(path, **kwargs)
        if Path(path).name == "attendance.json":
            c["files"].exclusive_bytes(c["root"], "attendance.commit-" + "0" * 64, b"")
        return result

    monkeypatch.setattr(c["receiver"], "read_owned", insert_marker)
    with pytest.raises(RuntimeError, match="authority set changed"):
        c["accept"]()
    assert not (c["root"] / "receiver-accepted.json").exists()


def test_record_rejects_second_marker_during_actual_payload_read(receiver_context, monkeypatch):
    c = receiver_context
    c["files"].publish_record(c["root"], "synthetic-record.json", {"nonsecret": True})
    original = c["files"].read_owned

    def insert_marker(path, **kwargs):
        result = original(path, **kwargs)
        if Path(path).name == "synthetic-record.json":
            c["files"].exclusive_bytes(c["root"], "synthetic-record.json.ready-" + "0" * 64, b"")
        return result

    monkeypatch.setattr(c["files"], "read_owned", insert_marker)
    with pytest.raises(RuntimeError, match="authority set changed"):
        c["files"].read_record(c["root"], "synthetic-record.json")
    assert not (c["root"] / "receiver-accepted.json").exists()

