"""Offline strict transport DATA; only phase.json enters the mutable runtime."""
import json
from pathlib import Path

from handoff_files import (
    canonical,
    digest,
    exclusive_bytes,
    owned_root,
    parse,
    read_owned,
    require,
)
from handoff_source import ENTRY_REGISTRY


def prepare_transport(bundle_root, phase_root, *, authority, nonce):
    """Return plan/anchor bytes and independent pin without executing a target."""
    bundle, root = owned_root(bundle_root), owned_root(phase_root)
    require(not list(root.iterdir()), "transport runtime must be fresh and descriptor-only")
    require(bundle != root and bundle not in root.parents and root not in bundle.parents, "source/runtime roots overlap")
    require(authority in {"capability_check", "synthetic_unit", "provider_free_handoff", "paid_outline_once"},
        "unregistered transport authority")
    kind = "paid_outline" if authority == "paid_outline_once" else "handoff_proof_only"
    controls_raw = read_owned(bundle / "source-controls.json")
    controls = parse(controls_raw)
    qa = json.loads(read_owned(bundle / "qa-interpreter.json"))
    source = parse(read_owned(bundle / "source-identity.json"))
    require(controls["registry"] == ENTRY_REGISTRY and controls["sourceRoot"] == str(bundle)
        and controls["files"]["source-identity.json"] == digest(canonical(source)), "sealed source registry/identity differs")
    for name, sha in controls["files"].items():
        require(Path(name).name == name and digest(read_owned(bundle / name)) == sha, "sealed source closure differs")
    allocation_sha = None
    if kind == "paid_outline":
        from paid_outline_contracts import PaidOutlineAllocation
        raw = read_owned(bundle / "paid-allocation.json")
        allocation = PaidOutlineAllocation.model_validate(parse(raw))
        allocation_sha = digest(raw)
        require(source["committed"] and allocation.nonce == nonce
            and allocation.phase_root.path == str(root) and allocation.bundle_root.path == str(bundle)
            and allocation.source.bundle_source_identity_sha256 == controls["files"]["source-identity.json"]
            and allocation.validator_runtime.qa_pin_sha256 == controls["files"]["qa-interpreter.json"],
            "paid allocation is not bound to this transport")
    si, ri = bundle.lstat(), root.lstat()
    source_pin, root_pin = [si.st_dev, si.st_ino, si.st_uid], [ri.st_dev, ri.st_ino, ri.st_uid]
    template = [qa["entrypoint"], "-B", str(bundle / ENTRY_REGISTRY[kind]),
        "--phase-root", str(root), "--phase-sha", "@PHASE_SHA256@"]
    phase = {"version": 3, "kind": kind, "authority": authority, "phaseRoot": str(root), "rootIdentity": root_pin,
        "sourceRoot": str(bundle), "sourceIdentity": source_pin, "namespace": root.name, "nonce": nonce,
        "sourceRevision": source["revision"], "sourceTree": source["tree"], "controlsSha256": digest(controls_raw),
        "capsuleSha256": controls["capsuleSourceSha256"], "helperSha256": controls["files"]["node_helper.mjs"],
        "qaPinSha256": controls["files"]["qa-interpreter.json"], "allocationSha256": allocation_sha,
        "entryArgvTemplate": template, "settlementAuthority": "hold_only" if kind == "paid_outline" else "none"}
    phase_sha = exclusive_bytes(root, "phase.json", canonical(phase))
    argv = [phase_sha if item == "@PHASE_SHA256@" else item for item in template]
    command = " ".join("'" + item.replace("'", "'\\''") + "'" for item in argv)
    exec_args = {"cmd": command, "workdir": qa["projectRoot"], "shell": "/bin/zsh",
        "login": False, "yield_time_ms": 250, "max_output_tokens": 1000}
    plan = {"version": 3, "authority": authority, "kind": kind, "sourceRoot": str(bundle), "sourceIdentity": source_pin,
        "controlsSha256": phase["controlsSha256"], "phaseRoot": str(root), "phaseIdentity": root_pin,
        "phaseSha256": phase_sha, "allocationSha256": allocation_sha, "namespace": root.name,
        "nonce": nonce, "argv": argv, "argvSha256": digest(canonical(argv)), "execArgs": exec_args}
    plan_raw = canonical(plan)
    anchor = {"version": 3, "kind": "capsule_plan_anchor.v3", "authority": authority, "sourceRoot": str(bundle),
        "sourceIdentity": source_pin, "capsuleSha256": phase["capsuleSha256"], "planSha256": digest(plan_raw),
        "controlsSha256": phase["controlsSha256"], "helperSha256": phase["helperSha256"],
        "phaseSha256": phase_sha, "allocationSha256": allocation_sha}
    anchor_raw = canonical(anchor)
    return {"phase": phase, "phaseSha256": phase_sha, "planText": plan_raw.decode(),
        "anchorText": anchor_raw.decode(), "anchorSha256": digest(anchor_raw)}
