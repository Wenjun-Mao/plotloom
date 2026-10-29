"""Primary Outline content rejection, including source-bound optional echoes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from plotloom.creative_handoff_contracts import creative_handoff_request_from_package
from plotloom.outline_echoes import OutlineEchoError, outline_echo_roles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--node", required=True)
    args = parser.parse_args()
    raw = args.candidate.read_bytes()
    candidate = json.loads(raw)
    request = creative_handoff_request_from_package(json.loads(args.request.read_bytes()))
    try:
        outline_echo_roles(candidate, request)
    except OutlineEchoError as error:
        print(json.dumps({"contract": "plotloom.typed-content-result.v1",
            "candidateHash": hashlib.sha256(raw).hexdigest(),
            "issues": [{"code": "candidate_content_invalid", "fieldPaths": ["$"], "repairFacts": {}}],
            "displayDiagnostics": [str(error)]}))
        return 42
    script = Path(__file__).with_name("text-content-validation.mjs")
    return subprocess.run([args.node, str(script), str(args.candidate), str(args.request)], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
