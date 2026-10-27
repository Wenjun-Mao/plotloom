"""Pure existing Art shapes: strict checks/schema only, never replacement payloads."""
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, WithJsonSchema

ART_STRUCTURE_FILENAME = "art-structure-schema.json"
ART_STRUCTURE_CONTRACT = "plotloom.art-structural-result.v1"


def _nonblank(value: str) -> str:
    if not value.strip("\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"):
        raise ValueError("required nonblank text")
    return value


def _nonnull(value):
    if value is None:
        raise ValueError("preset prompt access requires a non-null item")
    return value


def _omitted():
    # Omission is allowed; explicitly supplied null props/usage are not.
    # These validation-only models are discarded, never serialized into a candidate.
    return None


_Text = Annotated[str, AfterValidator(_nonblank)]
_NonNull = Annotated[Any, AfterValidator(_nonnull), WithJsonSchema({"not": {"type": "null"}})]


class _Object(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")


class _Anchor(_Object):
    name: _Text
    desc: _Text


class _State(_Object):
    state: _Text
    prompt: _Text


class _Image(_Object):
    prompt: _Text
    negativePrompt: _Text
    sheet: _Text
    # Existing validators require an array, not string-only elements.
    tags: list[Any]


class _Usage(_Object):
    episodes: list[Any]
    beats: list[Any]


class _Scene(_Object):
    id: Annotated[str, Field(pattern=r"^S[0-9]{2,}$")]
    name: _Text
    primary: bool
    summary: _Text
    anchors: Annotated[list[_Anchor], Field(min_length=3, max_length=5)]
    lighting: Annotated[list[_State], Field(min_length=1)]
    image: _Image
    usage: _Usage = Field(default_factory=_omitted)
    # gateReport also reads this optional extension; it must be mappable.
    states: list[Any] | None = None


class _Prop(_Object):
    id: Annotated[str, Field(pattern=r"^P[0-9]{2,}$")]
    name: _Text
    scale: _Text
    summary: _Text
    anchors: Annotated[list[_Anchor], Field(min_length=3, max_length=5)]
    states: Annotated[list[_State], Field(min_length=1)]
    image: _Image
    relatedScenes: list[Any] | None = None
    usage: _Usage = Field(default_factory=_omitted)
    lighting: list[Any] | None = None


class _Art(_Object):
    source: _Text
    style: str
    scenes: Annotated[list[_Scene], Field(min_length=1)]
    props: list[_Prop] = Field(default_factory=_omitted)


class _PresetScene(_Scene):
    # The preset extension uses item.prompt (not item?.prompt) on this optional list.
    states: list[_NonNull] | None = None


class _PresetProp(_Prop):
    lighting: list[_NonNull] | None = None


class _PresetArt(_Art):
    scenes: Annotated[list[_PresetScene], Field(min_length=1)]
    props: list[_PresetProp] = Field(default_factory=_omitted)


def art_structure_artifact(*, preset: bool) -> dict:
    model = _PresetArt if preset else _Art
    return {"contract": ART_STRUCTURE_CONTRACT, "route": "preset_style" if preset else "saved_brief",
        "schema": model.model_json_schema()}


def require_art_structure_artifact(value, *, preset: bool) -> None:
    import json
    canonical = lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if canonical(value) != canonical(art_structure_artifact(preset=preset)):
        raise ValueError("Art structural marker/generated schema differs from its source owner")


def art_structure_issues(candidate, *, preset: bool) -> tuple[str, ...]:
    """Return every applicable shape error without candidate values or error context."""
    model = _PresetArt if preset else _Art
    try:
        model.model_validate(candidate, strict=True)  # Discard; original bytes remain authoritative.
    except ValidationError as error:
        errors = error.errors(include_input=False, include_context=False, include_url=False)
    else:
        return ()
    vocabulary = {"missing": "required field is missing", "list_type": "must be an array",
        "model_type": "must be an object", "string_type": "must be text", "bool_type": "must be boolean",
        "string_pattern_mismatch": "invalid existing ID format", "too_short": "too few existing required items",
        "too_long": "too many existing allowed items", "value_error": "invalid required value"}
    result = []
    for item in errors:
        path = "$" + "".join(f"[{part}]" if isinstance(part, int) else "." + part for part in item["loc"])
        code = item["type"]
        if code not in vocabulary:
            raise ValueError("unrecognized Art structural validation result")
        result.append(path + ": " + vocabulary[code])
    return tuple(result)


def marked_art_structure(artifacts) -> bool:
    if ART_STRUCTURE_FILENAME not in artifacts:
        return False
    style = artifacts.get("art-style-contract.json")
    if not isinstance(style, dict):
        raise ValueError("marked Art requires frozen style authority")
    require_art_structure_artifact(artifacts[ART_STRUCTURE_FILENAME], preset="authority" not in style)
    return True
