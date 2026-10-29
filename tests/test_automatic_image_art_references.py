"""Automatic frames consume exact selected physical Art images, provider-free."""
import json
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from plotloom.image_commands import frozen_references, image_package
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_reference_roles import (
    ART_REFERENCE_INSTRUCTION,
    package_reference_role,
)
from plotloom.persistence.project.image_art_references import (
    ART_REFERENCE_CONTRACT,
    art_references_current,
    freeze_art_references,
    required_art_subjects,
    reusable_image_checkpoints,
)
from plotloom.persistence.schema import ArtReferenceDecisionStateRow, ImageJobRow
from tests.autopilot_installed_text_fixtures import installed_text_image_environment
from tests.test_autopilot_image_phase import references_ready
from tests.test_autopilot_images import current


def prepared_frame(tmp_path, monkeypatch, prefix):
    result = installed_text_image_environment(tmp_path, monkeypatch, prefix)
    storage, _registry, service, view, _calls, _text = result
    references_ready(storage, service, view)
    service.step(view.project_id)
    retained = current(storage, view)
    checkpoint = next(item for item in retained.checkpoints if item["evidence"]["owner"] == "image")
    assert checkpoint["state"] == "prepared"
    return result, checkpoint


def test_automatic_frame_freezes_views_and_packages_actual_selected_scene_bytes(
    tmp_path, monkeypatch, installed_text_prefix,
):
    (storage, _registry, service, view, calls, _text), checkpoint = prepared_frame(
        tmp_path, monkeypatch, installed_text_prefix)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            context = store.media.image_job_delivery_context(view.project_id, checkpoint["evidence"]["jobId"])
            snapshot = context["request"]["frozenSnapshot"]
            assert snapshot["artReferenceContract"] == ART_REFERENCE_CONTRACT
            refs = [item for item in snapshot["references"] if item["role"] == "scene_environment"]
            assert len(refs) == 1 and refs[0]["subjectId"] == snapshot["shot"]["locationId"]
            decision = next(item for item in store.media.list_art_reference_decisions(view.project_id)["decisions"] if item["current"])
            assert refs[0]["referenceDecisionId"] == decision["id"]
            assert refs[0]["originalHash"] == decision["assetHash"]
            assert refs[0]["subjectHash"] == decision["subjectHash"]
            paths = image_package(store, "image", context["id"])
            package = Path(paths["packagePath"])
            request = json.loads((package / "request.json").read_text())
            assert [item["role"] for item in request["references"]] == [item[0] for item in frozen_references(context)]
            for item in request["references"]:
                assert sha256((package / item["filename"]).read_bytes()).hexdigest() == item["sha256"]
            assert ART_REFERENCE_INSTRUCTION in (package / "COPY_ASSIGNMENT.txt").read_text()
            assert "scene_environment:" + refs[0]["subjectId"] in (package / "COPY_ASSIGNMENT.txt").read_text()
            assert snapshot["shot"]["action"]  # Art does not replace target action.
        assert len(calls) == 2  # Only the character/scene fixtures; no frame host admission.
    finally:
        service.close()


@pytest.mark.parametrize("change", ["missing", "replaced", "wrong_revision"])
def test_missing_replaced_or_stale_art_decision_blocks_current_frame_without_dispatch(
    tmp_path, monkeypatch, installed_text_prefix, change,
):
    (storage, _registry, service, view, calls, _text), checkpoint = prepared_frame(
        tmp_path, monkeypatch, installed_text_prefix)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            context = store.media.image_job_delivery_context(view.project_id, checkpoint["evidence"]["jobId"])
            snapshot = context["request"]["frozenSnapshot"]
            reference = next(item for item in snapshot["references"] if item["role"] == "scene_environment")
            if change == "replaced":
                store.media.create_art_reference_decision(view.project_id, subject_type="scene",
                    subject_id=reference["subjectId"], asset_id=reference["assetId"],
                    expected_reference_revision=reference["referenceRevision"])
            else:
                with store.repository._write() as session:
                    state = session.get(ArtReferenceDecisionStateRow, (view.project_id, "scene", reference["subjectId"]))
                    if change == "missing":
                        state.active_decision_id = None
                    else:
                        state.revision += 1
            assert not store.media.image_job_delivery_context(view.project_id, context["id"])["current"]
            with store.repository._read() as session:
                if change == "replaced":
                    replacement = freeze_art_references(session, view.project_id, [("scene", reference["subjectId"])],
                        store.repository._media.art_references)
                    assert replacement[0]["referenceDecisionId"] != reference["referenceDecisionId"]
                    assert replacement[0]["originalHash"] == reference["originalHash"]
                else:
                    with pytest.raises(ImageJobError, match="美术参考"):
                        freeze_art_references(session, view.project_id, [("scene", reference["subjectId"])],
                            store.repository._media.art_references)
                assert not art_references_current(session, view.project_id, snapshot, store.repository._media.art_references)
        assert len(calls) == 2
    finally:
        service.close()


def test_physical_location_and_prop_dependencies_follow_ids_across_route_scenes():
    context = {"locations": [{"id": "S01"}], "props": [{"id": "P01"}, {"id": "P02"}]}
    opening = SimpleNamespace(scene_id="opening-scene", location_id="S01", prop_ids=["P01"])
    ending = SimpleNamespace(scene_id="ending-scene", location_id="S01", prop_ids=["P01"])
    assert required_art_subjects(opening, context) == required_art_subjects(ending, context) == [
        ("scene", "S01"), ("prop", "P01"), ("prop", "P02")]
    assert package_reference_role({"role": "prop_identity", "subjectId": "P01"}) == "prop_identity:P01"
    assert package_reference_role({"role": "scene_environment", "subjectId": "S01"}) == "scene_environment:S01"


def test_continue_drops_only_frames_without_art_dependencies_and_preserves_original_evidence():
    legacy = SimpleNamespace(evidence={"owner": "image", "jobId": "legacy"})
    checked = SimpleNamespace(evidence={"owner": "image", "jobId": "checked"})
    reference = SimpleNamespace(evidence={"owner": "art-reference", "jobId": "art"})
    old_geometry = SimpleNamespace(evidence={"owner": "geometry-preparation",
        "geometryPreparation": {"source": {"jobId": "legacy"}}})
    current_geometry = SimpleNamespace(evidence={"owner": "geometry-preparation",
        "geometryPreparation": {"source": {"jobId": "checked"}}})
    snapshots = {
        "legacy": {"request": {"frozenSnapshot": {"references": []}}},
        "checked": {"request": {"frozenSnapshot": {"artReferenceContract": ART_REFERENCE_CONTRACT}}},
    }
    retained = json.dumps(snapshots, sort_keys=True)
    class Session:
        def get(self, model, identifier):
            assert model is ImageJobRow
            return SimpleNamespace(id=identifier, **snapshots[identifier])
    assert reusable_image_checkpoints(Session(), [legacy, checked, reference, old_geometry, current_geometry]) == [
        checked, reference, current_geometry]
    assert json.dumps(snapshots, sort_keys=True) == retained
