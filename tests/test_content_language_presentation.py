"""Synthetic semantic judgments over real presentation binding/projection."""
from copy import deepcopy

import pytest

from plotloom.content_language_classifier import string_leaves
from plotloom.content_language_contract import (
    CHECK_INPUT,
    bind_language_result,
    identity,
    language_check_instructions,
    language_result_schema,
)
from plotloom.content_language_presentation import (
    PRESENTATION_VIEW,
    presentation_witnesses,
)
from plotloom.production_presentation import (
    PresentationSource,
    PresentationUpdate,
    ProductionPresentation,
    bind_presentation_spans,
    project_presentation,
    stable_hash,
)
from plotloom.provider_literal_discovery import DISCOVERY
from plotloom.provider_literals import text_hash
from tests.content_language_fixtures import (
    checking_request,
    original_request,
    result_for,
)


def prepared(locale='en-US'):
    original = original_request('bridge-presentation', locale=locale)
    text = 'The cup bears 安.' if locale == 'en-US' else '杯上只印着Mira。'
    literal = '安' if locale == 'en-US' else 'Mira'
    original.source = {'text': text}
    sources = [PresentationSource(id=f'{kind}:{target}', kind=kind, target_id=target,
        coordinates={'stage': stage, 'field': field}, source_hash=stable_hash({field: text}), source_text=text)
        for kind, target, stage, field in [('action', 'B01', 'F4', 'action'),
                                          ('composition', 'SH01', 'F5', 'composition')]]
    package = ProductionPresentation(sources=sources,
        runtime_choice={'choices': [{'prompt': 'Where?', 'outcomes': [{'label': 'Here'}, {'label': 'There'}]}]},
        frozen_evidence={}, source_hash=stable_hash({}))
    original.input_artifacts['presentation-source.json'] = package.model_dump(mode='json', by_alias=True)
    start = text.index(literal)
    physical = 'Keep the same cup.' if locale == 'en-US' else '保留同一只杯子。'
    candidate = {'lang': 'en' if locale == 'en-US' else 'zh', 'entries': [
        {'id': source.id, 'spans': [
            {'start': 0, 'end': start, 'role': 'physical', 'rendering': physical, 'reason': physical},
            {'start': start, 'end': start + len(literal), 'role': 'visible_text', 'rendering': '', 'reason': physical},
            {'start': start + len(literal), 'end': len(text), 'role': 'physical', 'rendering': physical, 'reason': physical},
        ]} for source in sources]}
    checking = checking_request(original, candidate)
    return original, candidate, checking, reply_for(checking)


def fact_for(witness, path):
    return {'role': 'literal_visible_text', 'sourceSpan': witness['sourceSpan'],
        'sourceFieldHash': witness['sourceFieldHash'], 'intent': 'pass', 'relevance': 'required',
        'presence': 'pass', 'candidateOccurrences': [{'span': {'path': path, 'start': 0,
            'end': len(witness['text']), 'text': witness['text']}, 'fieldHash': text_hash(witness['text'])}],
        'explanation': 'Explicit synthetic source intent; not a native judgment.'}


def reply_for(checking):
    return result_for(checking)


@pytest.mark.parametrize('locale', ['en-US', 'zh-CN'])
def test_source_slice_witness_matches_canonical_visible_output(locale):
    original, candidate, checking, reply = prepared(locale)
    frozen = checking.input_artifacts[CHECK_INPUT]
    result = bind_language_result(checking, reply)
    assert result.verdict == 'pass'
    assert frozen['candidateHash'] == identity(candidate)
    assert len(frozen['inventory']) == len(list(string_leaves(candidate)))
    package = ProductionPresentation.model_validate(original.input_artifacts['presentation-source.json'])
    sources = bind_presentation_spans(package, [PresentationUpdate.model_validate(entry) for entry in candidate['entries']])
    # Explicit test-owned approval for exercising the existing pure projector.
    reviewed = package.model_copy(update={'sources': sources, 'reviewed': True})
    payload = {'sceneBeats': {'beats': [{'id': 'B01'}]}, 'storyboard': {
        'shots': [{'id': 'SH01'}], 'shotBeatLinks': [{'shotId': 'SH01', 'beatId': 'B01'}]}}
    actual = project_presentation(payload, reviewed)['storyboard']['shots'][0]['visibleTexts']
    expected = [{'text': w['text'], 'sourceCoordinates': w['sourceCoordinates'],
        'sourceContentHash': w['sourceContentHash']} for w in frozen[PRESENTATION_VIEW]]
    assert actual == expected
    assert all(span['rendering'] == '' for entry in candidate['entries'] for span in entry['spans'] if span['role'] == 'visible_text')
    schema = language_result_schema(frozen)
    paths = schema['$defs']['VisibleOccurrence']['properties']['span']['properties']['path']['enum']
    assert all(path in paths for path in presentation_witnesses(frozen))
    assert 'nonphysical rendering must stay empty' in language_check_instructions(frozen)


@pytest.mark.parametrize('field', ['entryId', 'entryIndex', 'targetId', 'spanIndex', 'sourceFieldHash',
                                   'sourceContentHash', 'sourceCoordinates', 'sourceSpan', 'text'])
def test_frozen_projection_cannot_change_any_binding(field):
    _original, _candidate, checking, _reply = prepared()
    frozen = deepcopy(checking.input_artifacts[CHECK_INPUT])
    frozen[PRESENTATION_VIEW][0][field] = 'tampered'
    with pytest.raises(ValueError, match='exact source-bound'):
        presentation_witnesses(frozen)


@pytest.mark.parametrize('mutation', ['other_assignment', 'wrong_offset', 'wrong_hash', 'missing_fact', 'missing_source', 'prose_copy'])
def test_presence_cannot_borrow_or_invent_output(mutation):
    _original, _candidate, checking, reply = prepared()
    rows = [row for row in reply[DISCOVERY]['sources'] if row['facts']]
    fact = rows[0]['facts'][0]
    occurrence = fact['candidateOccurrences'][0]
    if mutation == 'other_assignment':
        occurrence['span']['path'] = '$.presentationVisibleTexts[1].text'
    elif mutation == 'wrong_offset':
        occurrence['span']['start'] = 1
    elif mutation == 'wrong_hash':
        occurrence['fieldHash'] = '0' * 64
    elif mutation == 'missing_fact':
        rows[0].update(decision='no_visible_literal', facts=[])
    elif mutation == 'missing_source':
        reply[DISCOVERY]['sources'].remove(rows[0])
    else:
        # Actual raw prose with an exact character still is not projected output.
        occurrence['span'] = {'path': '$.entries[0].spans[1].rendering', 'start': 0, 'end': 1, 'text': '安'}
        occurrence['fieldHash'] = text_hash('')
    with pytest.raises(ValueError):
        bind_language_result(checking, reply)


def test_reassigned_visible_span_supplies_no_witness_and_cannot_borrow_another():
    original, candidate, checking, _reply = prepared()
    removed = checking.input_artifacts[CHECK_INPUT][PRESENTATION_VIEW][0]
    candidate['entries'][0]['spans'][1]['role'] = 'review_only'
    current = checking_request(original, candidate)
    frozen = current.input_artifacts[CHECK_INPUT]
    assert len(frozen[PRESENTATION_VIEW]) == 1
    reply = reply_for(current)
    row = next(row for row in reply[DISCOVERY]['sources'] if row['path'] == removed['sourceSpan']['path'])
    row.update(decision='visible_literal', facts=[fact_for(removed, '$.presentationVisibleTexts[0].text')])
    with pytest.raises(ValueError, match='own exact projected occurrence'):
        bind_language_result(current, reply)


@pytest.mark.parametrize('value', ['Peace', '安'])
def test_nonphysical_rendering_remains_empty(value):
    original, candidate, _checking, _reply = prepared()
    candidate['entries'][0]['spans'][1]['rendering'] = value
    with pytest.raises(ValueError):
        checking_request(original, candidate)


@pytest.mark.parametrize('intent,expected', [('reject', 'reject'), ('uncertain', 'uncertain')])
def test_projected_output_is_not_positive_author_intent(intent, expected):
    _original, _candidate, checking, reply = prepared()
    fact = next(row['facts'][0] for row in reply[DISCOVERY]['sources'] if row['facts'])
    fact.update(intent=intent, presence=expected, relevance='uncertain' if intent == 'uncertain' else 'required')
    if intent == 'reject':
        next(row for row in reply[DISCOVERY]['sources'] if fact in row['facts'])['decision'] = 'no_visible_literal'
    else:
        next(row for row in reply[DISCOVERY]['sources'] if fact in row['facts'])['decision'] = 'uncertain'
    reply['verdict'] = expected
    assert bind_language_result(checking, reply).verdict == expected


def test_contextual_source_uncertainty_still_blocks():
    _original, _candidate, checking, reply = prepared()
    witness = checking.input_artifacts[CHECK_INPUT][PRESENTATION_VIEW][0]
    fact = fact_for(witness, '$.presentationVisibleTexts[0].text')
    fact['sourceSpan'] = fact['sourceSpan'] | {'path': '$.source.text'}
    fact.update(intent='uncertain', relevance='uncertain', presence='uncertain')
    row = next(row for row in reply[DISCOVERY]['sources'] if row['path'] == '$.source.text')
    row.update(decision='uncertain', facts=[fact])
    reply['verdict'] = 'uncertain'
    assert bind_language_result(checking, reply).verdict == 'uncertain'


def test_physical_edits_invalidate_binding_without_changing_lettering():
    original, candidate, checking, _reply = prepared()
    candidate['entries'][0]['spans'][0]['rendering'] = 'Keep the cup upright.'
    changed = checking_request(original, candidate)
    assert changed.source['bindingHash'] != checking.source['bindingHash']
    assert changed.input_artifacts[CHECK_INPUT][PRESENTATION_VIEW] == checking.input_artifacts[CHECK_INPUT][PRESENTATION_VIEW]


def test_exact_lettering_in_a_reason_cannot_certify_visible_output():
    original, candidate, _checking, _reply = prepared()
    reason = 'Exact marking 安.'
    candidate['entries'][0]['spans'][1]['reason'] = reason
    checking = checking_request(original, candidate)
    reply = reply_for(checking)
    fact = next(row['facts'][0] for row in reply[DISCOVERY]['sources'] if row['facts'])
    fact['candidateOccurrences'] = [{'span': {'path': '$.entries[0].spans[1].reason',
        'start': reason.index('安'), 'end': reason.index('安') + 1, 'text': '安'}, 'fieldHash': text_hash(reason)}]
    with pytest.raises(ValueError, match='exact projected occurrence'):
        bind_language_result(checking, reply)
