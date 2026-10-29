"""Request-bound leaf ownership shared by primary validation and language checking."""
from __future__ import annotations

from .creative_handoff_identity import canonical_json

OWNERSHIP_FILENAME = "creative-field-ownership.json"
OWNERSHIP_VERSION = "plotloom.creative-field-ownership.v1"


class CreativeFieldError(ValueError):
    def __init__(self, path, rule):
        self.path = path
        super().__init__(f"{path}: {rule}")


def _style(request):
    filename = {"characters": "cast-style-contract.json", "art": "art-style-contract.json"}.get(request.stage)
    return request.input_artifacts.get(filename, {}) if filename else {}


def author_direction(request):
    """Only the author's original direction is source prose, never schema instructions."""
    contract = _style(request)
    value = contract.get("direction") if contract.get("authority") == "saved_brief" else contract.get("authorDirection")
    return value if isinstance(value, str) else None


def _marker(request):
    contract = _style(request)
    if contract.get("authority") == "saved_brief":
        from .autopilot_brief_style import BRIEF_STYLE_LABEL
        return BRIEF_STYLE_LABEL
    if request.stage == "characters" and contract:
        label = contract.get("preset", {}).get("label")
        if not isinstance(label, str) or not label:
            raise ValueError("frozen Cast preset label is unavailable")
        return label
    return None  # Preset Art has no fixed image.style requirement.


def _sections(request):
    return request.input_artifacts.get("section-map.json", {}).get("sections", [])


def _authority(request):
    contract = _style(request)
    keys = ("authority", "direction", "stageInstructionContract", "contentHash")
    if contract.get("authority") != "saved_brief" or any(key not in contract for key in keys):
        return None
    return {key: contract[key] for key in keys}


def creative_field_roles(candidate, request):
    """Validate before exemption; unregistered strings always remain semantic prose."""
    from .content_language_classifier import string_leaves
    from .outline_echoes import outline_echo_roles
    from .dialogue_timing_policy import DialogueDeliveryPace

    roles = outline_echo_roles(candidate, request)

    def exact(path, value, expected, *, source_path=None):
        if canonical_json(value) != canonical_json(expected):
            raise CreativeFieldError(path, "omit the optional echo or copy the frozen value exactly")
        for leaf, text in string_leaves(value, path):
            item = {"role": "stable_identity"}
            if source_path is not None and text:
                item = {"role": "exact_source", "sourceSpan": {"path": source_path,
                    "start": 0, "end": len(text), "text": text}}
            roles[leaf] = item

    if not isinstance(candidate, dict):
        raise CreativeFieldError("$", "candidate must be an object")
    if request.stage in {"characters", "art"}:
        marker = _marker(request)
        collections = ("characters",) if request.stage == "characters" else ("scenes", "props")
        for key in collections:
            for index, subject in enumerate(candidate.get(key, [])):
                if not isinstance(subject, dict):
                    continue  # The stage's structural validator owns malformed containers.
                path = f"$.{key}[{index}]"
                if "sheetImage" in subject:
                    raise CreativeFieldError(path + ".sheetImage", "text-only candidates must omit resource locators")
                image = subject.get("image", {})
                if marker is not None and not isinstance(image, dict):
                    raise CreativeFieldError(path + ".image", "fixed image style requires an image object")
                if isinstance(image, dict):
                    if "sheetImage" in image:
                        raise CreativeFieldError(path + ".image.sheetImage", "text-only candidates must omit resource locators")
                    if marker is not None:
                        exact(path + ".image.style", image.get("style"), marker)
                if request.stage == "characters" and "sectionPresence" in subject:
                    presence, sections = subject["sectionPresence"], _sections(request)
                    if not isinstance(presence, list) or not sections or len(presence) != len(sections):
                        raise CreativeFieldError(path + ".sectionPresence", "copy every frozen section once in source order")
                    for offset, (item, section) in enumerate(zip(presence, sections, strict=True)):
                        prefix = f"{path}.sectionPresence[{offset}]"
                        if not isinstance(item, dict) or set(item) != {"sectionId", "footageMode", "present", "context"}:
                            raise CreativeFieldError(prefix, "only sectionId, footageMode, present and context are allowed")
                        for field in ("sectionId", "footageMode"):
                            if field not in section:
                                raise ValueError("frozen section context is incomplete")
                            exact(prefix + "." + field, item[field], section[field])
                        if type(item["present"]) is not bool or section["footageMode"] == "route_only" and item["present"]:
                            raise CreativeFieldError(prefix + ".present", "use a strict boolean; route-only sections have no filmed presence")
                        if not isinstance(item["context"], str):
                            raise CreativeFieldError(prefix + ".context", "context must be authored project-language prose")
        if "styleAuthority" in candidate:
            value, expected = candidate["styleAuthority"], _authority(request)
            if expected is None or not isinstance(value, dict) or set(value) != set(expected):
                raise CreativeFieldError("$.styleAuthority", "omit or copy exactly the four saved-Brief authority fields")
            for key in expected:
                exact("$.styleAuthority." + key, value[key], expected[key],
                      source_path="$.authorDirection" if key == "direction" else None)
    if request.stage == "art" and "art-structure-schema.json" in request.input_artifacts:
        from .art_structure import art_structure_issues, marked_art_structure
        marked_art_structure(request.input_artifacts)
        issues = art_structure_issues(candidate, preset="authority" not in _style(request))
        if issues:
            raise CreativeFieldError("$", "; ".join(issues))
    if request.stage == "script":
        selectors = {pace.value for pace in DialogueDeliveryPace}
        for ep, episode in enumerate(candidate.get("episodes", [])):
            for sc, scene in enumerate(episode.get("scenes", [])):
                for fl, flow in enumerate(scene.get("flow", [])):
                    if isinstance(flow.get("delivery"), str) and flow["delivery"] in selectors:
                        roles[f"$.episodes[{ep}].scenes[{sc}].flow[{fl}].delivery"] = {"role": "stable_identity"}
    from .provider_literals import bind_provider_literals
    try:
        claims = bind_provider_literals(request, candidate)
    except ValueError as error:
        raise CreativeFieldError("$.providerLiterals", str(error)) from error
    for index, claim in enumerate(claims):
        for path,_text in string_leaves(claim, f"$.providerLiterals[{index}]"):
            roles[path] = {"role": "stable_identity"}
    return roles


def ownership_artifact(request):
    """An additive response-shape projection; it does not replace upstream schemas."""
    schema = {"type": "object", "properties": {}}
    if request.stage in {"characters", "art"}:
        subject = {"type": "object", "not": {"required": ["sheetImage"]}, "properties": {
            "image": {"type": "object", "not": {"required": ["sheetImage"]}, "properties": {}}}}
        marker = _marker(request)
        if marker is not None:
            subject["required"] = ["image"]
            subject["properties"]["image"] |= {"required": ["style"], "properties": {"style": {"const": marker}}}
        authority = _authority(request)
        schema["properties"]["styleAuthority"] = ({"const": authority} if authority is not None else False)
        if request.stage == "characters":
            sections = _sections(request)
            subject["properties"]["sectionPresence"] = {"type": "array", "minItems": len(sections),
                "maxItems": len(sections), "prefixItems": [{"type": "object", "additionalProperties": False,
                    "required": ["sectionId", "footageMode", "present", "context"], "properties": {
                        "sectionId": {"const": section["sectionId"]}, "footageMode": {"const": section["footageMode"]},
                        "present": {"const": False} if section["footageMode"] == "route_only" else {"type": "boolean"},
                        "context": {"type": "string"}}} for section in sections]}
            if not sections:
                subject["properties"]["sectionPresence"] = False
        for key in (("characters",) if request.stage == "characters" else ("scenes", "props")):
            schema["properties"][key] = {"type": "array", "items": subject}
    return {"version": OWNERSHIP_VERSION, "stage": request.stage, "schema": schema}


def assert_ownership_artifact(request):
    if request.input_artifacts.get(OWNERSHIP_FILENAME) != ownership_artifact(request):
        raise ValueError("creative field ownership artifact differs from frozen request owners")


def freeze_field_ownership(request):
    request.input_artifacts[OWNERSHIP_FILENAME] = ownership_artifact(request)
    request.creative_brief += (
        " Read creative-field-ownership.json as an additive response shape. Omit optional machine echoes, "
        "or copy only their exact registered fields and frozen values, without translation. Cast image.style "
        "is the exact saved-Brief marker or preset.label; saved-Brief Art scene AND prop image.style is the "
        "exact Saved Brief direction marker. Preset Art image.style remains readable prose if supplied. "
        "Cast/Art styleAuthority may contain only the four exact saved-Brief fields; direction is the original "
        "author quotation. Optional sectionPresence must cover all section-map sections in source order: "
        "copy sectionId/footageMode, author strict boolean present (false for route_only), and project-language "
        "context. Omit all subject/image sheetImage locators: images belong to the later app-owned phase. "
        "Art lighting AND states arrays on scenes AND props require state, description and prompt; labels and "
        "descriptions are project-language prose, prompts are English provider instructions. Script delivery "
        "is a machine selector only when exactly measured, natural or brisk; any other delivery is readable "
        "performance prose. Notes remain prose; use project-language terms rather than implementation jargon. "
        "Known source IDs may appear literally inside notes, but do not exempt the surrounding prose."
    )
