"""Receipt-bound upstream visible facts, including same-language semantic discovery."""
from .provider_literals import LITERAL_INPUT, digest, freeze_provider_context, text_hash


def passed_visible_sources(frozen, result):
    """Retained contracts contribute only the evidence they actually established."""
    for coverage in result.coverage:
        for exception in coverage.exceptions:
            if exception.kind == 'literal_visible_text':
                yield exception.source_span.model_dump(mode='json', by_alias=True)
    if result.visible_literal_discovery is not None:
        for source in result.visible_literal_discovery.sources:
            for fact in source.facts:
                if fact.intent == 'pass' and fact.presence in {'pass', 'not_applicable'}:
                    yield fact.source_span.model_dump(mode='json', by_alias=True)
    packet = frozen.get('providerLiterals')
    if packet and result.literal_review is not None:
        for review, claim in zip(result.literal_review.claims, packet['claims'], strict=True):
            if review.verdict == 'pass' and claim['role'] == 'literal_visible_text':
                yield claim['sourceSpan']
        for review, fact in zip(result.literal_review.facts, packet['context']['facts'], strict=True):
            if review.verdict in {'pass', 'not_applicable'} and fact['role'] == 'literal_visible_text':
                yield fact['sourceSpan']


def prepare_provider_literals(session, request):
    from .content_language_classifier import original_sources, string_leaves
    from .content_language_contract import CHECK_INPUT
    from .content_language_persistence import check_rows, verified_check
    sources = dict(string_leaves(original_sources(request, visible_literals=False)))
    facts, retained = {}, {}
    for row in check_rows(session, request.project_id):
        checking, data, _attempt, _profile, receipt, result = verified_check(row)
        if result is None or result.verdict != 'pass' or receipt is None:
            continue
        frozen = checking.input_artifacts[CHECK_INPUT]
        filename = {'outline': 'outline.json', 'characters': 'cast.json', 'art': 'art.json', 'script': 'script.json'}.get(frozen['stage'])
        if filename is None or digest(request.input_artifacts.get(filename)) != frozen['candidateHash']:
            continue
        old_sources = dict(string_leaves(frozen['sources']))
        for old_span in passed_visible_sources(frozen, result):
            full = old_sources[old_span['path']]
            if old_span['path'] in sources and sources[old_span['path']] != full:
                continue  # An explicitly changed current owner cannot borrow old source intent.
            paths = [path for path, text in sources.items() if text == full]
            if paths:
                path = paths[0]
            else:
                key = text_hash(full)
                retained[key] = {'text': full, 'sha256': key}
                path = '$.retainedVisibleSources.' + key
            identity = {'role':'literal_visible_text','sourceSpan':old_span | {'path':path}, 'sourceFieldHash':text_hash(full)}
            identifier = digest(identity)
            witness = {'checkJobId':checking.job_id, 'bindingHash':frozen['bindingHash'],
                'candidateHash':frozen['candidateHash'], 'resultHash':digest(data['result']), 'receiptHash':receipt.evidence_hash}
            fact = facts.setdefault(identifier, identity | {'id':identifier,'evidence':[]})
            if witness not in fact['evidence']:
                fact['evidence'].append(witness)
    for fact in facts.values():
        fact['evidence'].sort(key=digest)
    freeze_provider_context(request, facts=[facts[key] for key in sorted(facts)], retained_sources=retained)
    return request.input_artifacts[LITERAL_INPUT]
