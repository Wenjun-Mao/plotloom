"""Exact native two-occurrence regression; all execution receipts here are synthetic."""
from copy import deepcopy

import pytest

from plotloom.content_language_contract import (
    CHECK_INPUT,
    ContentLanguageResult,
    bind_language_result,
    render_language_report,
)
from plotloom.content_language_rejection import _language_issues
from plotloom.provider_literal_discovery import DISCOVERY
from plotloom.provider_literal_preparation import (
    passed_visible_sources,
    prepare_provider_literals,
)
from plotloom.provider_literals import freeze_provider_context, text_hash
from tests.content_language_fixtures import (
    completed_check,
    original_request,
)
from tests.provider_literal_discovery_fixtures import discover
from tests.test_content_language_persistence import (
    check_environment as _check_environment,
)
from tests.test_visible_literal_discovery import prepared

check_environment = _check_environment
PATH = "$.inputs.cast_json.characters[0].reviewNotes.performanceGuidance"
BAD_ID = "652aafa1ea45506265ad3eb91288d5451b85ab0e97da09a5935713e5f60196c6"
FIELD_HASH = "4ec2c6f579fef819df83d95a63369bfbf413d024e9e455cc3a82deab2fddf1d1"
PERFORMANCE_GUIDANCE = "Keep the same performer, appearance, wardrobe and voice across the opening and both alternatives. In the opening, rest one hand beside the cup and speak exactly Save this place. once, without an added gesture. Keep the cup’s single visible character exactly 安, legible in the opening and unchanged in both endings; it is never spoken or translated. In the table ending, withdraw the hand without moving the cup. In the window ending, move that same cup to the window within the same room with continuous hand contact and physically continuous motion. Do not imply an emotional transformation or add speech. The exact labels Keep the cup and Move it to the window belong only to the paused player interface. Each filmed section uses one continuous static-camera shot of about eight seconds, natural light, quiet ambience and 16:9 live action. Each route plays the shared opening and only its selected ending, about sixteen seconds total and at most twenty seconds, with no later join. The interface choice has no footage or assigned duration. Add no narrator, other characters, music, subtitles, signs or other visible words. The isolated character portraits and reference sheet omit the cup; its lettering belongs to the filmed prop, not to clothing or the voice design."
AUTHOR_SOURCE = "Original disposable bilingual QA story. Nora is an adult caretaker alone in a quiet reading room with one plain yellow cup on the table. The name Nora is intentional source wording. Shared opening: she rests a hand beside the cup and says exactly once, “Save this place.” Keep the physical action simple; no other characters, secrets, narrator or added speech. Playback then pauses for one choice with the exact button labels “Keep the cup” and “Move it to the window”. These words belong only to the player interface, never spoken or rendered inside the video. First ending: she withdraws her hand and the cup stays on the table. Second ending: she moves the cup to the window in the same room. Three filmed sections of about eight seconds each; every route about sixteen seconds with a hard maximum of twenty seconds. The choice is route-only with no fabricated footage duration. One continuous static-camera shot per section, natural light and quiet room ambience. No subtitles, signs or music. Exact visible source text: the cup has the single Chinese character “安” on its front, an intentional nonspoken foreign quotation that must remain exactly “安”, never translated. It is legible in the opening and remains on this same cup in later shots. Add no other visible words."


def _discovered(checking, reply, *, bad_intent='reject', missing_lettering=False, misuse=False):
    prefix_paths = [f'$.episodes[{ep}].segments[0].cuts[0].frame' for ep in range(3)] if misuse else []
    discover(checking, reply, 'Keep the cup', source_path=PATH, source_start=210,
             intent=bad_intent, relevance='uncertain' if bad_intent == 'uncertain' else 'required' if misuse else 'not_relevant',
             presence='uncertain' if bad_intent == 'uncertain' else 'reject' if misuse else 'not_applicable',
             candidate_paths=prefix_paths)
    discover(checking, reply, 'Keep the cup', source_path=PATH, source_start=624,
             relevance='not_relevant', presence='not_applicable')
    discover(checking, reply, 'Move it to the window', source_path=PATH, source_start=641,
             relevance='not_relevant', presence='not_applicable')
    paths = [] if missing_lettering else [path for ep in range(3) for path in (
        f'$.episodes[{ep}].segments[0].cuts[0].frame', f'$.episodes[{ep}].segments[0].h3Prompt')]
    discover(checking, reply, '安', source_path=PATH, source_start=258,
             candidate_paths=paths, presence='reject' if missing_lettering else 'pass')
    return reply


def _prospective(check_environment, *, missing_lettering=False, misuse=False):
    _storage, store, registry = check_environment
    assert text_hash(PERFORMANCE_GUIDANCE) == FIELD_HASH
    assert PERFORMANCE_GUIDANCE[210:222] == PERFORMANCE_GUIDANCE[624:636] == 'Keep the cup'
    cast = {'characters': [{'reviewNotes': {'performanceGuidance': PERFORMANCE_GUIDANCE}}]}
    original = original_request('art', locale='en-US', project_id=store.manifest.project_id)
    original.source = {'text': AUTHOR_SOURCE}
    original.input_artifacts['cast.json'] = cast
    freeze_provider_context(original)
    art = {'lang': 'en', 'props': [{'image': {'prompt': 'A yellow cup bears exactly 安.'}}]}
    previous, positive = prepared(store, registry, original, art)
    for text, start in [('Keep the cup', 210), ('Keep the cup', 624), ('Move it to the window', 641)]:
        discover(previous, positive, text, source_path=PATH, source_start=start,
                 relevance='not_relevant', presence='not_applicable')
    discover(previous, positive, '安', source_path=PATH, source_start=258,
             candidate_paths=['$.props[0].image.prompt'])
    # A receipt proves this synthetic wrong judgment happened; it does not make it true.
    completed_check(store, previous.job_id, positive)
    before = deepcopy(store.repository.content_language.load(original.project_id, previous.job_id)[1])
    request = original_request('storyboard', locale='en-US', project_id=original.project_id)
    request.source = deepcopy(original.source)
    request.input_artifacts.update({'cast.json': cast, 'art.json': art})
    with store.repository._read() as session:
        context = prepare_provider_literals(session, request)
    assert len(context['facts']) == 4
    bad = next(item for item in context['facts'] if item['id'] == BAD_ID)
    assert bad['sourceSpan'] == {'path': PATH, 'start': 210, 'end': 222, 'text': 'Keep the cup'}
    assert bad['sourceFieldHash'] == FIELD_HASH and bad['evidence'][0]['checkJobId'] == previous.job_id
    lettering = '' if missing_lettering else '安'
    unauthorized = ' A sign visibly reads Keep the cup.' if misuse else ''
    candidate = {'lang': 'en', 'episodes': [{'ep': ep + 1, 'segments': [{
        'h3Prompt': f'A yellow cup bears {lettering}. No player interface is filmed.',
        'cuts': [{'composition': 'Nora rests beside the yellow cup.',
                  'frame': f'A yellow cup bears {lettering}.{unauthorized}'}],
    }]} for ep in range(3)]}
    checking, reply = prepared(store, registry, request, candidate)
    _discovered(checking, reply, missing_lettering=missing_lettering, misuse=misuse)
    return store, previous, before, checking, reply


def test_wrong_prior_interpretation_is_explicit_without_rejecting_valid_content(check_environment):
    store, previous, before, checking, reply = _prospective(check_environment)
    result = bind_language_result(checking, reply)
    assert result.verdict == 'pass' and _language_issues(checking, result) == ()
    frozen = checking.input_artifacts[CHECK_INPUT]
    assert frozen['sources']['inputs']['cast_json']['characters'][0]['reviewNotes']['performanceGuidance'] == PERFORMANCE_GUIDANCE
    assert frozen['sources']['source']['text'] == AUTHOR_SOURCE
    review = next(item for item in result.literal_review.facts if item.fact_id == BAD_ID)
    assert (review.intent, review.relevance, review.verdict) == ('reject', 'not_relevant', 'not_applicable')
    source = next(row for row in result.visible_literal_discovery.sources if row.path == PATH)
    assert [(fact.source_span.start, fact.intent) for fact in source.facts] == [
        (210, 'reject'), (624, 'pass'), (641, 'pass'), (258, 'pass')]
    assert len(next(fact for fact in source.facts if fact.source_span.text == '安').candidate_occurrences) == 6
    assert store.repository.content_language.load(checking.project_id, previous.job_id)[1] == before
    # The prior negative judgment is retained in the exact checked result/report,
    # while preparation must never relabel it as positive authority.
    assert not any(span['path'] == PATH and span['start'] == 210
                   for span in passed_visible_sources(frozen, result))
    html = render_language_report(checking, reply).decode()
    assert 'Earlier interpretation rejected' in html and '210:222' in html
    completed_check(store, checking.job_id, reply)
    assert store.repository.content_language.load(checking.project_id, previous.job_id)[1] == before


@pytest.mark.parametrize('mutation', ['omit_discovery', 'move_span', 'omit_intent', 'erase_all', 'false_preservation'])
def test_prior_interpretation_cannot_disappear_or_move_to_identical_words(check_environment, mutation):
    _store, _previous, _before, checking, reply = _prospective(check_environment)
    source = next(row for row in reply[DISCOVERY]['sources'] if row['path'] == PATH)
    bad = next(fact for fact in source['facts'] if fact['sourceSpan']['start'] == 210)
    if mutation == 'omit_discovery':
        source['facts'].remove(bad)
    elif mutation == 'move_span':
        bad['sourceSpan'].update(start=624, end=636)
    elif mutation == 'omit_intent':
        next(fact for fact in reply['literalReview']['facts'] if fact['factId'] == BAD_ID).pop('intent')
    elif mutation == 'erase_all':
        source.update(decision='no_visible_literal', facts=[])
    else:
        bad.update(presence='pass', relevance='required')
    with pytest.raises(ValueError):
        bind_language_result(checking, reply)


def test_uncertain_prior_interpretation_stays_uncertain_without_false_content_rejection(check_environment):
    _store, _previous, _before, checking, reply = _prospective(check_environment)
    _discovered(checking, reply, bad_intent='uncertain')
    result = bind_language_result(checking, reply)
    assert result.verdict == 'uncertain' and _language_issues(checking, result) == ()
    assert 'Source intent uncertain' in render_language_report(checking, reply).decode()
    reply['verdict'] = 'pass'
    with pytest.raises(ValueError):
        bind_language_result(checking, reply)


@pytest.mark.parametrize('missing_lettering,misuse', [(True, False), (False, True)])
def test_real_required_lettering_omission_or_unauthorized_occurrence_still_rejects(
        check_environment, missing_lettering, misuse):
    _store, _previous, _before, checking, reply = _prospective(
        check_environment, missing_lettering=missing_lettering, misuse=misuse)
    result = bind_language_result(checking, reply)
    assert result.verdict == 'reject'
    assert [issue.code for issue in _language_issues(checking, result)] == ['candidate_content_invalid']


def test_frozen_schema_requires_current_intent_and_the_exact_prior_occurrence(check_environment):
    _store, _previous, _before, checking, _reply = _prospective(check_environment)
    schema = checking.input_artifacts['content-language-schema.json']
    assert 'contract' in schema['required']
    assert schema['properties']['contract']['const'] == 'plotloom.content-language-check.v2'
    assert 'exact positive current source-intent discovery' in schema['$defs']['LanguageException']['description']
    definition = schema['$defs']['LiteralFactReview']
    assert 'intent' in definition['required']
    assert definition['properties']['intent']['enum'] == ['pass', 'reject', 'uncertain']
    rules = [rule for rule in schema['allOf'] if rule['if']['properties']['literalReview']
             ['properties']['facts']['contains']['properties']['factId']['const'] == BAD_ID]
    assert len(rules) == 3
    for rule in rules:
        exact = rule['then']['properties'][DISCOVERY]['properties']['sources']['contains']['properties']['facts']['contains']
        assert exact['properties']['sourceSpan']['const'] == {
            'path': PATH, 'start': 210, 'end': 222, 'text': 'Keep the cup'}
        assert exact['properties']['sourceFieldHash']['const'] == FIELD_HASH
        intent = rule['if']['properties']['literalReview']['properties']['facts']['contains']['properties']['intent']['const']
        assert exact['properties']['intent']['const'] == intent
    condition = schema['$defs']['DiscoveredVisibleFact']['allOf'][-2]
    assert 'pass' not in condition['then']['properties']['presence']['enum']


def test_missing_marker_keeps_historical_meaning_and_cannot_acquire_current_authority(check_environment):
    historical = ContentLanguageResult.model_validate({
        'bindingHash': 'a' * 64, 'verdict': 'pass', 'coverage': [], 'findings': []})
    assert historical.contract == 'plotloom.content-language-check.v1'
    _store, _previous, _before, checking, reply = _prospective(check_environment)
    reply.pop('contract')
    with pytest.raises(ValueError):
        bind_language_result(checking, reply)


def test_partial_exception_cannot_launder_a_rejected_interpretation(check_environment):
    _store, _previous, _before, checking, _reply = _prospective(check_environment)
    # Equal bytes in a fresh envelope isolate missing intent authority from a
    # simple substring/text mismatch.
    candidate = deepcopy(checking.input_artifacts[CHECK_INPUT]['candidate'])
    candidate['episodes'][0]['segments'][0]['cuts'][0]['composition'] = 'Keep the yellow cup unchanged.'
    from tests.content_language_fixtures import checking_request, result_for
    original = checking.input_artifacts[CHECK_INPUT]['originalRequest']
    from plotloom.creative_handoff_contracts import CreativeHandoffRequest
    request = CreativeHandoffRequest.model_validate(original)
    current = checking_request(request, candidate)
    reply = _discovered(current, result_for(current))
    coverage = next(row for row in reply['coverage'] if row['path'] == '$.episodes[0].segments[0].cuts[0].composition')
    coverage['exceptions'] = [{'kind': 'literal_visible_text',
        'candidateSpan': {'path': coverage['path'], 'start': 0, 'end': 4, 'text': 'Keep'},
        'sourceSpan': {'path': PATH, 'start': 210, 'end': 214, 'text': 'Keep'}}]
    with pytest.raises(ValueError, match='exact positive current source-intent'):
        bind_language_result(current, reply)
    parsed = ContentLanguageResult.model_validate(reply)
    assert not any(span['path'] == PATH and span['start'] == 210
                   for span in passed_visible_sources(current.input_artifacts[CHECK_INPUT], parsed))


def test_genuine_lettering_inside_a_rejected_larger_interpretation_keeps_its_exact_authority():
    from tests.content_language_fixtures import checking_request, result_for
    original = original_request('branches', locale='en-US')
    original.source = {'text': 'Keep the cup’s single visible character exactly 安.'}
    candidate = {'lang': 'en', 'nodes': [{'id': 'start', 'title': 'A cup bears 安.'}]}
    checking = checking_request(original, candidate)
    reply = result_for(checking)
    source = original.source['text']
    discover(checking, reply, source, intent='reject', relevance='not_relevant', presence='not_applicable')
    discover(checking, reply, '安', candidate_paths=['$.nodes[0].title'])
    row = next(row for row in reply['coverage'] if row['path'] == '$.nodes[0].title')
    offset = candidate['nodes'][0]['title'].index('安')
    row['exceptions'] = [{'kind': 'literal_visible_text',
        'candidateSpan': {'path': row['path'], 'start': offset, 'end': offset + 1, 'text': '安'},
        'sourceSpan': {'path': '$.source.text', 'start': source.index('安'), 'end': source.index('安') + 1, 'text': '安'}}]
    assert bind_language_result(checking, reply).verdict == 'pass'
