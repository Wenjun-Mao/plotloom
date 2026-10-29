"""Exhaustive string roles; only explicitly owned paths receive exemptions."""
from __future__ import annotations

import re
from hashlib import sha256

CLASSIFIER_VERSION = "plotloom.content-language-classifier.v3"
STAGES = ("outline", "branches", "characters", "art", "script", "storyboard",
          "bridge-intent", "bridge-presentation")

# Paths are schema paths, not a vocabulary heuristic. New readable fields need
# an explicit owner here to be exempt; all other strings require semantic review.
# Extensible upstream output never lets a model create an exempt English field.
_PROSE = {
    "outline": """params.genre params.preferences[] adaptation.core adaptation.cutNote
        adaptation.mergeNote adaptation.keep[].what adaptation.keep[].why
        adaptation.cut[].what adaptation.cut[].why adaptation.merge[].what
        adaptation.merge[].why adaptation.risks[].what adaptation.risks[].plan
        characters[].role characters[].arc characters[].from[] scenes[].reusePlan
        props[].function beats[].type beats[].setup beats[].payoff
        episodes[].synopsis episodes[].hook episodes[].suspense
        episodes[].crowdPlan episodes[].warnings[]""",
    "branches": """nodes[].title nodes[].summary choices[].question
        choices[].options[].label choices[].options[].consequence
        joins[].reconciliation clarifications[]""",
    "characters": """summary characters[].oneLiner characters[].persona.gender
        characters[].persona.ageRange characters[].persona.identity
        characters[].persona.appearance characters[].persona.personality[]
        characters[].persona.temperament characters[].persona.motivation
        characters[].persona.arc characters[].persona.relationships[].relation
        characters[].image.style characters[].image.description
        characters[].image.promptLocal characters[].voice.timbre
        characters[].voice.pitch characters[].voice.pace characters[].voice.accent
        characters[].voice.emotion characters[].voice.referenceHint
        characters[].reviewNotes.sourceNotes characters[].reviewNotes.performanceGuidance""",
    "art": """scenes[].summary scenes[].anchors[].name scenes[].anchors[].desc
        scenes[].lighting[].state scenes[].lighting[].description scenes[].changes scenes[].usage.beats[]
        scenes[].image.description scenes[].image.promptLocal props[].summary
        props[].anchors[].name props[].anchors[].desc props[].states[].state props[].states[].description
        props[].usage.beats[] props[].image.description props[].image.promptLocal""",
    "script": """episodes[].hook episodes[].cliff episodes[].beatsClaimed[]
        episodes[].scenes[].lighting episodes[].scenes[].flow[].action
        episodes[].scenes[].flow[].line episodes[].scenes[].flow[].delivery""",
    "storyboard": """episodes[].segments[].note episodes[].segments[].cuts[].note
        episodes[].segments[].cuts[].composition""",
    "bridge-intent": "entries[].suggestedText",
    "bridge-presentation": "entries[].spans[].rendering entries[].spans[].reason",
}
_IDENTITIES = {
    "outline": """params.adaptMode characters[].id characters[].tier scenes[].id
        props[].id props[].beatIds[] beats[].id beats[].weight
        episodes[].sceneIds[] episodes[].characterIds[] episodes[].propIds[]""",
    "branches": "nodes[].id choices[].nodeId choices[].options[].id joins[].id",
    "characters": "style characters[].id characters[].importance",
    "art": """style scenes[].id scenes[].variantOf props[].id props[].scale props[].relatedScenes[]
        sectionUsage[].sectionId sectionUsage[].sceneIds[] sectionUsage[].propIds[]""",
    "script": """params.contentLocale params.timingPolicyVersion episodes[].scenes[].sceneId
        sectionBindings[].sectionId
        episodes[].scenes[].characters[] episodes[].scenes[].props[]
        episodes[].scenes[].flow[].speaker episodes[].scenes[].flow[].language""",
    "storyboard": """style promptLang params.contentLocale params.timingPolicyVersion
        episodes[].segments[].id episodes[].segments[].cuts[].size
        episodes[].segments[].cuts[].camera episodes[].segments[].cuts[].recipe
        episodes[].segments[].cuts[].characters[] episodes[].segments[].cuts[].props[]""",
    "bridge-intent": "entries[].id",
    "bridge-presentation": "entries[].id entries[].spans[].role",
}
_SOURCES = {
    "outline": "source characters[].name scenes[].name props[].name adaptation.keep[].evidence",
    "characters": """source characters[].name characters[].aliases[]
        characters[].persona.relationships[].name characters[].persona.evidence[]""",
    "art": "source scenes[].name props[].name props[].carriedBy[]",
    "script": "source",
    "storyboard": "source",
}
_TECHNICAL = {
    "characters": """characters[].image.prompt characters[].image.negativePrompt
        characters[].image.sheet characters[].image.tags[] characters[].voice.prompt""",
    "art": """scenes[].lighting[].prompt scenes[].image.prompt
        scenes[].image.negativePrompt scenes[].image.sheet scenes[].image.tags[]
        props[].states[].prompt props[].image.prompt props[].image.negativePrompt
        props[].image.sheet props[].image.tags[]""",
    "storyboard": "episodes[].segments[].h3Prompt episodes[].segments[].cuts[].frame",
}


def string_leaves(value, path="$"):
    """Canonical key order, array order and Unicode codepoint paths are stable."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key in sorted(value):
            if not isinstance(key, str) or any(c in key for c in ".[]"):
                raise ValueError("language inventory requires plain schema field names")
            yield from string_leaves(value[key], path + "." + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from string_leaves(item, f"{path}[{index}]")


def original_sources(request):
    """Only actual narrative sources can justify an exception, never schema prose."""
    inputs = {name.replace(".", "_"): value for name, value in request.input_artifacts.items()
              if name in {"outline.json", "cast.json", "art.json", "script.json",
                          "storyboard.json", "targets.json", "presentation-source.json",
                          "source.json", "book.json"}}
    return {"source": request.source, "inputs": inputs}


def source_occurrence(text, sources):
    if not text:
        return None
    for path, value in string_leaves(sources):
        start = value.find(text)
        if start >= 0:
            return {"path": path, "start": start, "end": start + len(text), "text": text}
    return None


def _owned_source_occurrence(path, text, sources):
    if not text:
        return None
    if path.endswith(".evidence[]") or path == "adaptation.keep[].evidence":
        return source_occurrence(text, sources)  # These fields explicitly own verbatim quotations.
    for source_path, value in string_leaves(sources):
        if value != text:
            continue
        normalized = re.sub(r"\[\d+\]", "[]", source_path)
        if path == "source":
            supported = normalized.endswith((".title", ".source"))
        elif path.startswith("scenes[]"):
            supported = normalized.endswith(".scenes[].name")
        elif path.startswith("props[]") and not path.endswith(".carriedBy[]"):
            supported = normalized.endswith(".props[].name")
        else:
            supported = normalized.endswith((".characters[].name", ".characters[].aliases[]"))
        if supported:
            return {"path": source_path, "start": 0, "end": len(text), "text": text}
    # Mere occurrence in prose does not establish that a model-authored title
    # or ordinary noun is an intentional proper name. The semantic checker
    # must assess it as authored prose and cite a supported exception itself.
    return None


def classify_candidate(stage, candidate, sources, *, original=None):
    if stage not in STAGES:
        raise ValueError("content-language checking supports exactly eight creative stages")
    rules = [(_PROSE, "authored_prose"), (_IDENTITIES, "stable_identity"),
             (_SOURCES, "exact_source"), (_TECHNICAL, "provider_technical")]
    from .outline_echoes import outline_echo_roles
    echoes = outline_echo_roles(candidate, original) if original is not None else {}
    inventory = []
    for path, text in string_leaves(candidate):
        normalized = re.sub(r"\[\d+\]", "[]", path.removeprefix("$."))
        role = "stable_identity" if normalized == "lang" else None
        for registry, kind in rules:
            if normalized in registry.get(stage, "").split():
                role = kind
                break
        if role is None:
            role = "authored_prose"
        echo = echoes.get(path)
        if echo is not None:
            role = echo["role"]
        origin = echo.get("sourceSpan") if echo is not None else (
            _owned_source_occurrence(normalized, text, sources) if role == "exact_source" else None)
        if role == "exact_source" and origin is None:
            # New names are authored work; they do not receive an automatic
            # exception merely because the model put prose in a name field.
            role = "authored_prose"
        item = {"path": path, "sha256": sha256(text.encode()).hexdigest(),
                "role": role, "length": len(text)}
        if origin:
            item["sourceSpan"] = origin
        inventory.append(item)
    return inventory
