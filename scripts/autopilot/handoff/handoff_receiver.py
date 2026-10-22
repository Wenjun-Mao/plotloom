"""Shared complete-payload/empty-commit receiver; synthetic evidence stays labeled."""
import re
import time

from handoff_files import (
    canonical,
    digest,
    identity,
    owned_root,
    parse,
    publish_record,
    read_owned,
    read_record,
    require,
)
from handoff_phase import assert_origins, validate_intent
from handoff_process import validate_tree

PAYLOAD_FIELDS = {"version", "authority", "phaseSha256", "phaseKind", "namespace", "nonce", "intentSha256",
    "planSha256", "anchorSha256", "argvSha256", "launchSha256", "driverProcessSha256", "controlsSha256",
    "capsuleSha256", "helperSha256", "allocationSha256", "nativeExecHandle", "observedTree"}


def accept_attendance(phase, phase_sha, launch, tree, *, clock=time.monotonic_ns,
        wait=time.sleep, stopped=lambda: False):
    assert_origins()
    root = owned_root(phase["phaseRoot"])
    info = root.lstat()
    require(phase["rootIdentity"] == [info.st_dev, info.st_ino, info.st_uid], "receiver namespace identity changed")
    require(type(launch["startedMonotonicNs"]) is str
        and re.fullmatch(r"[1-9][0-9]*", launch["startedMonotonicNs"]), "original monotonic start required")
    deadline = int(launch["startedMonotonicNs"]) + 60_000_000_000

    def gate():
        require(not stopped(), "operator stopped")
        if clock() >= deadline:
            raise TimeoutError("original native handle attachment deadline")

    gate()
    validate_tree(launch, tree)
    intent_record = read_record(root, "invocation-intent.json", gate=gate)
    require(intent_record is not None, "missing committed invocation intent")
    intent = validate_intent(intent_record[0], phase, phase_sha)
    expected = {"version": 3, "authority": phase["authority"], "phaseSha256": phase_sha,
        "phaseKind": phase["kind"], "namespace": phase["namespace"], "nonce": phase["nonce"],
        "intentSha256": intent_record[1], "planSha256": intent["planSha256"],
        "anchorSha256": intent["anchorSha256"], "argvSha256": intent["argvSha256"],
        "launchSha256": digest(read_owned(root / "launch.json")),
        "driverProcessSha256": digest(read_owned(root / "driver-process.json")),
        "controlsSha256": phase["controlsSha256"], "capsuleSha256": phase["capsuleSha256"],
        "helperSha256": phase["helperSha256"], "allocationSha256": phase["allocationSha256"], "observedTree": tree}
    require(launch["phaseSha256"] == phase_sha and launch["intentSha256"] == intent_record[1]
        and tree["launchSha256"] == expected["launchSha256"], "receiver record binding")
    while True:
        gate()
        names = [p.name for p in root.iterdir() if p.name.startswith("attendance.commit-")]
        gate()
        if names:
            break
        wait(min(0.02, max(0, (deadline - clock()) / 1_000_000_000)))
    require(len(names) == 1, "multiple attendance authorities")
    suffix = names[0][len("attendance.commit-"):]
    require(re.fullmatch(r"[0-9a-f]{64}", suffix), "bad attendance marker")
    marker_identity = identity((root / names[0]).lstat())
    require(read_owned(root / names[0]) == b"", "attendance marker must be empty")
    gate()
    payload_identity = identity((root / "attendance.json").lstat())
    raw = read_owned(root / "attendance.json")
    require(digest(raw) == suffix, "attendance payload changed")
    value = parse(raw)
    require(set(value) == PAYLOAD_FIELDS and type(value["version"]) is int and value["version"] == 3,
        "strict attendance schema/version required")
    require(canonical({key: value[key] for key in expected}) == canonical(expected), "attendance authority mismatch")
    require(type(value["nativeExecHandle"]) is int and value["nativeExecHandle"] > 0, "actual original handle required")
    gate()
    final_names = [p.name for p in root.iterdir() if p.name.startswith("attendance.commit-")]
    require(final_names == names, "attendance authority set changed during payload read")
    gate()
    require(marker_identity == identity((root / names[0]).lstat())
        and payload_identity == identity((root / "attendance.json").lstat()), "attendance identity changed before acceptance")
    info = root.lstat()
    require(phase["rootIdentity"] == [info.st_dev, info.st_ino, info.st_uid], "receiver namespace identity changed")
    accepted = clock()
    gate()
    witness = {key: value[key] for key in value if key not in {"observedTree", "namespace", "nonce"}}
    witness.update({"sourceRoot": phase["sourceRoot"], "phaseRoot": phase["phaseRoot"],
        "namespace": phase["namespace"], "nonce": phase["nonce"],
        "attendanceSha256": suffix, "acceptedMonotonicNs": str(accepted), "deadlineMonotonicNs": str(deadline),
        "productionAuthority": False, "providerAuthority": False,
        "syntheticEvidence": phase["authority"] == "synthetic_unit"})
    publish_record(root, "receiver-accepted.json", witness)
    gate()
    return value, witness
