"""Real file-SQLite and package exchange for terminal handoff route tests."""

import json
import sqlite3
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.source_structures import planned_structure
from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
from tests.test_specialist_settings import configured


def new_job():
    return "ch_" + uuid4().hex


def prepare(store, stage, job=None):
    job = job or new_job()
    if stage == "branches":
        store.prepare_branch_candidate()
        candidate = store.branch_state().candidate
        request = store.branch_candidate_request(candidate.job_id)
    elif stage == "outline":
        state = store.source_outline_state()
        request = CreativeHandoffRequest(
            job_id=job,
            project_id=store.manifest.project_id,
            stage=stage,
            section_id="story",
            expected_stage_revision=state.accepted_outline.revision,
            source=state.source.material.model_dump(mode="json", by_alias=True),
            input_artifacts={
                OUTLINE_SETTINGS_FILENAME: outline_settings(store.project().brief),
                "story-topology.json": planned_structure(
                    store.manifest.project_id, store.project().brief
                ).model_dump(mode="json", by_alias=True),
            },
            creative_brief="Terminal reconciliation fixture, never creative acceptance.",
        )
        candidate = store.prepare_outline_candidate(request)
    else:
        method = {
            "characters": store.prepare_cast_candidate,
            "art": store.prepare_art_candidate,
            "script": store.prepare_script_candidate,
            "storyboard": store.prepare_storyboard_review_candidate,
        }[stage]
        candidate, request = method(
            job,
            **({"render_style": "realistic"} if stage in {"art", "characters"} else {}),
        )
    # Match the route's preparation/export boundary before testing native send.
    store.creative_handoff_exchange().write_package(
        request, store.creative_handoff_execution_pin(request)
    )
    return candidate, request


def cancel(store, stage, job):
    method = {
        "branches": store.cancel_branch_candidate,
        "outline": store.cancel_outline_candidate,
        "characters": store.cancel_cast_candidate,
        "art": store.cancel_art_candidate,
        "script": store.cancel_script_candidate,
        "storyboard": store.cancel_storyboard_review_candidate,
    }[stage]
    return method(job)


def delivery(store, request):
    filename = {
        "branches": "branches.json",
        "outline": "outline.json",
        "characters": "cast.json",
        "art": "art.json",
        "script": "script.json",
        "storyboard": "storyboard.json",
    }[request.stage]
    # Exchange-valid placeholder content. Terminal handling must discard it
    # rather than revive currentness or execute stage validators.
    _deliver_stage(store, request, filename, {}, "cancelled-fixture")


def ready_delivery(store, request):
    state_method, accepted_field, payload_field = {
        "outline": (store.source_outline_state, "accepted_outline", "outline"),
        "characters": (store.cast_state, "accepted_cast", "cast"),
        "art": (store.art_state, "accepted_art", "art"),
        "script": (store.script_state, "accepted_script", "script"),
    }[request.stage]
    content = getattr(getattr(state_method(), accepted_field), payload_field)
    filename = {
        "branches": "branches.json",
        "outline": "outline.json",
        "characters": "cast.json",
        "art": "art.json",
        "script": "script.json",
    }[request.stage]
    return _deliver_stage(
        store, request, filename, content, "ready-replacement-fixture"
    )


def snapshot_files(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def snapshot_database(store):
    with sqlite3.connect(f"file:{store.database_path}?mode=ro", uri=True) as connection:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {
            name: connection.execute(
                f'SELECT * FROM "{name}" ORDER BY rowid'
            ).fetchall()
            for name in names
        }


class ReconciliationRuntime:
    def __init__(self, root, monkeypatch):
        self.storage = ProjectFolderStorage(
            outputs_root=root / "outputs", application_data_root=root / "application"
        )
        self.store = self.storage.projects.create(FIXED_CHINESE_BRIEF)
        _accepted_f4_script(self.store)
        self.project_id = self.store.manifest.project_id
        self.registry_root = self.storage.application.root
        self.registry, self.settings = configured(self.registry_root)
        self.calls = []
        original = subprocess.run

        def native_queue(command, **kwargs):
            if command[:2] == ["codex", "queue"]:
                self.calls.append(command)
                return subprocess.CompletedProcess(command, 0, "Queued")
            return original(command, **kwargs)

        monkeypatch.setattr(subprocess, "run", native_queue)

    def client(self, registry=None, *, raise_server_exceptions=False):
        app = create_project_folder_authoring_app(self.storage)
        assert app.state.specialists.path == (registry or self.registry).path
        return TestClient(app, raise_server_exceptions=raise_server_exceptions)

    def url(self, stage, job, project=None):
        return f"/api/v2/projects/{project or self.project_id}/specialist-tasks/{stage}/{job}"

    def dispatch_root(self, role="text"):
        data = json.loads(self.registry.path.read_text())
        return Path(data["roots"][getattr(self.settings, role).task_id])
