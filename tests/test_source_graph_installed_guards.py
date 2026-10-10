"""Installed production permits explicit source changes without erasing evidence."""

from __future__ import annotations

from hashlib import sha256

import pytest
from sqlalchemy import select

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName, StageStatus
from plotloom.persistence.schema import ProductionBridgeAdmissionRow
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.source_outline_contracts import (
    SectionMap,
    SectionMapGraphInstallRequest,
    SectionMapSaveRequest,
)
from tests.graph_draft_fixtures import save_graph_mapping
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.test_project_storage_source_outline import _storage


def _store_with_installed_bridge(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    proposal = _prepare_installable_bridge(store)
    accepted = store.accept_production_bridge(
        ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
        )
    )
    assert accepted.installation.status == "current"
    project_id = store.manifest.project_id
    with store.repository._read() as session:
        admission = session.scalar(
            select(ProductionBridgeAdmissionRow).where(
                ProductionBridgeAdmissionRow.project_id == project_id,
            )
        )
    assert admission is not None
    assert admission.id != project_id

    media_bytes = b"retained production reference"
    media_uri = store.artifacts.put(media_bytes)
    store.media.record_managed_import(
        project_id,
        original_hash=sha256(media_bytes).hexdigest(),
        display_hash=sha256(media_bytes).hexdigest(),
        mime_type="image/png",
        byte_size=len(media_bytes),
        width=1,
        height=1,
        declaration={"origin": "installed-graph-guard-fixture", "rights": "known"},
        publish=lambda: (media_uri, media_uri),
    )
    return store, media_uri, media_bytes


def _snapshot(store):
    project_id = store.manifest.project_id
    stages = {}
    for stage in StageName:
        head = store.authoring.get_stage_head(project_id, stage)
        payload = None
        if head.status == StageStatus.READY:
            payload = store.authoring.get_stage_payload(project_id, stage).model_dump(
                mode="json",
                by_alias=True,
            )
        stages[stage.value] = {
            "revision": head.revision,
            "status": head.status.value,
            "payload": payload,
        }
    state = store.source_outline_state()
    return {
        "stages": stages,
        "sourceOutline": state.model_dump(mode="json", by_alias=True),
        "drafts": [
            draft.model_dump(mode="json", by_alias=True)
            for draft in store.authoring_drafts()
        ],
        "media": store.media.list_managed_assets(project_id),
    }


def _changed_mapping(mapping: SectionMap, change: str) -> SectionMap:
    data = mapping.model_dump(mode="json", by_alias=True)
    if change == "footage_mode":
        section = next(
            item for item in data["sections"] if item["sectionId"] == "choose"
        )
        section["footageMode"] = "footage"
    elif change == "topology":
        edges = {item["id"]: item for item in data["topology"]["edges"]}
        edges["beacon"]["targetNodeId"], edges["dock"]["targetNodeId"] = (
            edges["dock"]["targetNodeId"],
            edges["beacon"]["targetNodeId"],
        )
        outcomes = {item["outcomeId"]: item for item in data["choices"][0]["outcomes"]}
        outcomes["beacon"]["endingSectionId"], outcomes["dock"]["endingSectionId"] = (
            outcomes["dock"]["endingSectionId"],
            outcomes["beacon"]["endingSectionId"],
        )
    else:
        raise AssertionError(f"unknown test mutation: {change}")
    return SectionMap.model_validate(data)


@pytest.mark.parametrize("change", ["topology", "footage_mode"])
def test_installed_bridge_allows_exact_section_map_confirmation_and_stales_production(
    tmp_path, change
):
    store, media_uri, media_bytes = _store_with_installed_bridge(tmp_path)
    try:
        before = store.source_outline_state()
        current_mapping = before.accepted_section_map.mapping
        changed_mapping = _changed_mapping(current_mapping, change)
        draft_receipt = save_graph_mapping(store, changed_mapping)
        installed = store.production_bridge_state().installation
        saved = store.save_section_map(
            SectionMapSaveRequest(
                expected_graph_draft_revision=draft_receipt.draft_revision,
                expected_section_map_revision=before.accepted_section_map.revision,
                expected_source_revision=before.source.revision,
                expected_outline_revision=before.accepted_outline.revision,
                expected_outline_content_hash=before.accepted_outline.content_hash,
                mapping=changed_mapping,
            )
        )
        assert saved.accepted_section_map.mapping == changed_mapping
        assert saved.graph_admission.status == "stale"
        current = store.production_bridge_state().installation
        assert current.admission_id == installed.admission_id
        assert current.status == "outdated"
        assert store.artifacts.get(media_uri) == media_bytes
    finally:
        store.close()


def test_installed_bridge_allows_exact_graph_apply_and_retains_media(tmp_path):
    store, media_uri, media_bytes = _store_with_installed_bridge(tmp_path)
    try:
        before = store.source_outline_state()
        mapping = before.accepted_section_map.mapping
        draft_receipt = save_graph_mapping(store, mapping)
        installed = store.install_section_map_graph(
            SectionMapGraphInstallRequest(
                expected_source_revision=before.source.revision,
                expected_source_content_hash=before.source.content_hash,
                expected_outline_revision=before.accepted_outline.revision,
                expected_outline_content_hash=before.accepted_outline.content_hash,
                expected_section_map_revision=before.accepted_section_map.revision,
                expected_section_map_content_hash=before.accepted_section_map.content_hash,
                expected_graph_revision=before.graph_admission.graph_revision,
                expected_graph_draft_revision=draft_receipt.draft_revision,
            )
        )
        assert (
            installed.graph_admission.graph_revision
            == before.graph_admission.graph_revision + 1
        )
        assert not store.authoring_drafts()
        assert store.production_bridge_state().installation.status == "outdated"
        assert store.artifacts.get(media_uri) == media_bytes
    finally:
        store.close()


def test_uninstalled_bridge_still_allows_a_reviewed_footage_change(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _prepare_installable_bridge(store)
        assert store.production_bridge_state().installation is None
        before = store.source_outline_state()
        changed_mapping = _changed_mapping(
            before.accepted_section_map.mapping, "footage_mode"
        )
        draft_receipt = save_graph_mapping(store, changed_mapping)

        saved = store.save_section_map(
            SectionMapSaveRequest(
                expected_graph_draft_revision=draft_receipt.draft_revision,
                expected_section_map_revision=before.accepted_section_map.revision,
                expected_source_revision=before.source.revision,
                expected_outline_revision=before.accepted_outline.revision,
                expected_outline_content_hash=before.accepted_outline.content_hash,
                mapping=changed_mapping,
            )
        )

        assert saved.section_map_status == "current"
        assert (
            saved.accepted_section_map.revision
            == before.accepted_section_map.revision + 1
        )
        assert saved.accepted_section_map.mapping == changed_mapping
    finally:
        store.close()
