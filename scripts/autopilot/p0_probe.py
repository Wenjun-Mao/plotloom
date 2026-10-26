"""Disposable P0 seam observations, never an autopilot acceptance claim."""
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

BASELINE = "731cfdbfb0d9139254e30c34c2a8e7669a98ddba"
subprocess.run(["git", "diff", "--exit-code", BASELINE, "--", "src/plotloom", "tests"], check=True, stdout=subprocess.DEVNULL)

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_identity import canonical_json
from plotloom.stage_contracts import StageName
from plotloom.keyframe_preparation import has_matching_aspect
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.current_schema import expected_project_schema_objects
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.same_person_review_contracts import SamePersonReviewRequest
from plotloom.source_outline_contracts import OutlineAcceptRequest, SourceMaterial
from plotloom.source_structures import complete_routes
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.source_outline_fixtures import _deliver, _material, _request

receipt = {
    "sourceRevision": BASELINE,
    "nativeSubmissions": 0,
    "deliveryKind": "deterministic offline fixtures",
    "priorLayoutHashAlgorithm": "sha256(canonical_json(schema_objects))",
    "priorLayoutHash": sha256(canonical_json(expected_project_schema_objects())).hexdigest(),
    "priorTableCount": sum(item[0] == "table" for item in expected_project_schema_objects()),
    "humanIdentityMaximum": SamePersonReviewRequest.model_json_schema(by_alias=True)["properties"]["comparisons"]["maxItems"],
}
layout_path = Path("docs/verification/2026-10-12-pre-video-autopilot-prior-layout.json")
archived = json.loads(layout_path.read_text())
assert archived == [list(row) for row in expected_project_schema_objects()]
receipt["priorLayoutFileHash"] = sha256(layout_path.read_bytes()).hexdigest()
try:
    SamePersonReviewRequest(binding_id="p0-fixture", expected_review_revision=0,
        reviewer="offline diagnostic", notes="Not persisted human evidence.",
        comparisons=[{"characterId": f"fixture-{index}", "judgment": "pass",
            "identityNotes": "Schema fixture only.", "stateNotes": "Schema fixture only."}
            for index in range(9)])
except ValidationError as error:
    assert any(item["type"] == "too_long" for item in error.errors())
    receipt["nineCharacterReviewRejected"] = True
else:
    raise AssertionError("baseline identity review unexpectedly admitted nine characters")
source = SourceMaterial(kind="synopsis", title="  exact title  ", text="  exact synopsis  ")
receipt["existingSourceTrimsBriefWhitespace"] = source.title != "  exact title  " and source.text != "  exact synopsis  "
receipt["geometryAdmissionFacts"] = {
    "portraitExactAspect": has_matching_aspect(720, 1280, 9, 16),
    "portraitDifferentDimensionsSameAspect": has_matching_aspect(1080, 1920, 9, 16),
    "portraitTwoToThreeRejected": not has_matching_aspect(1024, 1536, 9, 16),
    "landscapeExactAspect": has_matching_aspect(1280, 720, 16, 9),
    "landscapeThreeToTwoRejected": not has_matching_aspect(1536, 1024, 16, 9),
}
assert all(receipt["geometryAdmissionFacts"].values())
with TemporaryDirectory(prefix="plotloom-autopilot-p0-") as directory:
    root = Path(directory)
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    material = _material()
    store.save_source_material(expected_source_revision=0, material=material)
    request = _request(project_id, material)
    store.prepare_outline_candidate(request)
    store.admit_outline_delivery(_deliver(store, request))
    store.accept_outline_candidate(OutlineAcceptRequest(job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0))
    source_home = store.home
    retained = sorted(path.relative_to(source_home).as_posix() for path in (source_home / "outputs" / "creative-handoff").rglob("*") if path.is_file())
    store.close()
    snapshot = storage.recovery.create_snapshot(project_id)
    copied = {item.relative_path for item in snapshot.manifest.files}
    omitted = sorted(set(retained) - copied)
    assert retained and omitted == retained
    receipt["snapshotOmittedRetainedCreativeFiles"] = omitted
    storage.projects.close_project(project_id)
    destination = ProjectFolderStorage(outputs_root=root / "restored", application_data_root=root / "restored-application")
    try:
        destination.recovery.restore(source_home)
    except ProjectStorageCorruptionError as error:
        receipt["directFolderRestoreRefusal"] = str(error)
    else:
        raise AssertionError("baseline direct restore unexpectedly admitted creative tree")
    planning = storage.projects.create(FIXED_CHINESE_BRIEF)
    proposal = _prepare_installable_bridge(planning)
    planning.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
    graph = planning.authoring.get_stage_payload(planning.manifest.project_id, StageName.STORY_GRAPH)
    board = planning.authoring.get_stage_payload(planning.manifest.project_id, StageName.STORYBOARD)
    beats = planning.authoring.get_stage_payload(planning.manifest.project_id, StageName.SCENE_BEATS)
    scene_nodes = {scene.id: scene.story_node_id for scene in beats.scenes}
    routes = complete_routes(graph)
    required = {shot.id for shot in board.shots}
    route_occurrences = sum(sum(scene_nodes[shot.scene_id] in route for shot in board.shots) for route in routes)
    receipt["offlineManualPlanningFixture"] = {
        "routes": len(routes), "uniqueShots": len(required), "routeShotOccurrences": route_occurrences,
        "allShotsReachable": all(any(scene_nodes[shot.scene_id] in route for route in routes) for shot in board.shots),
        "routeOnlyNodes": [node.id for node in graph.nodes if node.footage_mode == "route_only"],
        "shotIdsUnique": len(required) == len(board.shots),
    }
    assert receipt["offlineManualPlanningFixture"]["allShotsReachable"]
    assert not set(scene_nodes.values()).intersection(receipt["offlineManualPlanningFixture"]["routeOnlyNodes"])
    assert len(required) == len(board.shots)
    planning.close()
destination = Path(".local/autopilot-p0")
destination.mkdir(parents=True, exist_ok=True)
(destination / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(receipt, ensure_ascii=False, indent=2))
