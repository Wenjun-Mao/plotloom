"""Independent full-source visible-text discovery in the existing native check."""
from typing import Literal

from pydantic import Field

from .domain_base import CamelModel
from .provider_literals import LiteralSpan, provider_path, text_hash

DISCOVERY = 'visibleLiteralDiscovery'
DISCOVERY_VERSION = 'plotloom.visible-literal-discovery.v1'


class VisibleOccurrence(CamelModel):
    span: LiteralSpan
    field_hash: str = Field(pattern=r'^[a-f0-9]{64}$')


class DiscoveredVisibleFact(CamelModel):
    role: Literal['literal_visible_text']
    source_span: LiteralSpan
    source_field_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    intent: Literal['pass', 'reject', 'uncertain']
    relevance: Literal['required', 'not_relevant', 'uncertain']
    presence: Literal['pass', 'reject', 'uncertain', 'not_applicable']
    candidate_occurrences: tuple[VisibleOccurrence, ...]
    explanation: str = Field(min_length=1, max_length=2000)


class VisibleSourceReview(CamelModel):
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    decision: Literal['no_visible_literal', 'visible_literal', 'uncertain']
    facts: tuple[DiscoveredVisibleFact, ...]
    explanation: str = Field(min_length=1, max_length=2000)


class VisibleLiteralDiscovery(CamelModel):
    sources: tuple[VisibleSourceReview, ...]


def discovery_inventory(sources):
    from .content_language_classifier import string_leaves
    return {'version': DISCOVERY_VERSION, 'sources': [
        {'path': path, 'sha256': text_hash(text), 'length': len(text)}
        for path, text in string_leaves(sources)]}


def discovery_verdicts(discovery):
    if discovery is None:
        return set()
    return ({'uncertain'} if any(row.decision == 'uncertain' for row in discovery.sources) else set()) | {
        verdict for row in discovery.sources for fact in row.facts for verdict in (fact.intent, fact.presence)}


def fact_matches(claim, fact):
    """One exact occurrence can satisfy duplicate proof of the same source fact."""
    return all(claim[key] == fact[key] for key in ('role', 'sourceSpan', 'sourceFieldHash'))


def bind_discovery(frozen, discovery, literal_review):
    if DISCOVERY not in frozen:
        if discovery is not None:
            raise ValueError('retained check has no visible-literal discovery contract')
        return
    from .content_language_classifier import string_leaves
    sources = dict(string_leaves(frozen['sources']))
    if frozen[DISCOVERY] != discovery_inventory(frozen['sources']):
        raise ValueError('frozen visible-source inventory differs')
    if discovery is None or [(row.path, row.sha256) for row in discovery.sources] != [
            (item['path'], item['sha256']) for item in frozen[DISCOVERY]['sources']]:
        raise ValueError('discovery must cover every ordered original source leaf')
    leaves = dict(string_leaves(frozen['candidate']))
    roles = {item['path']: item['role'] for item in frozen['inventory']}
    packet = frozen.get('providerLiterals')
    approved = []
    seen = set()

    def exact(span, values, expected_hash):
        text = values.get(span.path)
        if (text is None or text_hash(text) != expected_hash or not 0 <= span.start < span.end <= len(text)
                or text[span.start:span.end] != span.text):
            raise ValueError('discovery requires exact canonical Unicode span and complete field hash')

    for row in discovery.sources:
        if ((row.decision == 'no_visible_literal' and row.facts)
                or row.decision == 'visible_literal' and not row.facts):
            raise ValueError('visible discovery decision must explicitly enumerate its facts')
        for fact in row.facts:
            span = fact.source_span
            exact(span, sources, fact.source_field_hash)
            key = (span.path, span.start, span.end)
            if span.path != row.path or key in seen:
                raise ValueError('discovered fact must address its unique original source leaf occurrence')
            seen.add(key)
            for occurrence in fact.candidate_occurrences:
                exact(occurrence.span, leaves, occurrence.field_hash)
                allowed = (provider_path(frozen['stage'], occurrence.span.path, fact.role) if packet else
                           roles.get(occurrence.span.path) in {'authored_prose', 'exact_source'})
                if occurrence.span.text != span.text or not allowed:
                    raise ValueError('discovered lettering has an invented role or unsupported candidate channel')
            raw = fact.model_dump(mode='json', by_alias=True)
            mapped = [claim for claim in (packet or {}).get('claims', []) if fact_matches(claim, raw)]
            if fact.relevance == 'not_relevant' and (fact.presence != 'not_applicable' or fact.candidate_occurrences):
                raise ValueError('stage-irrelevant discovered lettering requires presence=not_applicable and empty candidateOccurrences')
            if fact.presence == 'not_applicable' and fact.relevance != 'not_relevant':
                raise ValueError('not_applicable discovered lettering presence requires relevance=not_relevant')
            if fact.relevance == 'uncertain' and fact.presence != 'uncertain':
                raise ValueError('uncertain discovered lettering relevance requires presence=uncertain')
            if (fact.relevance == 'required' and fact.presence == 'pass'
                    and not (fact.candidate_occurrences or mapped)):
                raise ValueError('required discovered lettering omission cannot pass')
            if fact.intent == 'pass':
                approved.append(raw)
    if packet and literal_review:
        for review, claim in zip(literal_review.claims, packet['claims'], strict=True):
            if (review.verdict == 'pass' and claim['role'] == 'literal_visible_text'
                    and not any(fact_matches(claim, fact) for fact in approved)):
                raise ValueError('passed visible claim requires independent source-intent discovery')
        for review, fact in zip(literal_review.facts, packet['context']['facts'], strict=True):
            if review.verdict in {'pass', 'not_applicable'} and not any(fact_matches(fact, item) for item in approved):
                raise ValueError('known source-visible fact cannot disappear from discovery')


def discovery_instructions():
    return (
        ' Complete visibleLiteralDiscovery.sources for EVERY ordered original source string in the frozen '
        'visibleLiteralDiscovery.sources inventory, even with zero writer claims or language exceptions. '
        'Use decision=no_visible_literal/visible_literal/uncertain and a source-grounded explanation. '
        'Discover ALL author-intended nonspoken visible lettering in BOTH project languages, including same-language '
        'English labels such as Mira. Language-exception absence, quotation marks, source equality, proper names '
        'and writer flags never establish or erase intent. Each visible_literal decision enumerates typed facts: '
        'literal_visible_text role, exact sourceSpan/sourceFieldHash, independent intent pass/reject/uncertain, '
        'current-stage relevance required/not_relevant/uncertain, presence pass/reject/uncertain/not_applicable '
        'and exact candidateOccurrences with span/fieldHash where present. '
        'relevance=not_relevant requires presence=not_applicable AND candidateOccurrences=[] exactly: '
        'incidental mentions in narrative intent, explanations or names are not current-stage lettering occurrences. '
        'Keep the discovered source-intent fact and explain its stage irrelevance; do not erase source intent. '
        'relevance=uncertain requires presence=uncertain. relevance=required cannot use presence=not_applicable. '
        'A required/pass fact needs exact candidateOccurrences OR exact mapped providerLiterals claims; '
        'candidateOccurrences may be empty when those mapped claims supply the same source fact. '
        'For provider stages those occurrences '
        'must be registered visible provider channels; speech and voice-design fields are not visible text. '
        'A required omitted, translated, altered or negated literal must reject, even with all-English instructions '
        'and no writer claims. no_visible_literal is an explicit semantic judgment against that entire source '
        'scalar, not a default for empty writer arrays. Keep known facts and explain stage irrelevance separately '
        'from source intent. Reject invented labels and arbitrary quoted foreign instructions. Candidate occurrence '
        'paths use candidate-root enums; every sourceSpan uses actual sources-root enums, never $.sources. '
        'This is part of this same distinct checking invocation, not another job or checker.'
    )
