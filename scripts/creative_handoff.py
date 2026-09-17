"""Prepare or inspect one project-local F0 creative handoff package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange


def request_from(path: Path) -> CreativeHandoffRequest:
    return CreativeHandoffRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "inspect"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--current-stage-revision", type=int)
    arguments = parser.parse_args()
    exchange = CreativeHandoffExchange(arguments.root)
    request = request_from(arguments.request)
    if arguments.command == "prepare":
        print(json.dumps(exchange.write_package(request), sort_keys=True))
        return
    delivery = exchange.read_delivery(request)
    if delivery is None:
        print(json.dumps({"state": "awaiting_delivery"}))
        return
    if arguments.current_stage_revision is not None:
        exchange.assert_current(delivery, current_stage_revision=arguments.current_stage_revision)
    print(json.dumps({"state": "candidate_ready", "manifestHash": delivery.manifest_hash}, sort_keys=True))


if __name__ == "__main__":
    main()
