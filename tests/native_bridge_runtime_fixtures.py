"""Fresh fake-native runtimes over either fresh or physically copied projects."""
import subprocess
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.native_bridge_intent_service import NativeBridgeIntentService
from plotloom.native_bridge_presentation_service import NativeBridgePresentationService
from plotloom.production_bridge_contracts import ProductionBridgeIntentUpdateRequest
from tests.native_bridge_seed_fixtures import pending_bridge_project
from tests.test_specialist_settings import configured


def _fake_native_transport(monkeypatch, stage):
    checkout = Path(__file__).resolve().parents[1]
    specialist = "intent" if stage == "bridge-intent" else "presentation"
    pin = {
        "upstreamRevision": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "upstreamSkillHash": sha256((checkout / f"docs/creative-workflow/native-bridge-{specialist}.md").read_bytes()).hexdigest(),
        "specialistSkillHash": sha256((checkout / f".agents/skills/plotloom-{specialist}-specialist/SKILL.md").read_bytes()).hexdigest(),
    }
    # The explicit fake pin qualifies binding mechanics, not source execution.
    if stage == "bridge-intent":
        current_pin = lambda _self, requested: pin if requested == stage else pytest.fail("unexpected stage")
    else:
        current_pin = lambda _self, requested: pin
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", current_pin)
    calls, real_run = [], subprocess.run

    def send(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "queued")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", send)
    return calls


def create_native_intent_runtime(root, monkeypatch, seed=None):
    storage, project, revision, digest = pending_bridge_project(root, seed)
    registry, _settings = configured(storage.application.root)
    service = NativeBridgeIntentService(storage, registry)
    calls = _fake_native_transport(monkeypatch, "bridge-intent")
    job = service.create(project, expected_revision=revision, expected_hash=digest)
    return storage, project, revision, digest, service, job, calls


def create_native_presentation_runtime(root, monkeypatch, seed=None):
    storage, project, _revision, _digest = pending_bridge_project(root, seed)
    with closing(storage.projects.open(project)) as store:
        proposal = store.prepare_production_bridge(store.production_bridge_state().preparation.request).proposal
        proposal = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
            entries=[{"id": entry.id, "text": "作者已保存的戏剧目的"} for entry in proposal.intent_package.entries],
        )).proposal
    registry, _ = configured(storage.application.root)
    service = NativeBridgePresentationService(storage, registry)
    calls = _fake_native_transport(monkeypatch, "bridge-presentation")
    job = service.create(project, expected_revision=proposal.revision, expected_hash=proposal.content_hash)
    return storage, project, proposal, service, job, calls
