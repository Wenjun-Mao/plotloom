"""Explicit model-judgment fixtures; never heuristic or live intent evidence."""
from plotloom.content_language_classifier import string_leaves
from plotloom.content_language_contract import CHECK_INPUT
from plotloom.provider_literal_discovery import DISCOVERY, fact_matches
from plotloom.provider_literals import text_hash


def discover(checking, result, text, *, source_path='$.source.text', candidate_paths=(),
             intent='pass', relevance='required', presence=None):
    frozen = checking.input_artifacts[CHECK_INPUT]
    sources = dict(string_leaves(frozen['sources']))
    source = sources[source_path]; start = source.index(text)
    span = {'path':source_path,'start':start,'end':start+len(text),'text':text}
    leaves = dict(string_leaves(frozen['candidate']))
    occurrences=[]
    for path in candidate_paths:
        value=leaves[path];offset=value.index(text)
        occurrences.append({'span':{'path':path,'start':offset,'end':offset+len(text),'text':text},'fieldHash':text_hash(value)})
    fact={'role':'literal_visible_text','sourceSpan':span,'sourceFieldHash':text_hash(source),
        'intent':intent,'relevance':relevance,'presence':presence or ('pass' if occurrences else 'reject'),
        'candidateOccurrences':occurrences,'explanation':'Explicit synthetic source-intent/completeness judgment.'}
    row=next(row for row in result[DISCOVERY]['sources'] if row['path']==source_path)
    row['decision']='visible_literal'
    row['facts']=[old for old in row['facts'] if old['sourceSpan']!=span]+[fact]
    literal=frozen.get('providerLiterals')
    if literal:
        for review,known in zip(result['literalReview']['facts'],literal['context']['facts'],strict=True):
            if fact_matches(fact,known):review.update(relevance=relevance,verdict=fact['presence'])
    refresh_verdict(result)
    return fact


def refresh_verdict(result):
    verdicts={item['verdict'] for item in result['coverage']}
    verdicts|={item['verdict'] for key in ('claims','facts') for item in result.get('literalReview',{}).get(key,[])}
    verdicts|={value for row in result[DISCOVERY]['sources'] for fact in row['facts'] for value in (fact['intent'],fact['presence'])}
    if any(row['decision']=='uncertain' for row in result[DISCOVERY]['sources']):verdicts.add('uncertain')
    result['verdict']='reject' if 'reject' in verdicts else 'uncertain' if 'uncertain' in verdicts else 'pass'
