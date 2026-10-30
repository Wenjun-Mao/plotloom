"""Exact provider-literal provenance; semantic intent remains an independent judgment."""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Literal

from pydantic import Field

from .creative_handoff_identity import canonical_json
from .domain_base import CamelModel

LITERAL_INPUT = "provider-literal-contract.json"
LITERAL_VERSION = "plotloom.provider-literals.v2"
LITERAL_STAGES = {"characters", "art", "storyboard"}
HASH = r"^[a-f0-9]{64}$"


class LiteralSpan(CamelModel):
    path: str = Field(min_length=1, max_length=1000)
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, ge=1)
    text: str = Field(min_length=1, max_length=20000)


class ProviderLiteral(CamelModel):
    role: Literal["literal_visible_text", "spoken_dialogue"]
    candidate_span: LiteralSpan
    source_span: LiteralSpan
    candidate_field_hash: str = Field(pattern=HASH)
    source_field_hash: str = Field(pattern=HASH)
    source_fact_id: str | None = Field(default=None, pattern=HASH)


def digest(value):
    return sha256(canonical_json(value)).hexdigest()


def text_hash(text):
    return sha256(text.encode()).hexdigest()


def provider_path(stage, path, role):
    """Registered channels, never source-substring or ID-looking heuristics."""
    if stage == "characters":
        return role == "literal_visible_text" and re.fullmatch(r"\$\.characters\[\d+\]\.image\.(prompt|sheet|negativePrompt|tags\[\d+\])", path) is not None
    if stage == "art":
        return role == "literal_visible_text" and re.fullmatch(r"\$\.(scenes|props)\[\d+\]\.(image\.(prompt|sheet|negativePrompt|tags\[\d+\])|(lighting|states)\[\d+\]\.prompt)", path) is not None
    if stage == "storyboard":
        return re.fullmatch(r"\$\.episodes\[\d+\]\.segments\[\d+\]\." + (r"h3Prompt" if role == "spoken_dialogue" else r"(h3Prompt|cuts\[\d+\]\.frame)"), path) is not None
    return False


def literal_policy_identity():
    from .validation_resources import policy_resource
    paths = ["src/plotloom/"+name for name in ("provider_literals.py", "provider_literal_dialogue.py", "provider_literal_review.py", "provider_literal_preparation.py", "provider_literal_discovery.py", "validation_resources.py")]
    paths += [f"third_party/shuohao-skills/skills/{skill}/scripts/provider-literals.mjs" for skill in ("novel-art","novel-characters","novel-storyboard")]
    values = {name: sha256(policy_resource(name).read_bytes()).hexdigest() for name in paths}
    return digest(values), values[paths[-1]]



def literal_claim_schema(source_paths):
    from copy import deepcopy
    schema = ProviderLiteral.model_json_schema(by_alias=True)
    source = deepcopy(schema["$defs"]["LiteralSpan"])
    source["properties"]["path"] |= {"enum":list(source_paths)} if source_paths else {"not":{}}
    source["properties"]["path"]["description"] = "Exact context.sources key, relative to sources root; never $.sources."
    schema["properties"]["sourceSpan"] = source
    return schema

def freeze_provider_context(request, *, facts=(), retained_sources=None):
    from .content_language_classifier import original_sources, string_leaves
    retained = dict(retained_sources or {})
    request.input_artifacts[LITERAL_INPUT] = {"retainedSources":retained}
    sources = {path: {"text": text, "sha256": text_hash(text)} for path, text in string_leaves(original_sources(request)) if text}
    policy_hash, helper_hash = literal_policy_identity()
    context = {"policyHash":policy_hash,"helperHash":helper_hash,"version": LITERAL_VERSION, "stage": request.stage, "sources": sources, "facts": list(facts),
               "claimSchema": literal_claim_schema(sources), "retainedSources":retained}
    context["contentHash"] = digest(context)
    request.input_artifacts[LITERAL_INPUT] = context
    return context


def validate_context(request):
    from .content_language_classifier import original_sources, string_leaves
    context = request.input_artifacts[LITERAL_INPUT]
    expected_sources = {path: {"text": text, "sha256": text_hash(text)} for path, text in string_leaves(original_sources(request)) if text}
    if (set(context) != {"version", "stage", "sources", "facts", "claimSchema", "contentHash", "policyHash", "helperHash", "retainedSources"}
            or (context["policyHash"],context["helperHash"]) != literal_policy_identity()
            or context["version"] != LITERAL_VERSION or context["stage"] != request.stage
            or context["sources"] != expected_sources
            or context["claimSchema"] != literal_claim_schema(expected_sources)
            or context["contentHash"] != digest({k:v for k,v in context.items() if k != "contentHash"})):
        raise ValueError("frozen provider literal context differs from original source owners")
    for key,value in context["retainedSources"].items():
        if (set(value) != {"text","sha256"} or not isinstance(value["text"],str)
                or key != text_hash(value["text"]) or value["sha256"] != key):
            raise ValueError("retained literal source identity differs")
    identifiers = set()
    used_retained = set()
    for fact in context["facts"]:
        if (set(fact) != {"id", "role", "sourceSpan", "sourceFieldHash", "evidence"}
                or fact["role"] not in {"literal_visible_text", "spoken_dialogue"}
                or fact["id"] != digest({k:fact[k] for k in ("role","sourceSpan","sourceFieldHash")}) or fact["id"] in identifiers):
            raise ValueError("frozen provider literal fact identity differs")
        evidence = fact["evidence"]
        if (not isinstance(evidence,list) or not evidence or len({digest(item) for item in evidence}) != len(evidence)
                or any(not isinstance(item,dict) or set(item) != {"checkJobId","bindingHash","candidateHash","resultHash","receiptHash"}
                    or not isinstance(item["checkJobId"],str) or not item["checkJobId"]
                    or any(not isinstance(item[key],str) or re.fullmatch(HASH,item[key]) is None
                        for key in ("bindingHash","candidateHash","resultHash","receiptHash")) for item in evidence)):
            raise ValueError("provider literal fact requires distinct receipt-bound witnesses")
        span = LiteralSpan.model_validate(fact["sourceSpan"])
        _span(span, expected_sources, fact["sourceFieldHash"])
        identifiers.add(fact["id"])
        if span.path.startswith("$.retainedVisibleSources."):
            used_retained.add(span.path.removeprefix("$.retainedVisibleSources."))
    if used_retained != set(context["retainedSources"]):
        raise ValueError("retained literal sources require receipt-backed fact ownership")
    return context


def _span(span, leaves, expected_hash):
    value = leaves.get(span.path)
    if (value is None or value["sha256"] != expected_hash or not 0 <= span.start < span.end <= len(value["text"])
            or value["text"][span.start:span.end] != span.text):
        raise ValueError("provider literal requires exact Unicode source/candidate spans and field hashes")


def bind_provider_literals(request, candidate):
    """Bind candidate proposals, not semantic intent; no text is normalized or rewritten."""
    from .content_language_classifier import string_leaves
    claims = candidate.get("providerLiterals", [])
    if LITERAL_INPUT not in request.input_artifacts:
        if claims:
            raise ValueError("provider literals require a frozen source context")
        return []
    context = validate_context(request)
    if not isinstance(claims, list) or len(claims) > 256:
        raise ValueError("provider literal claims must be a bounded array")
    leaves = {path: {"text": text, "sha256": text_hash(text)} for path,text in string_leaves(candidate)}
    facts = {fact["id"]: fact for fact in context["facts"]}
    spans, result = {}, []
    for raw in claims:
        claim = ProviderLiteral.model_validate(raw)
        a,b = claim.candidate_span,claim.source_span
        _span(a, leaves, claim.candidate_field_hash); _span(b, context["sources"], claim.source_field_hash)
        if a.text != b.text or not provider_path(request.stage, a.path, claim.role):
            raise ValueError("provider literal role is not allowed in this exact channel")
        if any(a.start < end and start < a.end for start,end in spans.get(a.path, [])):
            raise ValueError("provider literal occurrences must not overlap")
        spans.setdefault(a.path, []).append((a.start,a.end))
        if claim.source_fact_id is not None:
            fact = facts.get(claim.source_fact_id)
            if fact is None or (fact["role"],fact["sourceSpan"],fact["sourceFieldHash"]) != (
                    claim.role,b.model_dump(mode="json",by_alias=True),claim.source_field_hash):
                raise ValueError("provider literal differs from its established semantic fact")
        result.append(claim.model_dump(mode="json",by_alias=True))
    from .provider_literal_dialogue import script_literal_claims
    spoken = script_literal_claims(request, candidate)
    for claim in result:
        if claim["role"] == "spoken_dialogue" and claim not in spoken:
            raise ValueError("spoken literal claim differs from exact Script-owned channel")
    for claim in spoken:
        if claim not in result:
            a = claim["candidateSpan"]
            if any(a["start"] < end and start < a["end"] for start,end in spans.get(a["path"], [])):
                raise ValueError("visible/spoken literal roles must not overlap")
            result.append(claim)
    return result


def provider_literal_instructions():
    return (
        " Read provider-literal-contract.json. This request overrides blanket no-CJK/name rules ONLY for exact "
        "bound visible/spoken occurrences; all structural/style/reference/timing gates remain. Provider directions stay English. Preserve exact author-intended "
        "visible lettering without translating it. For EACH occurrence inside a registered provider field, propose "
        "providerLiterals using claimSchema: literal_visible_text or spoken_dialogue, exact candidateSpan/sourceSpan "
        "paths (candidate root $.props[0].image.prompt; source root $.source.text or an EXACT key in context.sources; "
        "never $.candidate or $.sources prefixes), Unicode codepoint offsets/text and SHA-256 of the complete scalar fields; use sourceFactId when an "
        "established fact applies, otherwise null. Provenance is not intent proof. Never invent lettering from an "
        "arbitrary source substring, quote foreign instructions, or move visible text/dialogue into voice-design "
        "prompts. Spoken claims belong only to exact Script-owned <d>[language]dialogue</d> in H3. Quotation marks "
        "alone exempt nothing. Preserve every relevant required source literal, including facts[]; omitting claims "
        "cannot waive required lettering. The existing independent checker reviews intent, relevance and omissions."
    )
