"""Role labels and evidence required for consumed image references."""
REVIEWED_REFERENCE_ROLES = frozenset({
    "character_identity", "scene_continuity", "scene_environment", "prop_identity",
})


def package_reference_role(reference):
    role = reference["role"]
    if role == "character_identity":
        return role + ":" + reference["characterId"]
    if role in {"scene_environment", "prop_identity"}:
        return role + ":" + reference["subjectId"]
    return role


ART_REFERENCE_INSTRUCTION = (
    "ART REFERENCE ROLES: scene_environment:<subjectId> fixes the same physical room's "
    "architecture, surfaces and object layout; prop_identity:<subjectId> fixes that object's "
    "shape, material, color and exact lettering. Use their actual supplied images. Preserve "
    "the same location across narrative scenes and alternative routes. Study-sheet panels, "
    "borders and multiple reference views are never footage or extra story objects. The target "
    "shot owns action, initial state, framing and object position; do not copy another study's "
    "pose, or transfer an isolated reference's white background/exclusions into the shot. "
    "If these owners contradict each other, stop with the exact conflict rather than inventing "
    "a replacement object or room. Include all consumed role hashes in referenceUse. "
)

ART_SUBJECT_INSTRUCTION = (
    "SELECTED ART SOURCE CONTEXT: artReferenceSubjects contains the exact descriptions "
    "of the attached selected Art subjects. A subject.scale value classifies physical size "
    "(for example 手持级 means handheld scale); that field does not prescribe a held pose "
    "or current placement. Explicit target action and initial state own holding and placement. "
    "Read size adjectives in their complete unchanged source context; do not silently rewrite "
    "the composition or disregard an explicit grip/pose requirement. If the complete owners "
    "still genuinely contradict each other, stop and report the exact conflict. "
)
