"""Closed prospective grants for reusing two observed opening images at the end."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OriginalFrameEndGrant:
    scope_id: str
    project_id: str
    shot_id: str
    asset_id: str
    original_hash: str


ORIGINAL_FRAME_END_GRANTS = (
    OriginalFrameEndGrant(
        "project-language-zh-native-20261029", "2458559c-b6cf-4d98-9921-bd169e2b6769",
        "node-1386be18-01df-5912-8dc7-dc0441c84d8f-s1-c1",
        "17535b3c-a61b-40e4-9b87-df242a8dd7bb",
        "a9775ba236e39c1db60ec088506b6f6403d02ba53dd3caa6a049c7f6d75ba198"),
    OriginalFrameEndGrant(
        "project-language-en-native-20261029", "a278ed7d-6244-4775-88cf-97250d0ebb22",
        "node-80ba076b-cc7d-5b86-98ac-2bc998894c69-s1-c1",
        "eb8acafa-c246-4721-afb5-054f230a82d0",
        "328bdd30f60aff2295a0823c142ce3e74498813a8c5a68dfb66f950d539485e0"),
)


def end_frame_within_authority(scope, snapshot):
    ending = snapshot.get("endFrame")
    if ending in (None, {"revision": 0, "assetId": None}):
        return True
    if snapshot.get("compilerVersion") != "plotloom.h3-production-brief.v10" or not isinstance(ending, dict):
        return False
    grant = next((item for item in ORIGINAL_FRAME_END_GRANTS
        if item.scope_id == scope.id and item.project_id == scope.project_id
        and item.shot_id == snapshot["shot"]["id"]), None)
    if grant is None:
        return False
    first, request = snapshot["keyframe"], snapshot["request"]
    provenance = ending.get("provenance")
    return (
        type(ending.get("revision")) is int and ending["revision"] > 0
        and ending.get("assetId") == first.get("assetId") == grant.asset_id
        and ending.get("originalHash") == first.get("originalHash") == grant.original_hash
        and ending.get("mimeType") == first.get("mimeType") in {"image/png", "image/jpeg"}
        and all(type(first.get(key)) is int and first[key] > 0
            and type(ending.get(key)) is int and ending[key] == first[key]
            for key in ("width", "height"))
        and ending.get("aspectPolicy") == request.get("aspectPolicy") == "cover_center_crop"
        and bool(snapshot.get("approvalId")) and ending.get("approvalId") == snapshot["approvalId"]
        and type(snapshot.get("storyboardRevision")) is int and snapshot["storyboardRevision"] > 0
        and ending.get("storyboardRevision") == snapshot["storyboardRevision"]
        and isinstance(snapshot.get("sourceTiming"), dict) and bool(snapshot["sourceTiming"])
        and ending.get("sourceTiming") == snapshot["sourceTiming"]
        and isinstance(provenance, list) and bool(provenance)
        and all(isinstance(item, dict) and item.get("id") and isinstance(item.get("declaration"), dict)
            and item["declaration"] for item in provenance)
        and request.get("durationSeconds") == 8 and request.get("frameCount") == 192
        and request.get("fps") == 24
        and request.get("profileVersion") == 2 and request.get("quality") == 8
        and request.get("width") == 832 and request.get("height") == 480
    )
