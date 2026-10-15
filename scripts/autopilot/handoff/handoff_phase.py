"""One immutable entry registry and distinct descriptor-only runtime roots."""
import json
import re
import sys
from pathlib import Path

from handoff_files import canonical, digest, owned_root, parse, read_owned, require
from handoff_source import ENTRY_REGISTRY, RECEIVER_REGISTRY

B = Path(__file__).absolute().parent
QA = json.loads(read_owned(B / "qa-interpreter.json"))
R = Path(QA["projectRoot"])
REGISTRY = ENTRY_REGISTRY
RECEIVERS = RECEIVER_REGISTRY
AUTHORITIES = {"capability_check", "synthetic_unit", "provider_free_handoff", "paid_outline_once"}
FIELDS = {"version", "kind", "authority", "phaseRoot", "rootIdentity", "sourceRoot", "sourceIdentity",
    "namespace", "nonce", "sourceRevision", "sourceTree", "controlsSha256", "capsuleSha256",
    "helperSha256", "qaPinSha256", "allocationSha256", "entryArgvTemplate", "settlementAuthority"}
CONTROL_FIELDS = {"version", "kind", "sourceRoot", "sourceIdentity", "sourceRevision", "sourceTree",
    "files", "registry", "builtinImports", "capsuleSourceSha256", "helperExportSha256"}
BUILTINS = ["node:fs/promises", "node:fs", "node:crypto", "node:os", "node:path", "node:url"]


def hash_value(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def root_identity(value):
    return type(value) is list and len(value) == 3 and all(type(v) is int and v >= 0 for v in value)


def entry_argv(kind, root, phase_sha, *, source_root=B):
    require(kind in REGISTRY, "unregistered phase kind")
    return [QA["entrypoint"], "-B", str(Path(source_root) / REGISTRY[kind]),
        "--phase-root", str(root), "--phase-sha", phase_sha]


def validate_descriptor(phase, root, expected_kind, identity, *, source_root=B, source_identity=None):
    require(type(phase) is dict and set(phase) == FIELDS, "unexpected descriptor fields")
    root, source_root = Path(root), Path(source_root)
    require(type(phase["version"]) is int and phase["version"] == 3
        and expected_kind in REGISTRY and phase["kind"] == expected_kind
        and phase["authority"] in AUTHORITIES, "phase version/kind/authority")
    require((phase["authority"] == "paid_outline_once") == (expected_kind == "paid_outline")
        and (hash_value(phase["allocationSha256"]) if expected_kind == "paid_outline" else phase["allocationSha256"] is None),
        "proof and paid allocation authority must remain distinct")
    require(root.is_absolute() and source_root.is_absolute() and root != source_root
        and source_root not in root.parents and root not in source_root.parents
        and phase["phaseRoot"] == str(root) and phase["sourceRoot"] == str(source_root)
        and phase["namespace"] == root.name, "source/runtime path binding")
    require(root_identity(phase["rootIdentity"]) and phase["rootIdentity"] == list(identity)
        and root_identity(phase["sourceIdentity"]), "strict root identities required")
    if source_identity is not None:
        require(phase["sourceIdentity"] == list(source_identity), "source root identity changed")
    require(type(phase["nonce"]) is str and re.fullmatch(r"[a-z0-9-]{16,100}", phase["nonce"])
        and type(phase["sourceRevision"]) is str and re.fullmatch(r"[a-f0-9]{40}", phase["sourceRevision"])
        and type(phase["sourceTree"]) is str and re.fullmatch(r"[a-f0-9]{40}", phase["sourceTree"]), "source/nonce binding")
    require(all(hash_value(phase[key]) for key in
        ("controlsSha256", "capsuleSha256", "helperSha256", "qaPinSha256")), "invalid descriptor hashes")
    require(phase["entryArgvTemplate"] == entry_argv(expected_kind, root, "@PHASE_SHA256@", source_root=source_root)
        and phase["settlementAuthority"] == ("hold_only" if expected_kind == "paid_outline" else "none"),
        "exact registered entry/settlement changed")


def assert_origins():
    for name in ("handoff_files", "handoff_phase", "handoff_process", "handoff_receiver", "handoff_qa",
            "handoff_source", "handoff_launch", "paid_outline_contracts", "paid_outline_prepare",
            "paid_outline_state", "paid_outline_composition", "paid_outline_run"):
        module = sys.modules.get(name)
        if module is not None:
            require(Path(module.__file__).absolute() == B / (name + ".py"), "workflow import origin changed")


def load_phase(root, expected_sha, *, expected_kind):
    assert_origins()
    require(hash_value(expected_sha), "invalid descriptor pin")
    owned_root(B)
    root = owned_root(root)
    raw = read_owned(root / "phase.json")
    require(digest(raw) == expected_sha, "phase descriptor hash changed")
    phase = parse(raw)
    bi, ri = B.lstat(), root.lstat()
    validate_descriptor(phase, root, expected_kind, (ri.st_dev, ri.st_ino, ri.st_uid),
        source_identity=(bi.st_dev, bi.st_ino, bi.st_uid))
    controls_raw = read_owned(B / "source-controls.json")
    require(digest(controls_raw) == phase["controlsSha256"], "source controls hash changed")
    controls = parse(controls_raw)
    require(set(controls) == CONTROL_FIELDS and type(controls["version"]) is int and controls["version"] == 3
        and controls["kind"] == "capsule_source_controls.v3" and controls["sourceRoot"] == str(B)
        and canonical(controls["sourceIdentity"]) == canonical(phase["sourceIdentity"])
        and controls["sourceRevision"] == phase["sourceRevision"]
        and controls["sourceTree"] == phase["sourceTree"] and controls["registry"] == REGISTRY
        and controls["builtinImports"] == BUILTINS, "source controls contract")
    require(type(controls["files"]) is dict and {p.name for p in B.iterdir()}
        == {*controls["files"], "source-controls.json"}, "source closure inventory changed")
    for name, sha in controls["files"].items():
        require(Path(name).name == name and hash_value(sha) and digest(read_owned(B / name)) == sha,
            "source closure changed: " + name)
    require(REGISTRY[expected_kind] in controls["files"], "actual registered entry unavailable")
    require(phase["capsuleSha256"] == controls["capsuleSourceSha256"]
        and phase["helperSha256"] == controls["files"]["node_helper.mjs"]
        and phase["qaPinSha256"] == controls["files"]["qa-interpreter.json"], "source body/QA binding changed")
    from handoff_source import source_identity
    source = parse(read_owned(B / "source-identity.json"))
    require(source == source_identity(R, require_committed=expected_kind == "paid_outline")
        and source["revision"] == phase["sourceRevision"] and source["tree"] == phase["sourceTree"],
        "actual owner source identity changed")
    if expected_kind == "paid_outline":
        from paid_outline_contracts import PaidOutlineAllocation
        raw = read_owned(B / "paid-allocation.json")
        require(digest(raw) == phase["allocationSha256"], "paid allocation body changed")
        allocation = PaidOutlineAllocation.model_validate(parse(raw))
        require(allocation.bundle_root.path == str(B) and allocation.phase_root.path == str(root)
            and allocation.nonce == phase["nonce"] and allocation.source.revision == source["revision"]
            and allocation.source.tree == source["tree"]
            and allocation.source.bundle_source_identity_sha256 == digest(canonical(source))
            and allocation.validator_runtime.qa_pin_sha256 == phase["qaPinSha256"], "paid source/phase/QA binding changed")
    return phase


def validate_intent(intent, phase, phase_sha):
    fields = {"version", "phaseSha256", "planSha256", "anchorSha256", "authority", "capsuleSha256",
        "controlsSha256", "helperSha256", "allocationSha256", "argvSha256", "invocationCount"}
    require(type(intent) is dict and set(intent) == fields and type(intent["version"]) is int
        and intent["version"] == 3 and type(intent["invocationCount"]) is int
        and intent["invocationCount"] == 1 and intent["phaseSha256"] == phase_sha
        and intent["authority"] == phase["authority"] and intent["allocationSha256"] == phase["allocationSha256"],
        "committed invocation intent contract")
    require(all(hash_value(intent[key]) for key in fields if key.endswith("Sha256") and key != "allocationSha256"), "invalid intent pins")
    require(all(intent[key] == phase[key] for key in ("capsuleSha256", "controlsSha256", "helperSha256"))
        and intent["argvSha256"] == digest(canonical(entry_argv(phase["kind"], phase["phaseRoot"], phase_sha))),
        "intent source/argv binding")
    return intent
