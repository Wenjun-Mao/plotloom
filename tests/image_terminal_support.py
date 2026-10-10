"""Real image-owner requests and immutable exchanges, with an offline queue."""

import json
import subprocess
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from tests.art_delivery_fixtures import _deliver
from tests.creative_delivery_fixtures import _prepare_art_context
from tests.image_identity_fixtures import (
    install_visible_fixture_character as _install_visible_fixture_character,
)
from tests.image_identity_fixtures import png as _png
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.specialist_reconciliation_support import snapshot_database, snapshot_files
from tests.test_project_storage_image_workflow import _approve
from tests.test_specialist_settings import configured


class ImageTerminalRuntime:
    def __init__(
        self, root, monkeypatch, target="image_job", *, unknown=False, reference=False
    ):
        self.storage = ProjectFolderStorage(
            outputs_root=root / "outputs", application_data_root=root / "application"
        )
        store = self.storage.projects.create(FIXED_CHINESE_BRIEF)
        self.project_id = store.manifest.project_id
        self.registry, self.settings = configured(self.storage.application.root)
        self.task_id = self.settings.image.task_id
        self.target = target
        self.calls = []
        original = subprocess.run

        def queue(command, **kwargs):
            if command[:2] == ["codex", "queue"]:
                self.calls.append(command)
                return subprocess.CompletedProcess(
                    command, 1 if unknown else 0, "offline"
                )
            return original(command, **kwargs)

        monkeypatch.setattr(subprocess, "run", queue)
        self.client = TestClient(create_project_folder_authoring_app(self.storage))
        if target == "image_job":
            ProjectPipelineExecutor(FixtureResolver()).execute(
                store, profile=fixture_profile()
            )
            if reference:
                _install_visible_fixture_character(store)
                imported = self.client.post(
                    f"/api/v2/projects/{self.project_id}/managed-assets",
                    files={
                        "image": ("reference.png", _png((50, 80, 120)), "image/png")
                    },
                    data={
                        "origin": "Offline reference fixture",
                        "rights": "unknown",
                        "declared_additions_json": "[]",
                    },
                )
                assert imported.status_code == 201, imported.text
                chosen = self.client.post(
                    f"/api/v2/projects/{self.project_id}/character-references",
                    json={
                        "characterId": "fixture-hero",
                        "authority": "story_bible",
                        "primaryAssetId": imported.json()["id"],
                        "expectedReferenceRevision": 0,
                        "reviewer": "Offline fixture",
                        "notes": "Identity role only",
                    },
                )
                assert chosen.status_code == 201, chosen.text
            approval = _approve(self.client, self.project_id, self.storage)
            head = store.authoring.get_stage_head(self.project_id, StageName.STORYBOARD)
            shot = store.authoring.get_stage_payload(
                self.project_id, StageName.STORYBOARD
            ).shots[0]
            job = store.media.prepare_image_job(
                self.project_id,
                approval_id=approval["id"],
                shot_id=shot.id,
                storyboard_revision=head.revision,
                presentation_change="Offline fixture",
                contract_version=3,
            )
            resource = "image-jobs"
        else:
            binding = _prepare_art_context(store)
            if target == "character_reference_proposal":
                job = store.media.prepare_character_reference_proposal(
                    self.project_id,
                    character_id="lin",
                    cast_revision=1,
                    visual_direction="Offline fixture",
                    parent_candidate_asset_id=None,
                )
                resource = "character-reference-proposals"
            else:
                candidate, request = store.prepare_art_candidate(
                    "ch_" + uuid4().hex, render_style="realistic"
                )
                ready = store.admit_art_delivery(_deliver(store, request))
                store.accept_art_candidate(
                    ArtAcceptRequest(
                        job_id=candidate.job_id,
                        expected_art_revision=0,
                        binding=binding,
                        art=ready.art,
                    )
                )
                job = store.media.prepare_art_reference_proposal(
                    self.project_id,
                    subject_type="scene",
                    subject_id="S01",
                    render_direction="Offline fixture",
                )
                resource = "art-reference-proposals"
        job = job.get("job", job.get("proposal", job))
        self.job = job
        self.job_url = f"/api/v2/projects/{self.project_id}/{resource}/{job['id']}"
        response = self.client.post(self.job_url + "/send")
        assert response.status_code == (422 if unknown else 200), response.text
        context = getattr(
            store.media,
            {
                "image_job": "image_job_delivery_context",
                "character_reference_proposal": "character_reference_proposal_delivery_context",
                "art_reference_proposal": "art_reference_proposal_delivery_context",
            }[target],
        )(self.project_id, job["id"])
        self.exchange = store.image_exchange_for(context)
        self.delivery = self.exchange._root() / "jobs" / job["id"] / "delivery"
        self.delivery.mkdir(exist_ok=True)
        self.provenance = {
            "codeRevision": "a" * 40,
            "skillVersion": "plotloom-image-specialist.v3",
            "skillHash": "b" * 64,
        }
        (self.delivery / "executor-pin.json").write_text(
            json.dumps(
                {
                    "jobId": job["id"],
                    "requestHash": job["requestHash"],
                    "executionContract": "codex_specialist.v2",
                    **self.provenance,
                }
            )
        )
        self.marker = {
            "schemaVersion": 1,
            "jobId": job["id"],
            "requestHash": job["requestHash"],
            "taskId": self.task_id,
            "outcome": "blocked",
            "phase": "before_generation",
            "generationStarted": False,
            "activeTools": False,
            "outputsProduced": False,
            "reason": "Contradictory fixture request; no live generation.",
            "executorProvenance": self.provenance,
        }
        self.write_marker()
        assert (
            self.client.post(
                self.job_url + "/cancel", json={"reason": "Offline fixture cancelled"}
            ).status_code
            == 200
        )
        self.before_database = snapshot_database(store)
        self.before_files = {
            name: content
            for name, content in snapshot_files(store.home).items()
            if not name.startswith("project.sqlite3")
        }
        store.close()
        self.url = (
            f"/api/v2/projects/{self.project_id}/image-terminal/{target}/{job['id']}"
        )
        self.review = {
            "markerHash": sha256(
                (self.delivery / "terminal.json").read_bytes()
            ).hexdigest(),
            "taskId": self.task_id,
            "terminalTurnId": str(uuid4()),
            "terminalRevision": 58,
            "observedIdle": True,
            "reviewedBlockedVerdict": True,
            "reviewer": "Offline terminal reviewer",
        }

    def write_marker(self):
        (self.delivery / "terminal.json").write_text(json.dumps(self.marker))

    def dispatch_root(self):
        data = json.loads(self.registry.path.read_text())
        return Path(data["roots"][self.task_id])

    def settle(self):
        return self.client.post(self.url + "/settle", json=self.review)

    def assert_unpublished(self):
        store = self.storage.projects.open(self.project_id)
        try:
            assert snapshot_database(store) == self.before_database
            # SQLite checkpoint/WAL bytes may change on ordinary close/open;
            # compare every logical table separately and immutable files here.
            actual = {
                name: content
                for name, content in snapshot_files(store.home).items()
                if not name.startswith("project.sqlite3")
            }
            assert actual == self.before_files, [
                name
                for name in actual.keys() | self.before_files.keys()
                if actual.get(name) != self.before_files.get(name)
            ]
        finally:
            store.close()
        assert len(self.calls) == 1
