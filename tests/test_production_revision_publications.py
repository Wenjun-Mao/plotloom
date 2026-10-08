"""Resolve outstanding publications explicitly before revising story authority."""
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage import ProjectFolderStorage
from plotloom.script_contracts import ScriptAcceptRequest
from plotloom.source_outline_contracts import SourceMaterial
from tests.test_project_storage_art import (
    _deliver, _deliver_stage, _pilot_script, _prepare_art_context,
    _write_art_reference_delivery,
)


def _storage_with_art(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate("ch_" + "u" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(ArtAcceptRequest(
            job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art,
        ))
        return storage, store.manifest.project_id


def _revised_source():
    return SourceMaterial(
        kind="synopsis", title="Tide Light", text="A source revision invalidates accepted downstream bindings.",
        attribution="fixture", rights_declaration="fixture", adaptation_intent="fixture",
    )


@pytest.mark.parametrize("resolution", ["cancel", "deliver"])
def test_script_publication_blocks_revision_until_explicit_resolution(tmp_path, resolution):
    storage, project_id = _storage_with_art(tmp_path)
    with closing(storage.projects.open(project_id)) as store:
        candidate, request = store.prepare_script_candidate("ch_" + "j" * 32)
        before = store.source_outline_state()
        before_script = store.script_state()
        with pytest.raises(InvalidTransitionError, match="unresolved publication"):
            store.save_source_material(expected_source_revision=1, material=_revised_source())
        assert store.source_outline_state() == before
        assert store.script_state() == before_script
        delivery = _deliver_stage(store, request, "script.json", _pilot_script(), "revision-script")
        if resolution == "cancel":
            store.cancel_script_candidate(candidate.job_id)
        else:
            ready = store.admit_script_delivery(delivery)
        store.save_source_material(expected_source_revision=1, material=_revised_source())
        if resolution == "cancel":
            with pytest.raises(CreativeHandoffError):
                store.admit_script_delivery(delivery)
        else:
            with pytest.raises(CreativeHandoffError, match="changed before acceptance"):
                store.accept_script_candidate(ScriptAcceptRequest(
                    job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding, script=ready.script,
                ))
        assert store.script_state().accepted_script is None


def test_art_reference_revision_preserves_evidence_and_refuses_late_cancelled_delivery(tmp_path):
    storage, project_id = _storage_with_art(tmp_path)
    client = TestClient(create_project_folder_authoring_app(storage))
    root = f"/api/v2/projects/{project_id}"
    proposals = f"{root}/art-reference-proposals"

    def prepare(direction):
        prepared = client.post(proposals, json={"subjectType": "scene", "subjectId": "S01", "renderDirection": direction})
        assert prepared.status_code == 201, prepared.text
        proposal = prepared.json()["proposal"]
        copied = client.post(f"{proposals}/{proposal['id']}/copy")
        assert copied.status_code == 200, copied.text
        return proposal, Path(copied.json()["deliveryPath"])

    first, first_path = prepare("Cinematic realism, no people.")
    _write_art_reference_delivery(first_path, first)
    accepted = client.post(f"{proposals}/{first['id']}/refresh").json()
    assert accepted["state"] == "accepted"
    assert accepted["candidates"]
    pending, pending_path = prepare("A pending late-delivery study.")
    before_proposals = client.get(proposals).json()
    with closing(storage.projects.open(project_id)) as store:
        before = store.source_outline_state()
        with pytest.raises(InvalidTransitionError, match="unresolved publication"):
            store.save_source_material(expected_source_revision=1, material=_revised_source())
        assert store.source_outline_state() == before
    assert client.get(proposals).json() == before_proposals
    cancelled = client.post(f"{proposals}/{pending['id']}/cancel", json={"reason": "Author abandoned this study before revising its source."})
    assert cancelled.status_code == 200, cancelled.text
    with closing(storage.projects.open(project_id)) as store:
        store.save_source_material(expected_source_revision=1, material=_revised_source())

    art = client.get(f"{root}/art").json()
    assert art["acceptedArt"]["revision"] == 1
    assert art["status"] == "stale"
    visible = client.get(proposals)
    assert visible.status_code == 200
    assert all(not proposal["current"] for proposal in visible.json()["proposals"])
    assert client.post(proposals, json={"subjectType": "scene", "subjectId": "S01", "renderDirection": "Must not prepare from stale art."}).status_code == 409
    assert client.post(f"{proposals}/{first['id']}/copy").status_code == 409
    assert client.post(f"{proposals}/{first['id']}/refresh").json()["candidates"] == accepted["candidates"]
    _write_art_reference_delivery(pending_path, pending)
    late = client.post(f"{proposals}/{pending['id']}/refresh")
    assert late.status_code == 200, late.text
    assert late.json()["state"] == "inapplicable"
    assert late.json()["candidates"] == []
