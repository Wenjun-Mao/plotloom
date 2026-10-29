"""Deterministic validation/rendering only; never launches a model or dispatch."""
import argparse
import json
import sys

from plotloom.content_language_contract import (
    bind_language_result,
    render_language_report,
)
from plotloom.creative_handoff_contracts import creative_handoff_request_from_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("validate", "render"))
    parser.add_argument("candidate")
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    with open(args.request) as source:
        request = creative_handoff_request_from_package(json.load(source))
    with open(args.candidate) as source:
        candidate = json.load(source)
    if args.operation == "render":
        sys.stdout.buffer.write(render_language_report(request, candidate))
    else:
        bind_language_result(request, candidate)


if __name__ == "__main__":
    main()
