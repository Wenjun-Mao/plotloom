"""Validate or deterministically render one frozen native intent candidate."""
import argparse
import json
from pathlib import Path
import sys

from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.native_bridge_intent_contract import native_intent_suggestions, render_native_intent_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.request.read_text(encoding="utf-8"))
    request = CreativeHandoffRequest.model_validate({key: value for key, value in raw.items()
        if key in {field.alias or name for name, field in CreativeHandoffRequest.model_fields.items()}})
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    native_intent_suggestions(request, candidate)
    if args.command == "render":
        sys.stdout.buffer.write(render_native_intent_report(request, candidate))
    else:
        print("complete native intent suggestions validated")


if __name__ == "__main__":
    main()
