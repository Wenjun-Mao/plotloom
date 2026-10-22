"""Validate or deterministically render one frozen video directions candidate."""
import argparse
import json
from pathlib import Path
import sys

from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.video_directions_contract import bind_draft, render_report


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
    bind_draft(request, candidate)
    if args.command == "render":
        sys.stdout.buffer.write(render_report(request, candidate))
    else:
        print("complete video directions suggestions validated")


if __name__ == "__main__":
    main()
