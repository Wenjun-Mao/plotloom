"""Real source/F1/adoption boundaries; language-check fixture is not live proof."""
import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from plotloom.api import create_project_folder_authoring_app
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import InvalidTransitionError
from plotloom.outline_echoes import OutlineEchoError, outline_echo_roles
from plotloom.outline_preparation import outline_request
from plotloom.outline_settings import assert_outline_settings_current
from plotloom.persistence.project.graph_workbench import GraphDraftRebaseRequest
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.source_outline_contracts import OutlineAcceptRequest, SourceMaterial
from plotloom.source_structures import complete_routes
from plotloom.stage_contracts import StageName
from tests.authored_source_fixtures import (
    authored_brief,
    authored_mapping,
    authored_material,
)
from tests.content_language_fixtures import install_synthetic_language_check
from tests.graph_authoring_fixtures import install_request
from tests.graph_draft_fixtures import graph_draft_revision, graph_map_save_request
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.source_outline_fixtures import _deliver, _storage


def test_accepted_source_freezes_real_f1_authority_adopts_and_reopens_all_three_routes(tmp_path):
    storage = _storage(tmp_path)
    client = TestClient(create_project_folder_authoring_app(storage))
    created = client.post("/api/v2/projects", json={"brief": authored_brief().model_dump(mode="json", by_alias=True)})
    assert created.status_code == 201, created.text
    project = created.json()["id"]
    base = f"/api/v2/projects/{project}/source-outline"
    material = authored_material()
    saved = client.put(base + "/source", json={"expectedSourceRevision": 0, "material": material.model_dump(mode="json", by_alias=True)})
    assert saved.status_code == 200, saved.text
    digest = saved.json()["source"]["contentHash"]
    prepared = client.post(base + "/candidates")
    assert prepared.status_code == 201, prepared.text
    raw = json.loads((Path(prepared.json()["packagePath"]) / "request.json").read_text())
    assert "story-topology.json" not in raw["inputArtifacts"]
    frozen = raw["inputArtifacts"]["source-structure.json"]
    assert frozen["sourceHash"] == digest
    assert frozen["structure"] == material.authored_structure.model_dump(mode="json", by_alias=True)
    assert "not a generic planner result" in raw["creativeBrief"]
    with closing(storage.projects.open(project)) as store:
        request = outline_request(store, job_id=prepared.json()["jobId"])
        assert_outline_settings_current(request, store.project().brief)
        echoed = {"sourceStructure": frozen}
        roles = outline_echo_roles(echoed, request)
        assert roles["$.sourceStructure.structure.choices[0].outcomes[0].label"]["sourceSpan"]["path"].startswith("$.source.authoredStructure")
        forged = deepcopy(echoed); forged["sourceStructure"]["structure"]["choices"][0]["prompt"] = "伪造"
        with pytest.raises(OutlineEchoError): outline_echo_roles(forged, request)
        ready = store.admit_outline_delivery(_deliver(store, request))
        # Explicit offline language evidence; final story uses the real native checker.
        install_synthetic_language_check(store, request, ready.outline)
        store.accept_outline_candidate(OutlineAcceptRequest(jobId=request.job_id, expectedSourceRevision=1, expectedOutlineRevision=0))
        initial = store.graph_workbench_state().initial_payload
        assert initial.mapping.seed_topology is None and initial.mapping.author_source_hash == digest
        mapping = authored_mapping(store)
        accepted = store.save_section_map(graph_map_save_request(store, mapping=mapping,
            expected_section_map_revision=0, expected_source_revision=1, expected_outline_revision=1,
            expected_outline_content_hash=store.source_outline_state().accepted_outline.content_hash))
        store.install_section_map_graph(install_request(accepted, graph_draft_revision(store)))
        graph = store.authoring.get_stage_payload(project, StageName.STORY_GRAPH)
        assert len(graph.nodes) == 7 and len(graph.edges) == 6
        assert sorted(sum(node in {"c01", "c02"} for node in route) for route in complete_routes(graph)) == [1, 2, 2]
    snapshot = storage.recovery.create_snapshot(project)
    with sqlite3.connect(Path(snapshot.location) / "project.sqlite3") as connection:
        stored = json.loads(connection.execute("SELECT material FROM v2_source_outline_source_revisions WHERE revision=1").fetchone()[0])
        assert stored["authoredStructure"] == frozen["structure"]
    with closing(storage.projects.open(project)) as reopened:
        state = reopened.source_outline_state()
        assert state.graph_admission.status == "current"
        assert state.accepted_section_map.mapping.author_source_hash == digest
        assert state.source.material.authored_structure == material.authored_structure
        # Forged origin and stale original source cannot start a new seedless draft.
        initial = reopened.graph_workbench_state().initial_payload
        original = initial.model_copy(deep=True)
        initial.mapping.author_source_hash = "a" * 64
        with pytest.raises(InvalidTransitionError, match="作者结构来源"):
            reopened.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=1,
                expected_draft_revision=0, payload=initial.model_dump(mode="json", by_alias=True))
        changed = material.model_copy(update={"text": material.text + "作者修改。"})
        reopened.save_source_material(expected_source_revision=1, material=changed)
        original.binding_hash = reopened.graph_workbench_state().binding_hash
        with pytest.raises(InvalidTransitionError, match="作者结构来源"):
            reopened.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=1,
                expected_draft_revision=0, payload=original.model_dump(mode="json", by_alias=True))
        with pytest.raises(CreativeHandoffError): assert_outline_settings_current(request, reopened.project().brief.model_copy(update={"node_budget": 8}))


def test_seedless_source_shape_requires_real_authority_and_omission_preserves_existing_bytes():
    material = SourceMaterial(kind="synopsis", title="原有来源", text="原文")
    assert "authoredStructure" not in material.model_dump(mode="json", by_alias=True)
    assert "authored_structure" not in material.model_dump(mode="json")
    base = authored_material().model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="exact synopsis"):
        SourceMaterial.model_validate(base | {"kind": "synopsis", "attribution": None, "adaptationIntent": "",
            "briefOrigin": {"kind": "saved_brief", "revision": 1, "contentHash": "a" * 64}})
    from plotloom.graph_draft_creation import create_graph_draft
    with pytest.raises(ValueError, match="exact accepted author mapping"):
        create_graph_draft(binding_hash="a" * 64, seed=None)


def test_seven_role_source_reaches_installed_production_and_retains_source_identity(tmp_path):
    storage = _storage(tmp_path)
    with closing(storage.projects.create(authored_brief())) as store:
        proposal = _prepare_installable_bridge(store, structure_factory=authored_mapping, source_material=authored_material())
        accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(
            expectedProposalRevision=proposal.revision, expectedContentHash=proposal.content_hash))
        assert accepted.installation.status == "current"
        assert {scene["sectionId"] for scene in proposal.scenes} == {"n00", "n10", "e01", "e02", "e03"}
        assert len(proposal.presentation.runtime_choice["choices"]) == 2
        project = store.manifest.project_id
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_installation().status == "current"


@pytest.mark.parametrize("remove", [False, True])
@pytest.mark.parametrize("with_payload", [False, True])
def test_existing_seedless_recovery_cannot_bless_replaced_or_removed_author_source(tmp_path, remove, with_payload):
    storage = _storage(tmp_path)
    with closing(storage.projects.create(authored_brief())) as store:
        material = authored_material()
        store.save_source_material(expected_source_revision=0, material=material)
        initial = store.graph_workbench_state().initial_payload
        receipt = store.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=0,
            expected_draft_revision=0, payload=initial.model_dump(mode="json", by_alias=True))
        replacement = material.model_copy(update={"authored_structure": None} if remove else {"text": "新的作者来源。"})
        store.save_source_material(expected_source_revision=1, material=replacement)
        state = store.graph_workbench_state()
        with pytest.raises(InvalidTransitionError, match="作者结构来源"):
            store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=receipt.draft_revision,
                expected_binding_hash=state.binding_hash, payload=initial if with_payload else None))
        retained = store.graph_workbench_state().draft
        assert retained.draft_revision == receipt.draft_revision and retained.payload == receipt.payload
        assert store.source_outline_state().graph_admission is None
        assert store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH).revision == 0
