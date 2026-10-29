"""Two prospective native profile grants; existing scope definitions stay frozen."""
from dataclasses import asdict, dataclass

from .persistence.codec import stable_hash

HIGH_RESOLUTION_PROFILE = "minimax_h3_quality8_landscape_1280x704_v2"


@dataclass(frozen=True)
class HighResolutionQaGrant:
    scope_id: str
    project_id: str
    scope_hash: str


HIGH_RESOLUTION_QA_GRANTS = (
    HighResolutionQaGrant("project-language-zh-native-20261029",
        "2458559c-b6cf-4d98-9921-bd169e2b6769",
        "153807a815786fae4b5288afb6f842cf6ef6f4bc9df582e2ef020646a793fb18"),
    HighResolutionQaGrant("project-language-en-native-20261029",
        "a278ed7d-6244-4775-88cf-97250d0ebb22",
        "cbfb37a5d1c02d69ba0866de55a023d9b7ceb531ad57ec8087e5ea5e8aa0ab08"),
)


def high_resolution_request(scope, snapshot):
    if snapshot.get("compilerVersion") != "plotloom.h3-production-brief.v11":
        return False
    grant = next((item for item in HIGH_RESOLUTION_QA_GRANTS
        if item.scope_id == scope.id and item.project_id == scope.project_id), None)
    if grant is None or stable_hash(asdict(scope)) != grant.scope_hash:
        return False
    request = snapshot.get("request", {})
    return (request.get("profileId") == HIGH_RESOLUTION_PROFILE
        and request.get("resolution") == "1280x704"
        and request.get("audio") is True and request.get("aspectPolicy") == "cover_center_crop"
        and all(type(request.get(key)) is int and request[key] == expected for key, expected in {
            "width": 1280, "height": 704, "quality": 8, "profileVersion": 2,
            "durationSeconds": 8, "frameCount": 192, "fps": 24}.items()))


def profile_within_authority(scope, snapshot):
    return snapshot["request"].get("profileId") == scope.profile_id or high_resolution_request(scope, snapshot)


def manifest_profile_within_authority(scope, manifest):
    profile = manifest["setup"]["profileId"]
    targets = manifest["targets"]
    if any(target["snapshot"]["request"].get("profileId") != profile for target in targets):
        return False
    return profile == scope.profile_id or bool(targets) and all(
        high_resolution_request(scope, target["snapshot"]) for target in targets)
