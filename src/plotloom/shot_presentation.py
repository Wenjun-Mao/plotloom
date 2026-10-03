"""Source-bound author amendments, separate from immutable canonical approval."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import Field, StrictInt, model_validator

from .domain import CamelModel
from .production_presentation import stable_hash


class LiteralSource(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    index: StrictInt = Field(ge=0)


class PhysicalPresentation(CamelModel):
    action: str = Field(min_length=1, max_length=4000)
    composition: str = Field(min_length=1, max_length=4000)
    visual_intent: str = Field(max_length=2000)
    motion_intent: str = Field(max_length=2000)
    camera_movement: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def nonblank(self):
        if any(not value.strip() for value in (self.action, self.composition, self.camera_movement)):
            raise ValueError("physical presentation needs action, composition and camera movement")
        return self


class ShotPresentationRequest(CamelModel):
    expected_revision: StrictInt = Field(ge=0)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approval_id: str = Field(min_length=1)
    storyboard_revision: StrictInt = Field(ge=1)
    physical: PhysicalPresentation
    literal_sources: list[LiteralSource] = Field(max_length=32)
    message_presentation: Literal["source", "popped_out_draft", "popped_out_send"]
    reason: str = Field(min_length=1, max_length=2000)
    reviewed: Literal[True]

    @model_validator(mode="after")
    def review_context(self):
        if not self.reason.strip():
            raise ValueError("presentation amendment needs an author explanation")
        keys = [(item.shot_id, item.index) for item in self.literal_sources]
        if len(set(keys)) != len(keys):
            raise ValueError("literal source pointers must be unique")
        if self.message_presentation != "source" and not keys:
            raise ValueError("message preview requires exact source text")
        return self


def source_package(shot: dict, context: dict, predecessor: dict | None) -> dict:
    """The trusted source includes all effective-input dependencies and literals."""
    literals = [
        {"shotId": candidate["id"], "index": index, **deepcopy(text)}
        for candidate in (shot, predecessor) if candidate is not None
        for index, text in enumerate(candidate.get("visibleTexts", []))
    ]
    source = {"shot": shot, "resolvedContext": context,
              "predecessor": predecessor, "literalOptions": literals}
    return {**source, "sourceHash": stable_hash(source)}


def reviewed_projection(source: dict, request: ShotPresentationRequest) -> dict:
    """Resolve exact literal provenance; semantic amendment is explicitly reviewed."""
    if request.source_hash != source["sourceHash"]:
        raise ValueError("shot presentation source changed; review current sources")
    options = {(item["shotId"], item["index"]): item for item in source["literalOptions"]}
    texts = []
    for pointer in request.literal_sources:
        item = options.get((pointer.shot_id, pointer.index))
        if item is None:
            raise ValueError("literal must come from this shot or its immediate scene predecessor")
        texts.append({key: deepcopy(value) for key, value in item.items() if key not in {"shotId", "index"}})
    # Presentation review cannot withdraw canonical dialogue authority. Refuse
    # contradictory nonspoken literals at the shared image/H3 source boundary.
    spoken = [str(cue.get("text") or "") for cue in source["resolvedContext"].get("dialogueCues", [])]
    if any(text["text"] in utterance for text in texts for utterance in spoken):
        raise ValueError("nonspoken presentation text overlaps authored dialogue; resolve the canonical cue first")
    shot = deepcopy(source["shot"])
    shot.update(request.physical.model_dump(mode="json", by_alias=True))
    shot["visibleTexts"] = texts
    return shot


def effective_projection(shot: Any, context: dict, decision: dict | None) -> tuple[Any, dict]:
    if decision is None:
        return shot, context
    effective = type(shot).model_validate(decision["effectiveShot"])
    projected = deepcopy(context)
    # The amended action replaces the mixed source physical direction once.
    # Keep all beat IDs/states, but never reactivate old phone/typing instructions.
    for index, beat in enumerate(projected.get("beats", [])):
        beat["visibleEvent"] = effective.action if index == 0 else ""
    projected["productionPresentation"] = {
        "messagePresentation": decision["review"]["messagePresentation"],
        "reason": decision["review"]["reason"],
    }
    return effective, projected


def message_direction(decision: dict | None) -> str:
    mode = decision["review"]["messagePresentation"] if decision else "source"
    if mode == "popped_out_draft":
        return ("A large front-facing popped-out message preview outside the phone contains the complete exact "
                "unsent draft from the first frame. Compose or review the draft with small hand motions; "
                "do not animate character-by-character completion, send it, or show a sent state or new reply. "
                "The phone has no readable text. The preview text is not spoken.")
    if mode == "popped_out_send":
        return ("The complete exact unsent draft is visible in a large front-facing popped-out message preview "
                "outside the phone from the first frame. Show the deliberate send action and an intelligible "
                "sent-message state afterward, retaining the exact words; no new reply. The phone has no "
                "readable text. The preview text is not spoken. Hand movement alone does not establish sending.")
    return ""
