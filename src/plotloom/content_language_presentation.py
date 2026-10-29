"""Exact planned visible output of source-bound presentation assignments."""
from .provider_literals import text_hash

PRESENTATION_VIEW = "presentationVisibleTexts"


def presentation_visible_texts(original, candidate):
    if original.stage != "bridge-presentation":
        return None
    from .native_bridge_presentation_contract import (
        frozen_presentation,
        native_presentation_suggestions,
    )
    from .production_presentation import (
        PresentationUpdate,
        bind_presentation_spans,
        visible_text_spans,
    )

    suggestions = native_presentation_suggestions(original, candidate)
    package = frozen_presentation(original)
    sources = bind_presentation_spans(package, [PresentationUpdate(id=entry.id, spans=entry.spans)
                                             for entry in suggestions.entries])
    entry_indexes = {entry.id: index for index, entry in enumerate(suggestions.entries)}
    return [{"entryId": source.id, "entryIndex": entry_indexes[source.id],
             "targetId": source.target_id, "spanIndex": index,
             "sourceSpan": {"path": f"$.inputs.presentation-source_json.sources[{source_index}].sourceText",
                            "start": span.start, "end": span.end, "text": text},
             "sourceFieldHash": text_hash(source.source_text),
             "sourceContentHash": source.source_hash, "sourceCoordinates": source.coordinates,
             "text": text}
            for source_index, source in enumerate(sources)
            for index, span, text in visible_text_spans(source)]


def presentation_witnesses(frozen):
    """Recompute even on retained read; an old check never gains this channel."""
    if PRESENTATION_VIEW not in frozen:
        return {}
    from .creative_handoff_contracts import CreativeHandoffRequest

    original = CreativeHandoffRequest.model_validate(frozen["originalRequest"])
    expected = presentation_visible_texts(original, frozen["candidate"])
    if expected is None or frozen[PRESENTATION_VIEW] != expected:
        raise ValueError("presentation visible output differs from exact source-bound candidate spans")
    return {f"$.{PRESENTATION_VIEW}[{index}].text": item for index, item in enumerate(expected)}


def require_owning_occurrence(frozen, fact, witness):
    """An owning field cannot borrow another equal-looking assignment."""
    package = frozen["originalRequest"]["inputArtifacts"]["presentation-source.json"]
    own_paths = {f"$.inputs.presentation-source_json.sources[{index}].sourceText"
                 for index, _source in enumerate(package["sources"])}
    span = fact.source_span.model_dump(mode="json", by_alias=True)
    expected = witness["sourceSpan"]
    hashes = {text_hash(source["sourceText"]) for source in package["sources"]}
    if span["path"] in own_paths:
        matches = span == expected and fact.source_field_hash == witness["sourceFieldHash"]
    elif fact.source_field_hash in hashes:
        matches = (fact.source_field_hash == witness["sourceFieldHash"]
                   and all(span[key] == expected[key] for key in ("start", "end", "text")))
    else:
        return  # Contextual facts still need the checker's explicit semantic mapping.
    if not matches:
        raise ValueError("presentation owning-source fact requires its own exact projected occurrence")


def bind_presentation_discovery(discovery, witnesses):
    """A model's visible assignment is proposed output, not positive source intent."""
    facts = [fact for row in discovery.sources for fact in row.facts]
    for path, witness in witnesses.items():
        matches = [fact for fact in facts if fact.source_span.model_dump(mode="json", by_alias=True)
                   == witness["sourceSpan"] and fact.source_field_hash == witness["sourceFieldHash"]]
        if len(matches) != 1:
            raise ValueError("every projected visible assignment needs exact independent source-intent discovery")
        fact = matches[0]
        if (fact.relevance == "not_relevant" or fact.presence == "not_applicable"
                or not any(item.span.path == path and item.span.start == 0
                           and item.span.end == len(witness["text"])
                           for item in fact.candidate_occurrences)):
            raise ValueError("projected lettering must retain explicit current presence/intent review")


def presentation_instructions(frozen):
    if PRESENTATION_VIEW not in frozen:
        return ""
    return (
        " For bridge-presentation, presentationVisibleTexts is a TRUSTED derived output view, not writer prose. "
        "Its exact text comes from validated visible_text source spans; nonphysical rendering must stay empty. "
        "For every witness, independently judge its exact sourceSpan/sourceFieldHash and include that fact on "
        "the owning source row, with an occurrence at $.presentationVisibleTexts[index].text, start=0, "
        "end=the text's Unicode length, fieldHash=SHA256 of that entire text. Required/pass presence uses ONLY "
        "these projection paths; text in reasons or physical renderings cannot prove visible output. Owning "
        "source facts must address their own assignment, not another identical character. Contextual source "
        "facts still need explicit semantic mapping; cover every original source row. Empty rendering is not "
        "omission when its exact visible_text source slice is projected. An unsupported visible assignment "
        "requires intent=reject and presence=reject with its projected occurrence; uncertain intent remains "
        "uncertain and blocks adoption. Never invent witnesses or convert actual missing assignments into passes."
    )
