"""Retained image inputs do not confer current design or selection authority."""

from copy import deepcopy

import pytest

from plotloom.cast_contracts import CastReopenRequest, CastSaveRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import (
    CharacterReferenceProposalCandidateRow,
    CharacterReferenceProposalDeliveryRow,
    CharacterReferenceProposalRow,
)
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.test_project_storage_art import _prepare_art_context


@pytest.fixture
def retained(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    _prepare_art_context(store)
    project_id = store.manifest.project_id
    parent = store.media.prepare_character_reference_proposal(
        project_id, character_id="lin", cast_revision=1,
        visual_direction="Original design", parent_candidate_asset_id=None,
    )["proposal"]
    store.media.mark_character_reference_proposal_exported(project_id, parent["id"])
    output = {"filename": "fixture.png", "originalHash": "a" * 64, "displayHash": "b" * 64,
              "mimeType": "image/png", "byteSize": 3, "width": 1, "height": 1, "role": "original"}
    result = store.media.record_character_reference_proposal_delivery(
        project_id, parent["id"], delivery_id="retained", manifest_hash="c" * 64,
        manifest={"actualPrompt": "Offline persistence fixture", "toolEvidence": {}},
        outputs=[output], publish=lambda _: ("managed/original.png", "managed/display.png"),
    )
    asset_id = result["candidates"][0]["assetId"]
    store.media.create_character_reference_decision(
        project_id, character_id="lin", primary_asset_id=asset_id, complementary_asset_ids=[],
        expected_reference_revision=0, reviewer=None, notes=None, authority="cast",
    )
    try:
        yield store, project_id, parent, asset_id, result["candidates"][0]["id"]
    finally:
        store.close()


def revise(store):
    accepted = store.cast_state().accepted_cast
    store.reopen_cast(CastReopenRequest(expected_cast_revision=accepted.revision))
    edited = deepcopy(accepted.cast)
    edited["characters"][0]["persona"]["appearance"] = "Revised blue coat and compact low bun"
    return store.save_reopened_cast(CastSaveRequest(
        expected_cast_revision=accepted.revision, binding=accepted.binding,
        cast=edited, consumer_mappings=accepted.consumer_mappings,
    )).accepted_cast


def prepare(store, project_id, asset_id, revision=2):
    return store.media.prepare_character_reference_proposal(
        project_id, character_id="lin", cast_revision=revision,
        visual_direction="Keep identity, follow revised hair design", parent_candidate_asset_id=asset_id,
    )["proposal"]


def test_revised_cast_can_refine_retained_image_without_reviving_parent(retained):
    store, project_id, parent, asset_id, _ = retained
    revised = revise(store)
    before = store.media.list_character_reference_proposals(project_id)
    decisions = store.media.list_character_reference_decisions(project_id)
    assert before[0]["current"] is False
    assert decisions["decisions"][0]["current"] is False

    proposal = prepare(store, project_id, asset_id)
    snapshot = proposal["request"]["frozenSnapshot"]
    assert proposal["current"] is True and proposal["request"]["kind"] == "refinement"
    assert snapshot["acceptedCast"]["revision"] == revised.revision
    assert snapshot["characterContext"]["appearance"] == "Revised blue coat and compact low bun"
    assert snapshot["references"][0]["originalHash"] == "a" * 64
    assert snapshot["references"][0]["assetId"] == asset_id
    assert snapshot["references"][0]["role"] == "parent_output"
    after = store.media.list_character_reference_proposals(project_id)
    assert next(item for item in after if item["id"] == parent["id"]) == before[0]
    assert store.media.list_character_reference_decisions(project_id) == decisions
    sources = store.media.character_reference_proposal_package_sources(project_id, proposal["id"])
    assert sources["references"][0]["contentHash"] == "a" * 64
    revise(store)
    assert not store.media.character_reference_proposal_delivery_context(project_id, proposal["id"])["current"]
    with pytest.raises(InvalidTransitionError, match="no longer current"):
        store.media.character_reference_proposal_package_sources(project_id, proposal["id"])


@pytest.mark.parametrize("corruption", ["other_character", "cancelled", "rejected", "inapplicable", "wrong_delivery", "changed_hash", "not_candidate"])
def test_parent_requires_same_subject_and_intact_accepted_delivery(retained, corruption):
    store, project_id, parent, asset_id, candidate_id = retained
    revise(store)
    unrelated = prepare(store, project_id, None)
    with store.repository._write() as session:
        candidate = session.get(CharacterReferenceProposalCandidateRow, candidate_id)
        proposal = session.get(CharacterReferenceProposalRow, parent["id"])
        delivery = session.get(CharacterReferenceProposalDeliveryRow, candidate.delivery_id)
        if corruption == "other_character":
            proposal.character_id = "someone-else"
        elif corruption == "cancelled":
            proposal.state = "cancelled"
        elif corruption in {"rejected", "inapplicable"}:
            delivery.state = corruption
        elif corruption == "wrong_delivery":
            delivery.proposal_id = unrelated["id"]
        elif corruption == "changed_hash":
            candidate.output_hash = "e" * 64
        elif corruption == "not_candidate":
            session.delete(candidate)
    before = store.media.list_character_reference_proposals(project_id)
    with pytest.raises(InvalidTransitionError, match="同一角色"):
        prepare(store, project_id, asset_id)
    assert store.media.list_character_reference_proposals(project_id) == before


def test_another_project_cannot_use_the_retained_candidate(retained, tmp_path):
    store, project_id, _, asset_id, _ = retained
    storage = ProjectFolderStorage(outputs_root=tmp_path / "other-outputs", application_data_root=tmp_path / "other-application")
    other = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _prepare_art_context(other)
        with pytest.raises(InvalidTransitionError, match="同一角色"):
            prepare(other, other.manifest.project_id, asset_id, revision=1)
        assert other.media.list_character_reference_proposals(other.manifest.project_id) == []
        assert store.media.list_character_reference_proposals(project_id)[0]["current"] is True
    finally:
        other.close()


def test_parent_does_not_bypass_current_cast_or_expected_revision(retained):
    store, project_id, _, asset_id, _ = retained
    revise(store)
    with pytest.raises(InvalidTransitionError, match="current accepted cast"):
        prepare(store, project_id, asset_id, revision=1)
    store.reopen_cast(CastReopenRequest(expected_cast_revision=2))
    with pytest.raises(InvalidTransitionError, match="current accepted cast"):
        prepare(store, project_id, asset_id)
