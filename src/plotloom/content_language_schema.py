"""Frozen response schema, exact coordinates and source-intent relationships."""
from .content_language_classifier import string_leaves
from .provider_literal_discovery import DISCOVERY
from .provider_literal_review import INTENT_REVIEW_CONTRACT


def _current_intent_schema(schema, frozen):
    """Bind each historical interpretation to its explicit current exact-span judgment."""
    schema["properties"]["contract"] = {"type": "string", "const": INTENT_REVIEW_CONTRACT}
    schema["required"] = [*schema.get("required", []), "contract"]
    schema["$defs"]["LanguageException"]["description"] = (
        "literal_visible_text requires exact positive current source-intent discovery: identical sourceSpan "
        "and the complete source-field hash. Provenance, a partial span, or identical words elsewhere are insufficient.")
    review = schema["$defs"]["LiteralFactReview"]
    review["properties"]["intent"] = {"type": "string", "enum": ["pass", "reject", "uncertain"]}
    review["required"] = [*review["required"], "intent"]
    review["allOf"] = [
        {"if": {"properties": {"intent": {"const": "reject"}}, "required": ["intent"]},
         "then": {"properties": {"verdict": {"enum": ["reject", "uncertain", "not_applicable"]}}}},
        {"if": {"properties": {"intent": {"const": "uncertain"}}, "required": ["intent"]},
         "then": {"properties": {"relevance": {"const": "uncertain"}, "verdict": {"const": "uncertain"}}}},
    ]
    discovered = schema["$defs"]["DiscoveredVisibleFact"]
    discovered["allOf"] += [
        {"if": {"properties": {"intent": {"const": "reject"}}, "required": ["intent"]},
         "then": {"properties": {"presence": {"enum": ["reject", "uncertain", "not_applicable"]}}}},
        {"if": {"properties": {"intent": {"const": "uncertain"}}, "required": ["intent"]},
         "then": {"properties": {"relevance": {"const": "uncertain"}, "presence": {"const": "uncertain"}}}},
    ]
    source = schema["$defs"]["VisibleSourceReview"]
    source["allOf"] = [
        {"if": {"properties": {"decision": {"const": "no_visible_literal"}}, "required": ["decision"]},
         "then": {"properties": {"facts": {"items": {"properties": {"intent": {"const": "reject"}}}}}}},
        {"if": {"properties": {"decision": {"const": "visible_literal"}}, "required": ["decision"]},
         "then": {"properties": {"facts": {"contains": {"properties": {"intent": {"const": "pass"}}}}}}},
    ]
    for fact in frozen.get("providerLiterals", {}).get("context", {}).get("facts", []):
        for intent in ("pass", "reject", "uncertain"):
            current = {"properties": {"factId": {"const": fact["id"]}, "intent": {"const": intent}},
                       "required": ["factId", "intent"]}
            exact = {"properties": {key: {"const": fact[key]} for key in ("role", "sourceSpan", "sourceFieldHash")},
                     "required": ["role", "sourceSpan", "sourceFieldHash", "intent"]}
            exact["properties"]["intent"] = {"const": intent}
            schema.setdefault("allOf", []).append({
                "if": {"properties": {"literalReview": {"properties": {"facts": {"contains": current}},
                       "required": ["facts"]}}, "required": ["literalReview"]},
                "then": {"properties": {DISCOVERY: {"properties": {"sources": {"contains": {
                    "properties": {"path": {"const": fact["sourceSpan"]["path"]},
                                   "facts": {"contains": exact}}, "required": ["path", "facts"]}}},
                    "required": ["sources"]}}, "required": [DISCOVERY]},
            })


def language_result_schema(frozen):
    """Freeze separate root coordinates; neither span uses the envelope root."""
    from copy import deepcopy

    from .content_language_contract import ContentLanguageResult

    schema = ContentLanguageResult.model_json_schema(by_alias=True)
    leaves = dict(string_leaves(frozen["candidate"]))
    exception_paths = [item["path"] for item in frozen["inventory"]
                       if item["role"] == "authored_prose" and leaves[item["path"]].strip()]
    finding_paths = [item["path"] for item in frozen["inventory"]
                     if (item["role"] == "authored_prose"
                         or "providerLiterals" in frozen and item["role"] == "provider_technical")
                     and leaves[item["path"]].strip()]
    sources = [path for path, text in string_leaves(frozen["sources"]) if text]

    def span(paths, description):
        value = deepcopy(schema["$defs"]["LanguageSpan"])
        value["properties"]["path"] |= ({"enum": paths} if paths else {"not": {}})
        value["properties"]["path"]["description"] = description
        return value

    exception_candidate = span(exception_paths,
        "Copy a nonempty authored_prose candidate path exactly; relative to candidate root, never $.candidate.")
    finding_candidate = span(finding_paths,
        "Copy a semantically reviewed candidate path exactly; relative to candidate root, never $.candidate.")
    source = span(sources, "Copy a canonical source path exactly; relative to sources root, never $.sources.")
    schema["$defs"]["LanguageException"]["properties"]["candidateSpan"] = exception_candidate
    schema["$defs"]["LanguageException"]["properties"]["sourceSpan"] = source
    schema["$defs"]["LanguageFinding"]["properties"]["span"] = finding_candidate

    coverage_conditions = [
        {"if": {"properties": {"role": {"enum": ["exact_source", "provider_technical", "stable_identity"]}},
                "required": ["role"]},
         "then": {"properties": {"exceptions": {"maxItems": 0}}}},
        {"if": {"properties": {"verdict": {"const": "not_applicable"}}, "required": ["verdict"]},
         "then": {"properties": {"exceptions": {"maxItems": 0}}}},
    ]
    schema["properties"]["coverage"]["items"] = {"allOf": [
        {"$ref": "#/$defs/LanguageCoverage"}, *coverage_conditions]}

    if "providerLiterals" in frozen:
        schema["required"] = [*schema.get("required", []), "literalReview"]
        schema["properties"]["literalReview"] = {"$ref":"#/$defs/ProviderLiteralReview"}
        technical_paths = [item["path"] for item in frozen["inventory"]
            if item["role"] == "provider_technical" and leaves[item["path"]].strip()]
        if technical_paths:
            schema["properties"]["coverage"]["items"]["allOf"].append(
                {"if":{"properties":{"path":{"enum":technical_paths}},"required":["path"]},
                 "then":{"properties":{"verdict":{"enum":["pass","reject","uncertain"]}}}})

    if DISCOVERY in frozen:
        schema["required"] = [*schema.get("required", []), DISCOVERY]
        schema["properties"][DISCOVERY] = {"$ref": "#/$defs/VisibleLiteralDiscovery"}
        fact_schema = schema["$defs"]["DiscoveredVisibleFact"]
        fact_schema["properties"]["sourceSpan"] = deepcopy(source)
        fact_schema["allOf"] = [
            {"if": {"properties": {"relevance": {"const": relevance}}, "required": ["relevance"]},
             "then": {"properties": properties}}
            for relevance, properties in (
                ("not_relevant", {"presence": {"const": "not_applicable"}, "candidateOccurrences": {"maxItems": 0}}),
                ("uncertain", {"presence": {"const": "uncertain"}}),
                ("required", {"presence": {"enum": ["pass", "reject", "uncertain"]}}),
            )
        ]
        from .provider_literals import provider_path, text_hash
        occurrence_paths = [item["path"] for item in frozen["inventory"] if leaves[item["path"]].strip()
            and (provider_path(frozen["stage"],item["path"],"literal_visible_text") if "providerLiterals" in frozen
                 else item["role"] in {"authored_prose","exact_source"})]
        from .content_language_presentation import (
            PRESENTATION_VIEW,
            presentation_witnesses,
        )
        witnesses = presentation_witnesses(frozen)
        occurrence_paths += list(witnesses)
        if PRESENTATION_VIEW in frozen:
            projected_span = span(list(witnesses), "Exact trusted presentationVisibleTexts output path.")
            fact_schema["allOf"].append({
                "if": {"properties": {"presence": {"const": "pass"}}, "required": ["presence"]},
                "then": {"properties": {"candidateOccurrences": {"minItems": 1, "items": {"properties": {
                    "span": projected_span}}}}},
            })
            for path, witness in witnesses.items():
                own_occurrence = {"properties": {
                    "fieldHash": {"const": text_hash(witness["text"])},
                    "span": {"properties": {"path": {"const": path}, "start": {"const": 0},
                        "end": {"const": len(witness["text"])}, "text": {"const": witness["text"]}}}}}
                own_fact = {"properties": {"sourceSpan": {"const": witness["sourceSpan"]},
                    "sourceFieldHash": {"const": witness["sourceFieldHash"]},
                    "relevance": {"enum": ["required", "uncertain"]},
                    "presence": {"enum": ["pass", "reject", "uncertain"]},
                    "candidateOccurrences": {"minItems": 1, "items": own_occurrence}}}
                schema.setdefault("allOf", []).append({"properties": {DISCOVERY: {"properties": {
                    "sources": {"contains": {"properties": {
                        "path": {"const": witness["sourceSpan"]["path"]},
                        "facts": {"contains": own_fact}}}}}}}})
        occurrence = schema["$defs"]["VisibleOccurrence"]["properties"]
        occurrence["span"] = span(occurrence_paths,
            "Canonical candidate-root occurrence or explicitly frozen presentationVisibleTexts path; never $.candidate.")
        source_paths = [item["path"] for item in frozen[DISCOVERY]["sources"]]
        schema["$defs"]["VisibleSourceReview"]["properties"]["path"] = {"type":"string"} | ({"enum":source_paths} if source_paths else {"not":{}})
        schema["$defs"].pop("LiteralSpan",None)
        if frozen["contract"] == INTENT_REVIEW_CONTRACT:
            _current_intent_schema(schema, frozen)
    return schema
