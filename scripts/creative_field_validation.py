"""Typed primary ownership validation followed by the pinned Node stage gate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from plotloom.creative_field_ownership import (
    CreativeFieldError, assert_ownership_artifact, creative_field_roles,
)
from plotloom.creative_handoff_contracts import creative_handoff_request_from_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--node", required=True)
    args = parser.parse_args()
    raw = args.candidate.read_bytes()
    candidate = json.loads(raw)
    request = creative_handoff_request_from_package(json.loads(args.request.read_bytes()))
    if request.stage not in {"characters", "storyboard"} or request.content_validation_contract != "plotloom.typed-content-result.v1":
        raise ValueError("primary ownership validation requires a marked typed Cast or Storyboard request")
    assert_ownership_artifact(request)  # Frozen input failures never become correction authority.
    from plotloom.provider_literals import LITERAL_INPUT, validate_context
    if LITERAL_INPUT in request.input_artifacts:
        validate_context(request)
    try:
        creative_field_roles(candidate, request)
    except CreativeFieldError as error:
        print(json.dumps({"contract": "plotloom.typed-content-result.v1", "candidateHash": sha256(raw).hexdigest(),
            "issues": [{"code": "candidate_content_invalid", "fieldPaths": ["$"], "repairFacts": {}}],
            "displayDiagnostics": [str(error)]}))
        return 42
    script = Path(__file__).with_name("storyboard-content-validation.mjs" if request.stage == "storyboard" else "text-content-validation.mjs")
    return subprocess.run([args.node, str(script), str(args.candidate), str(args.request)], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
