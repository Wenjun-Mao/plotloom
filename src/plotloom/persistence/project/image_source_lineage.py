"""One strict single-hop native source resolver shared by all frame consumers."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
from ...autopilot_contracts import CheckpointEvidence
from ...geometry_preparation_contracts import GeometryPreparation
from ..codec import stable_hash
from ...exceptions import InvalidTransitionError
from ...keyframe_preparation import has_matching_aspect
from ..schema import ImageJobRow


def geometry_policy_matches(policy, record, policy_hash):
    """Geometry semantics survived the v2-to-v3 style-authority contract bump."""
    return (record.policy_hash == policy_hash and stable_hash(policy) == policy_hash
        and policy.get("version") in {
            "plotloom.pre-video.v2", "plotloom.pre-video.v3", "plotloom.pre-video.v4"
        }
        and policy.get("geometryPreparation") == {"recipeVersion": record.recipe.version,
            "runtime": record.runtime.model_dump(mode="json", by_alias=True)}
        and (record.recipe.target_width, record.recipe.target_height) == (policy["imageWidth"], policy["imageHeight"]))
@dataclass(frozen=True)
class ImageSource:
    kind: str
    job_id: str
    candidate_id: str
    source_asset_id: str
    source_hash: str
    output_hash: str
    geometry: GeometryPreparation | None = None


def _row(connection, sql, values):
    cursor = connection.execute(sql, values)
    row = cursor.fetchone()
    if row is None:
        raise ValueError("generated source evidence is missing")
    return dict(zip((item[0] for item in cursor.description), row, strict=True))


def _assert_geometry_bytes(connection, *assets, asset_home=None):
    # Geometry is a byte transformation: relational lineage alone cannot prove
    # the retained input/output still exist. Use the admitted folder's confined
    # content-addressed store, including during snapshot destination validation.
    from ...project_storage.artifacts import ProjectArtifactStore, _OwnedArtifactStore
    from ...project_storage.format import ProjectStorageError
    database = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), None)
    if not database:
        raise ValueError("geometry lineage requires a project-owned file store")
    store = ProjectArtifactStore(_OwnedArtifactStore(asset_home or Path(database).parent, create=False), writable=False)
    for asset in assets:
        if not 0 < asset["byte_size"] <= 8 * 1024 * 1024:
            raise ValueError("geometry asset exceeds its bounded byte contract")
        try:
            content = store.get(asset["original_uri"])
        except (OSError, ValueError, ProjectStorageError) as error:
            raise ValueError("geometry source/output bytes unavailable") from error
        if len(content) != asset["byte_size"] or sha256(content).hexdigest() != asset["original_hash"]:
            raise ValueError("geometry source/output bytes changed")


def assert_geometry(connection, record, *, project_id, run_id, asset_home=None):
    """Historical identity validation; currentness is checked separately."""
    from .autopilot_bindings import assert_checkpoint_binding
    source = record.source
    run = _row(connection, "SELECT * FROM v2_autopilot_runs WHERE id=?", (run_id,))
    policy = json.loads(run["policy"])
    checkpoint = _row(connection, "SELECT * FROM v2_autopilot_checkpoints WHERE id=?", (source.checkpoint_id,))
    evidence = CheckpointEvidence.model_validate_json(checkpoint["evidence"])
    decision = _row(connection, "SELECT * FROM v2_autopilot_decisions WHERE id=?", (source.decision_id,))
    selected = json.loads(decision["decision"])
    job = _row(connection, "SELECT * FROM v2_image_jobs WHERE id=?", (source.job_id,))
    request = json.loads(job["request"])
    candidate = _row(connection, "SELECT * FROM v2_image_job_candidates WHERE id=?", (source.candidate_id,))
    delivery = _row(connection, "SELECT * FROM v2_image_job_deliveries WHERE id=?", (source.delivery_row_id,))
    raw = _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (source.asset.asset_id,))
    output = _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (record.output.asset_id,))
    declaration = _row(connection, "SELECT declaration FROM v2_managed_asset_provenance WHERE asset_id=?", (record.output.asset_id,))
    provenance = json.loads(declaration["declaration"])
    if (record.project_id != project_id or record.run_id != run_id or run["project_id"] != project_id
            or not geometry_policy_matches(policy, record, run["policy_hash"])
            or record.preparation_id != stable_hash({"runId": run_id, "operationKey": checkpoint["operation_key"] + ":geometry"})
            or checkpoint["run_id"] != run_id or checkpoint["project_id"] != project_id or checkpoint["state"] != "adopted"
            or evidence.owner != "image" or evidence.subject_id != record.shot_id or evidence.job_id != source.job_id
            or evidence.execution_pin != source.execution_pin or evidence.request_hash != source.request_hash
            or evidence.delivery_hash != source.manifest_hash or evidence.result.get("assetId") != source.asset.asset_id
            or evidence.result.get("geometryCompatible") is not False
            or decision["run_id"] != run_id or decision["project_id"] != project_id
            or decision["checkpoint_id"] != checkpoint["id"] or decision["scope"] != "provisional_selection"
            or {"assetId": source.asset.asset_id, "originalHash": source.asset.original_hash} not in selected["selectedAssets"]
            or any(item["project_id"] != project_id for item in (job, raw, output))
            or job["request_hash"] != source.request_hash or stable_hash(request) != source.request_hash
            or request.get("kind") != "original" or request.get("frozenSnapshot", {}).get("shot", {}).get("id") != record.shot_id
            or candidate["job_id"] != source.job_id or candidate["asset_id"] != source.asset.asset_id
            or candidate["role"] != "original" or candidate["output_hash"] != source.asset.original_hash
            or candidate["delivery_id"] != delivery["id"] or delivery["job_id"] != source.job_id
            or delivery["state"] != "accepted" or delivery["delivery_id"] != source.delivery_id or delivery["manifest_hash"] != source.manifest_hash
            or (raw["original_hash"], raw["width"], raw["height"]) != (source.asset.original_hash, source.asset.width, source.asset.height)
            or (output["original_hash"], output["width"], output["height"]) != (record.output.original_hash, record.output.width, record.output.height)
            or output["mime_type"] != "image/png" or output["id"] == raw["id"]
            or provenance.get("origin") != "plotloom_geometry_preparation" or provenance.get("preparationId") != record.preparation_id
            or has_matching_aspect(raw["width"], raw["height"], policy["imageWidth"], policy["imageHeight"])):
        raise ValueError("geometry preparation differs from its frozen local/native authority")
    _assert_geometry_bytes(connection, raw, output, asset_home=asset_home)
    assert_checkpoint_binding(connection, project_id, "adopted", evidence, run_id=run_id,
        operation_key=checkpoint["operation_key"], asset_home=asset_home)


def resolve_image_source(connection, project_id, asset_id, *, shot_id=None, asset_home=None):
    asset = _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (asset_id,))
    if asset["project_id"] != project_id:
        raise ValueError("generated source belongs to another project")
    declarations = list(connection.execute("SELECT declaration FROM v2_managed_asset_provenance WHERE asset_id=?", (asset_id,)))
    origin = json.loads(declarations[0][0]).get("origin") if len(declarations) == 1 else None
    candidates = list(connection.execute("SELECT id,job_id,output_hash FROM v2_image_job_candidates WHERE asset_id=?", (asset_id,)))
    if origin == "plotloom_geometry_preparation":
        if candidates:
            raise ValueError("local derivative cannot impersonate a native candidate")
        checkpoints = list(connection.execute("SELECT id,run_id,project_id,state,evidence FROM v2_autopilot_checkpoints WHERE project_id=? AND json_extract(evidence,'$.geometryPreparation.output.assetId')=?", (project_id, asset_id)))
        if len(checkpoints) != 1 or checkpoints[0][3] != "adopted":
            raise ValueError("geometry derivative lacks one immutable preparation checkpoint")
        checkpoint_id, run_id, project, state, raw = checkpoints[0]
        evidence = CheckpointEvidence.model_validate_json(raw)
        geometry = evidence.geometry_preparation
        if evidence.owner != "geometry-preparation" or geometry is None or evidence.subject_id != geometry.shot_id:
            raise ValueError("geometry derivative typed owner changed")
        assert_geometry(connection, geometry, project_id=project, run_id=run_id, asset_home=asset_home)
        decisions = list(connection.execute("SELECT decision FROM v2_autopilot_decisions WHERE checkpoint_id=? AND scope=?", (checkpoint_id, "geometry_preparation")))
        if len(decisions) != 1 or json.loads(decisions[0][0]).get("evidence") != evidence.model_dump(mode="json", by_alias=True):
            raise ValueError("geometry derivative lacks its exact local authority decision")
        if shot_id is not None and geometry.shot_id != shot_id:
            raise ValueError("geometry derivative targets a different shot")
        return ImageSource("managed_geometry_derivative", geometry.source.job_id, geometry.source.candidate_id,
            geometry.source.asset.asset_id, geometry.source.asset.original_hash, geometry.output.original_hash, geometry)
    if not candidates:
        if origin == "codex_image_job":
            raise ValueError("native output lacks its candidate evidence")
        # A forged/missing declaration cannot disguise a retained typed derivative.
        retained = connection.execute("SELECT 1 FROM v2_autopilot_checkpoints WHERE project_id=? AND json_extract(evidence,'$.geometryPreparation.output.assetId')=?", (project_id, asset_id)).fetchone()
        if retained:
            raise ValueError("geometry derivative declaration is missing or changed")
        return None
    if len(candidates) != 1:
        raise ValueError("native source candidate identity is ambiguous")
    candidate_id, job_id, digest = candidates[0]
    job = _row(connection, "SELECT * FROM v2_image_jobs WHERE id=?", (job_id,))
    if job["project_id"] != project_id or digest != asset["original_hash"]:
        raise ValueError("native source bytes or owner changed")
    if shot_id is not None and json.loads(job["request"]).get("frozenSnapshot", {}).get("shot", {}).get("id") != shot_id:
        raise ValueError("native output targets a different shot")
    return ImageSource("native_output", job_id, candidate_id, asset_id, digest, digest)


def source_in_session(session, project_id, asset_id, *, shot_id=None):
    try:
        return resolve_image_source(session.connection().connection.driver_connection, project_id, asset_id, shot_id=shot_id)
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidTransitionError(str(error)) from error


def current_source_in_session(session, project_id, asset_id, currentness, *, shot_id=None):
    source = source_in_session(session, project_id, asset_id, shot_id=shot_id)
    if source:
        job = session.get(ImageJobRow, source.job_id)
        if job is None or job.state != "delivered" or not currentness.image_job_is_current_in_session(session, job):
            raise InvalidTransitionError("generated source is no longer currently applicable")
    return source
