"""Historical cross-shot JSON admission, including snapshot destination bytes."""
import json

from ..persistence.project.image_reviewed_use import (
    resolve_reviewed_use,
    validate_reviewed_source,
)
from .format import ProjectStorageCorruptionError


def assert_cross_shot_contracts(connection, *, asset_home=None):
    try:
        for project_id, asset_id, shot_id, raw in connection.execute(
            "SELECT b.project_id,b.asset_id,b.shot_id,i.intent FROM v2_reviewed_shot_bindings b "
            "JOIN v2_visual_intents i ON i.id=b.visual_intent_id"
        ):
            intent = json.loads(raw)
            if intent.get("targetUse") is not None:
                resolve_reviewed_use(connection, project_id, asset_id, shot_id, intent, asset_home=asset_home)
            else:
                # Preserve ordinary historical admission/currentness semantics.
                # Only a foreign native origin reveals a removed target-use
                # contract; ordinary corrupted source facts remain owned by
                # their existing consumer's currentness/error projection.
                origins = connection.execute(
                    "SELECT j.request FROM v2_image_job_candidates c JOIN v2_image_jobs j ON j.id=c.job_id WHERE c.asset_id=?",
                    (asset_id,),
                )
                origin_shots = (json.loads(item[0]).get("frozenSnapshot", {}).get("shot", {}).get("id") for item in origins)
                if any(isinstance(origin, str) and bool(origin.strip()) and origin != shot_id for origin in origin_shots):
                    raise ValueError("cross-shot native binding lacks explicit target use")
                geometry_origins = connection.execute(
                    "SELECT json_extract(evidence,'$.geometryPreparation.shotId') FROM v2_autopilot_checkpoints "
                    "WHERE project_id=? AND json_extract(evidence,'$.geometryPreparation.output.assetId')=?",
                    (project_id, asset_id),
                )
                if any(isinstance(item[0], str) and bool(item[0].strip()) and item[0] != shot_id for item in geometry_origins):
                    raise ValueError("cross-shot geometry binding lacks explicit target use")
        for project_id, asset_id, raw in connection.execute("SELECT project_id,asset_id,intent FROM v2_visual_intents"):
            intent = json.loads(raw)
            if intent.get("targetUse") is not None:
                resolve_reviewed_use(connection, project_id, asset_id, intent["targetUse"]["targetShotId"], intent,
                    asset_home=asset_home)
        for project_id, raw in connection.execute("SELECT project_id,request FROM v2_image_jobs"):
            request = json.loads(raw)
            snapshot = request.get("frozenSnapshot", {})
            source = snapshot.get("sceneContinuity")
            refs = [item for item in snapshot.get("references", []) if item.get("role") == "scene_continuity"]
            if source is None:
                if refs:
                    raise ValueError("continuity reference lacks its source authority")
                continue
            if (request.get("kind") != "original" or request.get("schemaVersion") != 3
                    or snapshot.get("authority") is not None or snapshot.get("reviewedVisualIntent") is not None
                    or snapshot.get("keyframeAdaptation") is not None
                    or source["sourceShotId"] == snapshot.get("shot", {}).get("id")
                    or len(refs) != 1 or refs[0].get("assetId") != source["assetId"]
                    or refs[0].get("originalHash") != source["originalHash"]):
                raise ValueError("continuity reference does not match its independent target request")
            validate_reviewed_source(connection, project_id, source, asset_home=asset_home)
    except (ValueError, TypeError, KeyError) as error:
        raise ProjectStorageCorruptionError("cross-shot image use evidence is invalid") from error
