"""Independent literal intent, relevance and completeness in the existing checker."""
from typing import Literal

from pydantic import Field

from .domain_base import CamelModel


class LiteralClaimReview(CamelModel):
    index: int = Field(strict=True, ge=0)
    verdict: Literal["pass", "reject", "uncertain"]
    explanation: str = Field(min_length=1, max_length=2000)


class LiteralFactReview(CamelModel):
    fact_id: str
    relevance: Literal["required", "not_relevant", "uncertain"]
    verdict: Literal["pass", "reject", "uncertain", "not_applicable"]
    explanation: str = Field(min_length=1, max_length=2000)


class ProviderLiteralReview(CamelModel):
    claims: tuple[LiteralClaimReview, ...]
    facts: tuple[LiteralFactReview, ...]


def bind_literal_review(frozen, review, discovery=None):
    if "providerLiterals" not in frozen:
        if review is not None:
            raise ValueError("original check has no provider literal review contract")
        return
    if review is None:
        raise ValueError("complete independent provider literal review is required")
    packet = frozen["providerLiterals"]
    if [item.index for item in review.claims] != list(range(len(packet["claims"]))):
        raise ValueError("literal review must cover every exact occurrence in order")
    facts = packet["context"]["facts"]
    if [item.fact_id for item in review.facts] != [item["id"] for item in facts]:
        raise ValueError("literal review must cover all established source facts, even with no claims")
    for item in review.facts:
        from .provider_literal_discovery import fact_matches
        fact = next(fact for fact in facts if fact["id"] == item.fact_id)
        modern = "visibleLiteralDiscovery" in frozen
        claims = [claim for claim in packet["claims"] if (
            fact_matches(claim, fact) if modern else claim["sourceFactId"] == item.fact_id)]
        independently_present = modern and any(fact_matches(fact, found.model_dump(mode="json", by_alias=True))
            and found.intent == "pass" and found.presence == "pass" and found.candidate_occurrences
            for row in (discovery.sources if discovery else ()) for found in row.facts)
        if ((item.relevance == "not_relevant") != (item.verdict == "not_applicable")
                or item.relevance == "not_relevant" and claims
                or item.relevance == "uncertain" and item.verdict != "uncertain"
                or item.relevance == "required" and item.verdict == "pass" and not (claims or independently_present)):
            raise ValueError("required literal omissions cannot pass; relevance requires explicit semantic judgment")


def literal_verdicts(review):
    return {item.verdict for item in (*review.claims,*review.facts)} if review is not None else set()


def literal_review_instructions():
    return (
        " For this new provider-literal contract, every nonempty provider_technical coverage leaf also needs "
        "pass/reject/uncertain: check its residual instructions are English after ONLY verified literal/spoken "
        "spans, with exact findings for wrong-language residuals. Other roles keep their existing rules. "
        "Also complete literalReview: assess EVERY providerLiterals.claims occurrence for actual original author "
        "intent, exact visible/nonspoken versus spoken role, contextual relevance, negation and instruction "
        "laundering. Provenance equality is insufficient. Review EVERY established providerLiterals.context.facts "
        "entry for this stage even when claims is empty. Set relevance=required/not_relevant/uncertain with a "
        "specific source-grounded explanation. A required visible fact omitted, translated, negated or altered in "
        "the provider instructions must reject, including all-English Art that drops required lettering. Required "
        "facts can pass only with exact mapped occurrences. not_relevant/not_applicable requires an actual "
        "stage/source reason, never merely missing claims. Every claim needs pass/reject/uncertain. Technical "
        "not_applicable inventory coverage DOES NOT certify literals, intent, relevance or completeness. Refuse "
        "invented labels, arbitrary quoted foreign instructions, names as identity in forbidden channels, and "
        "dialogue in image/voice-design fields. This is the same checking invocation, not a separate engine."
    )
