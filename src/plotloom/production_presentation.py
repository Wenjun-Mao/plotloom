"""Reviewed, exhaustive source presentation; no semantic inference or deletion."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal
from pydantic import Field, StrictInt
from .domain import CamelModel
from hashlib import sha256
from .creative_handoff_exchange import canonical_json


def stable_hash(value: Any) -> str:
    return sha256(canonical_json(value)).hexdigest()


class PresentationSpan(CamelModel):
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=1)
    role: Literal["unassigned", "physical", "visible_text", "runtime_choice", "review_only", "dialogue"]
    rendering: str = ""
    reason: str = ""


class PresentationSource(CamelModel):
    id: str
    kind: Literal["action", "composition", "dialogue"]
    target_id: str
    coordinates: dict[str, Any]
    source_hash: str
    source_text: str
    spans: list[PresentationSpan] = Field(default_factory=list)


class ProductionPresentation(CamelModel):
    version: Literal[1] = 1
    reviewed: bool = False
    sources: list[PresentationSource]
    runtime_choice: dict[str, Any]
    frozen_evidence: dict[str, Any]
    source_hash: str


class PresentationUpdate(CamelModel):
    id: str
    spans: list[PresentationSpan]


class ProductionPresentationUpdateRequest(CamelModel):
    expected_proposal_revision: int = Field(ge=1)
    expected_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_hash: str
    reviewed_complete: Literal[True]
    entries: list[PresentationUpdate]


def prepare_presentation(*, inputs: dict, script: dict, storyboard: dict, mapping: dict) -> ProductionPresentation:
    sources: list[PresentationSource] = []
    sections = {item["episode"]: item["sectionId"] for item in script["sectionBindings"]}
    def add(kind, target, coordinates, raw, field):
        text = raw.get(field)
        if isinstance(text, str) and text.strip():
            sources.append(PresentationSource(id=f"{kind}:{target}", kind=kind, target_id=target,
                coordinates=coordinates | {"field": field}, source_hash=stable_hash(raw), source_text=text))
    for episode in script["episodes"]:
        section = sections[episode["ep"]]
        for index, scene in enumerate(episode["scenes"], 1):
            for order, flow in enumerate(scene["flow"], 1):
                kind, field = ("action", "action") if flow.get("action") else ("dialogue", "line")
                add(kind, f"{section}-s{index}-b{order}", {"stage": "F4", "sectionId": section, "episode": episode["ep"], "sceneIndex": index, "flowIndex": order}, flow, field)
    for episode in storyboard["episodes"]:
        section = sections[episode["ep"]]; counters: dict[int, int] = {}
        for segment_index, segment in enumerate(episode["segments"], 1):
            scene_index = segment["sceneIndex"]
            for cut_index, cut in enumerate(segment["cuts"], 1):
                counters[scene_index] = counters.get(scene_index, 0) + 1
                add("composition", f"{section}-s{scene_index}-c{counters[scene_index]}", {"stage": "F5", "sectionId": section, "episode": episode["ep"], "sceneIndex": scene_index, "segmentIndex": segment_index, "cutIndex": cut_index}, cut, "frame")
    evidence = {"inputs": inputs, "script": script, "storyboard": storyboard, "sectionMap": mapping}
    choices = {"choices": mapping["choices"]} if mapping.get("topology") else mapping["choice"]
    return ProductionPresentation(sources=sources, runtime_choice=choices, frozen_evidence=evidence,
        source_hash=stable_hash(evidence))


def review_presentation(package: ProductionPresentation, request: ProductionPresentationUpdateRequest) -> ProductionPresentation:
    """Validate exact span coverage, not the reviewer's semantic judgment."""
    if request.source_hash != package.source_hash:
        raise ValueError("presentation source hash changed")
    updates = {item.id: item.spans for item in request.entries}
    if len(updates) != len(request.entries) or set(updates) != {item.id for item in package.sources}:
        raise ValueError("presentation review must cover every exact source once")
    sources = []
    choice = package.runtime_choice
    for source in package.sources:
        cursor = 0
        for span in updates[source.id]:
            if span.start != cursor or span.end <= span.start or span.end > len(source.source_text):
                raise ValueError("presentation spans must be contiguous, ordered, exhaustive and in range")
            cursor = span.end
            if span.role == "unassigned":
                raise ValueError("every presentation span needs explicit ownership")
            if source.kind == "dialogue" and span.role != "dialogue" or source.kind != "dialogue" and span.role == "dialogue":
                raise ValueError("spoken words must remain exclusively cue-owned")
            if span.role == "physical" and not span.rendering.strip():
                raise ValueError("physical presentation needs a reviewed faithful rendering")
            if span.role != "physical" and span.rendering:
                raise ValueError("visible/dialogue/runtime text cannot be rewritten")
            if span.role == "review_only" and not span.reason.strip():
                raise ValueError("review-only source direction needs an explicit reason")
            if span.role == "runtime_choice" and not span.reason.strip():
                raise ValueError("runtime-choice span needs an explicit source-choice explanation")
        if cursor != len(source.source_text):
            raise ValueError("presentation review omitted source text")
        sources.append(source.model_copy(update={"spans": updates[source.id]}))
    # Runtime wording comes only from the exact frozen author map, never a rendering.
    choices = choice.get("choices", [choice])
    if any(not item.get("prompt") or len(item.get("outcomes", [])) < 2 for item in choices):
        raise ValueError("presentation requires every exact authored playback choice")
    return package.model_copy(update={"reviewed": True, "sources": sources})


def physical_text(source: PresentationSource) -> str:
    return "\n".join(span.rendering.strip() for span in source.spans if span.role == "physical")


def project_presentation(payload: dict, package: ProductionPresentation) -> dict:
    """Only reviewed media facts enter canonical presentation fields."""
    if not package.reviewed:
        raise ValueError("production presentation must be explicitly reviewed")
    projected = deepcopy(payload)
    by_target = {item.target_id: item for item in package.sources}
    beats = {beat["id"]: beat for beat in projected["sceneBeats"]["beats"]}
    for beat_id, beat in beats.items():
        source = by_target[beat_id]
        physical = physical_text(source)
        beat["description"] = physical or ("对白节拍" if source.kind == "dialogue" else "运行时呈现节拍")
        beat["visibleEvent"] = physical
    links = projected["storyboard"]["shotBeatLinks"]
    for shot in projected["storyboard"]["shots"]:
        source = by_target[shot["id"]]
        covered = [link["beatId"] for link in links if link["shotId"] == shot["id"]]
        shot["action"] = "\n".join(beats[beat]["visibleEvent"] for beat in covered if beats[beat]["visibleEvent"])
        shot["composition"] = physical_text(source)
        shot["title"] = shot["composition"] or shot["action"] or shot["id"]
        shot["visibleTexts"] = [
            {"text": entry.source_text[span.start:span.end], "sourceCoordinates": entry.coordinates,
             "sourceContentHash": entry.source_hash}
            for entry in [*[by_target[beat] for beat in covered], source]
            for span in entry.spans if span.role == "visible_text"
        ]
    return projected
