"""Seed an isolated, contract-valid bridge for real-browser handoff checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from tests.test_production_bridge import _prepare_installable_bridge


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--application", type=Path, required=True)
    args = parser.parse_args()
    storage = ProjectFolderStorage(outputs_root=args.outputs, application_data_root=args.application)
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))
    try:
        proposal = _prepare_installable_bridge(store)
        accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
        ))
        assert accepted.status == "accepted"
        print(store.manifest.project_id)
    finally:
        store.close()


if __name__ == "__main__":
    main()
