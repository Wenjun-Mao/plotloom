"""Marked Art shape results followed by the unchanged Node semantic boundary."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "src"))

from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_issues, require_art_structure_artifact
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.creative_handoff_identity import canonical_json
from plotloom.text_correction_contracts import CONTENT_DIAGNOSTIC_COUNT, CONTENT_DIAGNOSTIC_LENGTH


def _json(data):
    def invalid_constant(_value):
        raise ValueError("invalid JSON constant")
    return json.loads(data, parse_constant=invalid_constant)


def _file(raw):
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path or not path.is_file():
        raise ValueError("Art validation requires physical absolute files")
    return path


def frozen_context(request_path, node):
    request = _json(request_path.read_text(encoding="utf-8"))
    if request.get("stage") != "art" or request.get("contentValidationContract") != "plotloom.typed-content-result.v1":
        raise ValueError("marked Art typed request required")
    artifacts = request["inputArtifacts"]
    contract = artifacts["art-style-contract.json"]
    if not isinstance(contract, dict):
        raise ValueError("frozen Art authority must be an object")
    preset = "authority" not in contract
    require_art_structure_artifact(artifacts[ART_STRUCTURE_FILENAME], preset=preset)
    for name, value in artifacts.items():
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\.json", name):
            raise ValueError("invalid frozen Art input filename")
        copied = _json(_file(request_path.parent / "inputs" / name).read_text(encoding="utf-8"))
        if canonical_json(copied) != canonical_json(value):
            raise ValueError("frozen Art input differs from its request")
    cast = artifacts["cast.json"]
    if not isinstance(cast, (dict, list)):
        raise ValueError("frozen Art cast context is unavailable")
    characters = cast.get("characters", []) if isinstance(cast, dict) else cast
    if not isinstance(characters, list) or any(isinstance(c, dict) and
            not isinstance(c.get("aliases", []), (list, str, type(None))) for c in characters):
        raise ValueError("frozen Art cast context is not safely iterable")
    if preset:
        observed = subprocess.run([str(node), str(SOURCE / "scripts/art-style.mjs"), "contract",
            "--style", contract["style"], "--author-direction", json.dumps(contract["authorDirection"])],
            capture_output=True, check=True, timeout=30)
        expected = json.loads(observed.stdout)
    else:
        if contract.get("authority") != "saved_brief" or not isinstance(contract.get("direction"), (str, type(None))):
            raise ValueError("unsupported frozen Art style authority")
        expected = freeze_brief_style(contract.get("direction"))
    if canonical_json(expected) != canonical_json(contract):
        raise ValueError("frozen Art style contract is not current")
    correction = request.get("textCorrection")
    if correction is not None:
        prior = correction["priorCandidateJson"]
        if (not isinstance(prior, str) or len(prior.encode("utf-8")) > 500_000
                or sha256(prior.encode("utf-8")).hexdigest() != correction["rejection"]["candidateHash"]
                or not isinstance(_json(prior), dict)):
            raise ValueError("Art correction prior bytes differ")
    return preset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("--request", required=True)
    parser.add_argument("--node", required=True)
    args = parser.parse_args(argv)
    node = _file(args.node)
    if not os.access(node, os.X_OK):
        raise ValueError("frozen Node tool is not executable")
    version = subprocess.run([str(node), "--version"], capture_output=True, check=True, timeout=5)
    if not re.fullmatch(rb"v[0-9]+\.[0-9]+\.[0-9]+[^\r\n]*\r?\n?", version.stdout) or version.stderr:
        raise ValueError("frozen Node runtime is unavailable")
    request = _file(args.request)
    raw = _file(args.candidate).read_bytes()
    candidate = _json(raw.decode("utf-8", "strict"))  # Parser failures never grant correction.
    preset = frozen_context(request, node)
    diagnostics = art_structure_issues(candidate, preset=preset)
    if diagnostics:
        if len(diagnostics) > CONTENT_DIAGNOSTIC_COUNT or any(len(d) > CONTENT_DIAGNOSTIC_LENGTH for d in diagnostics):
            raise ValueError("complete Art structural feedback exceeds existing typed bounds")
        print(json.dumps({"contract": "plotloom.typed-content-result.v1", "candidateHash": sha256(raw).hexdigest(),
            "issues": [{"code": "candidate_content_invalid", "fieldPaths": ["$"], "repairFacts": {}}],
            "displayDiagnostics": diagnostics}, ensure_ascii=False))
        return 42
    # Never serialize the validation model or synthesize a repaired candidate.
    return subprocess.run([str(node), str(SOURCE / "scripts/text-content-validation.mjs"),
        str(_file(args.candidate)), str(request)], check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("Art structural validation refused frozen input or runtime", file=sys.stderr)
        raise SystemExit(1)
