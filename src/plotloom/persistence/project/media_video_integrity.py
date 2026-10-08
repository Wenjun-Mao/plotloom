"""Pure frozen-video integrity; neither lifecycle nor current canon is authority."""

from __future__ import annotations

from typing import Any

from ...production_timing import source_seconds_to_milliseconds
from ...video_provider import VideoProductionContract
from ..codec import stable_hash
from ..schema import VideoJobRow


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _texts(mapping: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(_text(mapping.get(key)) for key in keys)


def _positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def frozen_video_source_is_valid(snapshot: dict[str, Any]) -> bool:
    shot, source = snapshot.get("shot"), snapshot.get("sourceTiming")
    if not isinstance(shot, dict) or not isinstance(source, dict):
        return False
    duration = shot.get("durationUnits")
    if (not _text(shot.get("id")) or not _positive_integer(duration)
            or type(source.get("durationUnits")) is not int
            or source["durationUnits"] != duration):
        return False
    if source.get("kind") == "canonical":
        return (source.get("shotId") == shot["id"]
                and _positive_integer(source.get("storyboardRevision")))
    if source.get("kind") != "f5_bridge":
        return False
    cut = source.get("cut")
    if (not isinstance(cut, dict) or cut.get("shotId") != shot["id"]
            or stable_hash(cut) != source.get("cutHash")):
        return False
    try:
        if source_seconds_to_milliseconds(cut.get("seconds")) != duration:
            return False
    except (ValueError, TypeError):
        return False
    revisions = source.get("installedStageRevisions")
    return bool(
        _texts(source, ("admissionId", "proposalContentHash"))
        and _positive_integer(source.get("proposalRevision"))
        and isinstance(revisions, dict) and revisions
        and all(_positive_integer(value) for value in revisions.values())
    )


def _identity_is_valid(snapshot: dict[str, Any]) -> bool:
    identity = snapshot.get("identityLineage")
    if not isinstance(identity, list):
        return False
    for item in identity:
        if (not isinstance(item, dict)
                or not _texts(item, ("characterId", "referenceDecisionId", "characterContextHash"))
                or not _positive_integer(item.get("referenceRevision"))):
            return False
        assets = item.get("assets")
        if (not isinstance(assets, list) or not assets
                or any(not isinstance(asset, dict)
                       or not _texts(asset, ("assetId", "originalHash")) for asset in assets)):
            return False
    review_id = snapshot.get("samePersonReviewId")
    return review_id is None or _text(review_id)


def _provider_request_is_valid(provider: dict[str, Any], request: dict[str, Any]) -> bool:
    """Parse the supported frozen schema without borrowing today's catalog."""
    if (not _texts(provider, ("adapterId", "adapterVersion", "provider", "model"))
            or not _positive_integer(provider.get("capabilityVersion"))
            or not _text(request.get("resolution")) or request.get("audio") is not True):
        return False
    adapter = provider["adapterId"]
    h3 = adapter == "minimax_h3_gateway"
    if h3:
        if (provider["provider"] != adapter or provider.get("costPolicy") != "local_capacity_v1"
                or not _texts(request, ("profileId", "aspectPolicy"))
                or provider["model"] != request["profileId"]
                or any(not _positive_integer(request.get(key)) for key in
                       ("profileVersion", "width", "height", "fps", "frameCount", "quality"))
                or type(request.get("seed")) is not int
                or any(type(request.get(key)) is not bool for key in ("allowLetterbox", "allowCenterCrop"))
                or request["resolution"] != f"{request['width']}x{request['height']}"):
            return False
    elif (adapter != "atlas_wan" or provider["provider"] != "atlascloud"
          or provider["model"] != "alibaba/wan-3.0/image-to-video"
          or provider.get("costPolicy") != "wan_paid_pilot_v1"
          or any(key in request for key in ("profileId", "profileVersion", "width", "height", "fps",
                                           "frameCount", "quality", "seed", "aspectPolicy"))):
        return False
    try:
        VideoProductionContract(
            adapter_id=adapter, adapter_version=provider["adapterVersion"],
            provider=provider["provider"], model=provider["model"],
            capability_version=provider["capabilityVersion"],
            requested_seconds=request["durationSeconds"], resolution=request["resolution"],
            audio=request["audio"], aspect_policy=request.get("aspectPolicy"), seed=request.get("seed"),
            cost_policy=provider["costPolicy"],
            allow_letterbox=request.get("allowLetterbox", False),
            allow_center_crop=request.get("allowCenterCrop", False),
            profile_id=request.get("profileId"), profile_version=request.get("profileVersion"),
            width=request.get("width"), height=request.get("height"), fps=request.get("fps"),
            frame_count=request.get("frameCount"), quality=request.get("quality"),
        )
    except (ValueError, TypeError, KeyError):
        return False
    return True


def frozen_video_request_is_valid(row: VideoJobRow) -> bool:
    """Validate persisted inputs without requiring them to remain current."""
    snapshot = row.snapshot
    if not isinstance(snapshot, dict):
        return False
    if (stable_hash(snapshot) != row.snapshot_hash
            or stable_hash({"snapshot": snapshot, "idempotencyKey": row.idempotency_key})
            != row.request_hash):
        return False
    request, provider, keyframe = (snapshot.get(key) for key in ("request", "provider", "keyframe"))
    if not all(isinstance(value, dict) for value in (request, provider, keyframe)):
        return False
    if (not _positive_integer(row.requested_seconds)
            or type(request.get("durationSeconds")) is not int
            or request["durationSeconds"] != row.requested_seconds):
        return False
    if not _provider_request_is_valid(provider, request):
        return False
    if (not _texts(snapshot, ("approvalId", "storyboardEntityRevisionId"))
            or not _texts(keyframe, ("bindingId", "assetId", "originalHash"))
            or not _positive_integer(keyframe.get("selectionRevision"))
            or not frozen_video_source_is_valid(snapshot)
            or not _identity_is_valid(snapshot)):
        return False
    if snapshot.get("shotPresentation") is not None and not isinstance(snapshot["shotPresentation"], dict):
        return False
    if provider.get("adapterId") == "minimax_h3_gateway":
        duration = snapshot["shot"]["durationUnits"]
        frames = request.get("frameCount")
        if (type(request.get("fps")) is not int or request["fps"] != 24
                or not _positive_integer(frames) or duration * 24 % 1_000
                or frames * 1_000 < duration * 24
                or not isinstance(snapshot.get("endFrame"), dict)):
            return False
        intent = "source_exact" if frames * 1_000 == duration * 24 else "segment_required"
        if snapshot.get("playbackIntent") != intent:
            return False
    return True
