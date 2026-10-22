"""Disposable validated advice with a fake native queue, never a real specialist."""
import argparse
import json
import subprocess
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from plotloom.native_bridge_presentation_contract import render_native_presentation_report
from plotloom.native_bridge_presentation_service import NativeBridgePresentationService
from plotloom.production_bridge_contracts import ProductionBridgeIntentUpdateRequest
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.test_specialist_settings import configured
from tests.test_native_bridge_presentation import candidate_for
from plotloom.conformance import FIXED_CHINESE_BRIEF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--application", type=Path, required=True)
    args = parser.parse_args()
    storage = ProjectFolderStorage(outputs_root=args.outputs, application_data_root=args.application)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))) as store:
        _prepare_installable_bridge(store)
        proposal = store.prepare_production_bridge(store.production_bridge_state().preparation.request).proposal
        proposal = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
            entries=[{"id": entry.id, "text": "测试作者已保存的戏剧目的"} for entry in proposal.intent_package.entries])).proposal
        project = store.manifest.project_id
    registry, _ = configured(storage.application.root)
    service = NativeBridgePresentationService(storage, registry)
    checkout = Path(__file__).resolve().parents[3]
    pin = {"upstreamRevision": subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True, text=True, check=True).stdout.strip(),
        "upstreamSkillHash": sha256((checkout / "docs/creative-workflow/native-bridge-presentation.md").read_bytes()).hexdigest(),
        "specialistSkillHash": sha256((checkout / ".agents/skills/plotloom-presentation-specialist/SKILL.md").read_bytes()).hexdigest()}
    real_run = subprocess.run
    def fake_queue(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            return subprocess.CompletedProcess(command, 0, "queued")
        return real_run(command, **kwargs)
    with patch.object(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: pin), patch("subprocess.run", fake_queue):
        job = service.create(project, expected_revision=proposal.revision, expected_hash=proposal.content_hash)
        service.send(project, job)
    with closing(storage.projects.open(project)) as store:
        request, _ = service._request(store, project, job)
        paths = store.creative_handoff_exchange().verified_package_paths(request, store.creative_handoff_execution_pin(request))
    candidate = canonical_json(candidate_for(request))
    report = render_native_presentation_report(request, json.loads(candidate))
    output = Path(paths["deliveryPath"]); output.mkdir()
    (output / "presentation.json").write_bytes(candidate); (output / "report.html").write_bytes(report)
    manifest = json.loads((Path(paths["packagePath"]) / "completion-manifest.example.json").read_text())
    manifest["deliveryId"] = "browser-fake-presentation-advice"
    manifest["candidate"]["sha256"], manifest["report"]["sha256"] = sha256(candidate).hexdigest(), sha256(report).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = pin["upstreamRevision"]
    manifest["limitations"] = ["Software fixture: fake queue and authored deterministic spans, not a real specialist or creative acceptance."]
    (output / "completion.json").write_bytes(canonical_json(manifest))
    assert service.check(project, job)["candidateStatus"] == "ready"
    print(project)


if __name__ == "__main__":
    main()
