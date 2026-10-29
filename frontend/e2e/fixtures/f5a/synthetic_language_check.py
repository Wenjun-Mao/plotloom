"""Install only the repository's explicit synthetic language-check proof in E2E data."""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from plotloom.content_language_contract import CHECK_INPUT
from plotloom.creative_handoff_identity import canonical_json
from plotloom.project_storage import ProjectFolderStorage
from tests.content_language_fixtures import install_synthetic_language_check


def install_for_job(store, stage: str, candidate_job_id: str) -> dict[str, str | bool]:
    from plotloom.creative_commands import CREATIVE_METHODS

    creative_stage = "storyboard" if stage == "storyboard-review" else stage
    state = getattr(store, CREATIVE_METHODS[creative_stage][0])()
    current = state.candidate
    if current is None or current.job_id != candidate_job_id or current.status in {"cancelled", "accepted"}:
        return {"candidateJobId": candidate_job_id, "proofKind": "synthetic-test-skip",
                "dispatchPerformed": False, "reason": "terminal-or-replaced"}
    original = getattr(store, CREATIVE_METHODS[creative_stage][1])(candidate_job_id)
    delivery = store.creative_handoff_exchange().read_delivery(
        original, store.creative_handoff_execution_pin(original))
    if delivery is None:
        raise ValueError("fixture delivery is incomplete")
    candidate = delivery.candidate

    check_job_id = install_synthetic_language_check(store, original, candidate)
    checking, data = store.repository.content_language.load(store.manifest.project_id, check_job_id)
    frozen = checking.input_artifacts[CHECK_INPUT]
    result, receipt, attempt = data.get("result"), data.get("receipt"), data.get("attempt")
    candidate_hash = sha256(canonical_json(candidate)).hexdigest()
    if (check_job_id == candidate_job_id
            or checking.source.get("candidateJobId") != candidate_job_id
            or frozen.get("candidateHash") != candidate_hash
            or result is None or result.get("bindingHash") != frozen.get("bindingHash")
            or result.get("verdict") != "pass"
            or not receipt or not attempt or attempt.get("state") != "completed"):
        raise ValueError("synthetic language proof is missing, stale, unbound, or not a pass")
    return {
        "candidateJobId": candidate_job_id,
        "candidateHash": candidate_hash,
        "checkJobId": check_job_id,
        "bindingHash": frozen["bindingHash"],
        "resultHash": sha256(canonical_json(result)).hexdigest(),
        "receiptHash": sha256(canonical_json(receipt)).hexdigest(),
        "verdict": result["verdict"],
        "proofKind": "synthetic-test-receipt",
        "dispatchPerformed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-root", required=True, type=Path)
    parser.add_argument("--application-data-root", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--candidate-job-id", required=True)
    parser.add_argument("--stage", required=True,
        choices=("outline", "characters", "art", "script", "storyboard-review"))
    args = parser.parse_args()
    storage = ProjectFolderStorage(outputs_root=args.outputs_root,
        application_data_root=args.application_data_root)
    store = storage.projects.open(args.project_id)
    try:
        proof = install_for_job(store, args.stage, args.candidate_job_id)
    finally:
        store.close()
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
