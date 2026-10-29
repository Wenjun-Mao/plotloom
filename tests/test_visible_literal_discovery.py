"""Small API/SQLite/exchange proof of independent discovery; synthetic native host."""
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.content_language_contract import CHECK_INPUT, bind_language_result, language_result_schema
from plotloom.content_language_service import ContentLanguageService
from plotloom.persistence.project.creative_execution_pins import freeze_execution_pin
from plotloom.provider_literal_discovery import DISCOVERY
from plotloom.provider_literal_preparation import prepare_provider_literals
from plotloom.provider_literals import digest
from tests.content_language_fixtures import original_request, result_for, completed_check, checking_request
from tests.provider_literal_discovery_fixtures import discover, refresh_verdict
from tests.test_content_language_persistence import check_environment as _check_environment
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION

check_environment = _check_environment


def prepared(store, registry, original, candidate):
    from plotloom.persistence.schema import ProjectRow
    with store.repository._write() as session:
        row=session.get(ProjectRow,original.project_id)
        row.brief=dict(row.brief,language=original.input_artifacts['language-contract.json']['contentLocale'])
        freeze_execution_pin(session,original,PIN)
    job=ContentLanguageService(registry).prepare(store,original,candidate,code_revision=SOURCE_REVISION)
    checking,_=store.repository.content_language.load(original.project_id,job)
    return checking,result_for(checking)


@pytest.mark.parametrize('text,locale',[('安','zh-CN'),('Mira','en-US')])
def test_same_language_source_discovery_flows_through_actual_preparation_without_language_exception(check_environment,text,locale):
    _storage,store,registry=check_environment
    original=original_request('outline',locale=locale,project_id=store.manifest.project_id)
    original.source={'text':f'The cup must visibly bear the exact nonspoken lettering {text}.'}
    candidate={'lang':'zh' if locale=='zh-CN' else 'en','adaptation':{'core':f'杯子保留{text}字样。' if locale=='zh-CN' else f'The cup bears {text}.'}}
    checking,result=prepared(store,registry,original,candidate)
    assert all(not row['exceptions'] for row in result['coverage'])
    discover(checking,result,text,candidate_paths=['$.adaptation.core'])
    assert bind_language_result(checking,result).verdict=='pass'
    completed_check(store,checking.job_id,result)
    downstream=original_request('art',locale=locale,project_id=original.project_id)
    downstream.source=deepcopy(original.source);downstream.input_artifacts['outline.json']=candidate
    with store.repository._read() as session:context=prepare_provider_literals(session,downstream)
    assert len(context['facts'])==1 and context['facts'][0]['sourceSpan']['text']==text
    evidence=context['facts'][0]['evidence'][0]
    assert evidence['candidateHash']==digest(candidate) and evidence['checkJobId']==checking.job_id


def checked_cast(store,registry):
    original=original_request('characters',locale='en-US',project_id=store.manifest.project_id)
    original.source={'text':'The plain cup must visibly bear the exact nonspoken label Mira.'}
    candidate={'lang':'en','characters':[{'id':'keeper','image':{'prompt':'A plain cup bearing the exact visible label Mira.'}}]}
    # Writer supplied no provider claims or authored-language exceptions.
    from plotloom.provider_literals import freeze_provider_context
    freeze_provider_context(original)
    checking,result=prepared(store,registry,original,candidate)
    assert checking.input_artifacts[CHECK_INPUT]['providerLiterals']['claims']==[]
    assert all(not row['exceptions'] for row in result['coverage'])
    discover(checking,result,'Mira',candidate_paths=['$.characters[0].image.prompt'])
    assert bind_language_result(checking,result).verdict=='pass'
    completed_check(store,checking.job_id,result)
    return original,candidate,checking,result


def downstream_art(store,upstream,candidate):
    request=original_request('art',locale='en-US',project_id=store.manifest.project_id)
    # F5-shaped loss of the original narrative scalar: preserve its exact owned
    # source bytes and receipt proof, not an unverified copied substring.
    request.source={'acceptedCastContentHash':digest(candidate)}
    request.input_artifacts['cast.json']=candidate
    with store.repository._read() as session:context=prepare_provider_literals(session,request)
    assert context['retainedSources'] and len(context['facts'])==1
    fact=context['facts'][0]
    assert fact['sourceFieldHash']==digest_text(upstream.source['text'])
    return request,context


def digest_text(text):
    from plotloom.provider_literals import text_hash
    return text_hash(text)


def test_provider_only_discovery_survives_source_rebasing_and_omission_cannot_pass(check_environment):
    _storage,store,registry=check_environment
    upstream,candidate,checked,result=checked_cast(store,registry)
    request,context=downstream_art(store,upstream,candidate)
    assert context['facts'][0]['evidence'][0]['resultHash']==digest(result)
    assert context['facts'][0]['evidence'][0]['checkJobId']==checked.job_id
    art={'lang':'en','props':[{'image':{'prompt':'A plain yellow cup with no lettering.'}}]}
    checking,reply=prepared(store,registry,request,art)
    assert bind_language_result(checking,reply).verdict=='reject'
    assert not checking.input_artifacts[CHECK_INPUT]['providerLiterals']['claims']
    from plotloom.content_language_rejection import _language_issues
    assert _language_issues(checking,bind_language_result(checking,reply))[0].code=='candidate_content_invalid'
    for section in ('literalReview',DISCOVERY):
        forged=deepcopy(reply)
        if section=='literalReview':forged[section]['facts']=[]
        else:forged[section]['sources']=[]
        forged['verdict']='pass'
        with pytest.raises(ValueError):bind_language_result(checking,forged)
    forged=deepcopy(reply)
    for row in forged[DISCOVERY]['sources']:row.update(decision='no_visible_literal',facts=[])
    for fact in forged['literalReview']['facts']:fact['verdict']='pass'
    forged['verdict']='pass'
    with pytest.raises(ValueError):bind_language_result(checking,forged)
    # Independent discovery can identify same-language presence with no writer claim.
    art['props'][0]['image']['prompt']='A plain cup bears Mira.'
    current=checking_request(request,art);reply=result_for(current)
    path=context['facts'][0]['sourceSpan']['path']
    discover(current,reply,'Mira',source_path=path,candidate_paths=['$.props[0].image.prompt'])
    assert bind_language_result(current,reply).verdict=='pass'


@pytest.mark.parametrize('mutation',['candidate','result','receipt'])
def test_stale_upstream_candidate_result_or_receipt_never_yields_facts(check_environment,mutation):
    _storage,store,registry=check_environment
    upstream,candidate,checked,_=checked_cast(store,registry)
    request=original_request('art',locale='en-US',project_id=upstream.project_id)
    request.source=deepcopy(upstream.source);request.input_artifacts['cast.json']=deepcopy(candidate)
    if mutation=='candidate':
        request.input_artifacts['cast.json']['characters'][0]['image']['prompt']+=' Changed.'
        with store.repository._read() as session:assert prepare_provider_literals(session,request)['facts']==[]
        return
    from plotloom.persistence.schema import SourceOutlineCandidateRow
    with store.repository._write() as session:
        row=session.get(SourceOutlineCandidateRow,checked.job_id);data=deepcopy(row.outline)
        if mutation=='result':data['result'][DISCOVERY]['sources'][0]['explanation']+=' tampered'
        else:data['receipt']['evidenceHash']='e'*64
        row.outline=data
    with store.repository._read() as session,pytest.raises(ValueError):prepare_provider_literals(session,request)


def test_assembled_current_prompt_schema_and_binder_agree_and_retained_prompt_stays_literal(check_environment):
    _storage,store,registry=check_environment
    original,candidate,checking,result=checked_cast(store,registry)
    frozen=checking.input_artifacts[CHECK_INPUT]
    schema=language_result_schema(frozen)
    assert bind_language_result(checking,result).verdict=='pass'
    assert 'literalReview' in schema['required'] and DISCOVERY in schema['required']
    definition=schema['$defs']['DiscoveredVisibleFact']['properties']['sourceSpan']
    expected=[item['path'] for item in frozen[DISCOVERY]['sources'] if item['length']]
    assert definition['properties']['path']['enum']==expected
    assert 'LiteralSpan' not in schema['$defs']
    paths=schema['$defs']['VisibleOccurrence']['properties']['span']['properties']['path']['enum']
    assert paths==['$.characters[0].image.prompt']
    package=store.creative_handoff_exchange().root/'jobs'/checking.job_id/'package'
    assignment=(package/'COPY_ASSIGNMENT.txt').read_text()
    assert checking.creative_brief in assignment
    assert 'authored_prose AND provider_technical' in assignment
    assert 'other roles and empty strings use not_applicable' not in assignment
    assert 'Provider technical English and stable IDs/enums are exempt' not in assignment
    assert 'zero writer claims or language exceptions' in assignment
    conditional=schema['properties']['coverage']['items']['allOf'][1]
    assert conditional['then']['properties']['verdict']['enum']==['pass','reject','uncertain']
    technical=next(row for row in result['coverage'] if row['role']=='provider_technical')
    assert technical['verdict']=='pass'
    forged=deepcopy(result);next(row for row in forged['coverage'] if row['path']==technical['path'])['verdict']='not_applicable'
    with pytest.raises(ValueError):bind_language_result(checking,forged)
    # Package instructions are bound to the original checking request, not the
    # mutable current prompt factory, including for retained historical checks.
    from plotloom.creative_package_projection import project_creative_package
    retained=checking.model_copy(update={'creative_brief':'Exact original retained checking instructions.'})
    _projection,instructions,*_=project_creative_package(Path('/explicit-synthetic-job'),retained,PIN,
        executor_backend='codex_exec',plotloom_code_revision=SOURCE_REVISION)
    assert instructions.startswith(retained.creative_brief.encode())


@pytest.mark.parametrize('mutation',['role','source_prefix','candidate_prefix','source_hash','invented_intent','voice_channel'])
def test_discovery_cannot_invent_roles_source_coordinates_or_lettering(check_environment,mutation):
    _storage,store,registry=check_environment
    _original,_candidate,checking,result=checked_cast(store,registry)
    fact=next(fact for row in result[DISCOVERY]['sources'] for fact in row['facts'])
    if mutation=='role':fact['role']='spoken_dialogue'
    elif mutation=='source_prefix':fact['sourceSpan']['path']='$.sources.source.text'
    elif mutation=='candidate_prefix':fact['candidateOccurrences'][0]['span']['path']='$.candidate.characters[0].image.prompt'
    elif mutation=='source_hash':fact['sourceFieldHash']='f'*64
    elif mutation=='voice_channel':fact['candidateOccurrences'][0]['span']['path']='$.characters[0].voice.prompt'
    else:
        fact['intent']='reject';refresh_verdict(result)
        assert bind_language_result(checking,result).verdict=='reject'
        return
    with pytest.raises(ValueError):bind_language_result(checking,result)


def test_two_native_receipts_are_one_semantic_requirement_and_one_occurrence(check_environment):
    _storage,store,registry=check_environment
    source={'text':'A cup must visibly bear the exact nonspoken label Mira.'}
    outline=original_request('outline',locale='en-US',project_id=store.manifest.project_id)
    outline.source=source
    outline_candidate={'lang':'en','adaptation':{'core':'A cup bears Mira.'}}
    first,reply=prepared(store,registry,outline,outline_candidate)
    discover(first,reply,'Mira',candidate_paths=['$.adaptation.core']);completed_check(store,first.job_id,reply)
    cast=original_request('characters',locale='en-US',project_id=outline.project_id)
    cast.source=deepcopy(source);cast.input_artifacts['outline.json']=outline_candidate
    with store.repository._read() as session:prepare_provider_literals(session,cast)
    cast_candidate={'lang':'en','characters':[{'id':'keeper','image':{'prompt':'A cup bears Mira.'}}]}
    second,reply=prepared(store,registry,cast,cast_candidate)
    discover(second,reply,'Mira',candidate_paths=['$.characters[0].image.prompt']);completed_check(store,second.job_id,reply)
    art=original_request('art',locale='en-US',project_id=outline.project_id)
    art.source=deepcopy(source);art.input_artifacts.update({'outline.json':outline_candidate,'cast.json':cast_candidate})
    with store.repository._read() as session:context=prepare_provider_literals(session,art)
    assert len(context['facts'])==1
    fact=context['facts'][0]
    assert {proof['checkJobId'] for proof in fact['evidence']}=={first.job_id,second.job_id}
    assert fact['id']==digest({key:fact[key] for key in ('role','sourceSpan','sourceFieldHash')})
    candidate={'lang':'en','props':[{'image':{'prompt':'A cup bears Mira.'}}]}
    from tests.provider_literal_fixtures import claim
    claim(art,candidate,'$.props[0].image.prompt','Mira',fact=fact)
    checking=checking_request(art,candidate)
    assert len(candidate['providerLiterals'])==1
    assert bind_language_result(checking,result_for(checking)).verdict=='pass'


@pytest.mark.parametrize('version',[1,2,3,4,5])
def test_retained_checks_never_gain_discovery_or_new_source_projection(version):
    from plotloom.content_language_contract import identity
    from plotloom.creative_handoff_identity import canonical_json
    original=original_request('outline')
    request=checking_request(original,{'lang':'zh','adaptation':{'core':'杯子留在桌上。'}})
    frozen=request.input_artifacts[CHECK_INPUT]
    frozen.pop(DISCOVERY)
    frozen['classifierVersion']=f'plotloom.content-language-classifier.v{version}'
    frozen['bindingHash']=identity({key:value for key,value in frozen.items() if key!='bindingHash'})
    request.source['bindingHash']=frozen['bindingHash']
    reply=result_for(request);before=canonical_json(reply)
    assert DISCOVERY not in reply and 'literalReview' not in reply
    retained=bind_language_result(request,reply,require_current=False)
    assert canonical_json(retained.model_dump(mode='json',by_alias=True))==before
    with pytest.raises(ValueError):bind_language_result(request,reply)
    reply[DISCOVERY]={'sources':[]}
    with pytest.raises(ValueError,match='retained check'):bind_language_result(request,reply,require_current=False)


def test_fresh_source_omission_is_rejected_with_no_known_facts_or_writer_claims(check_environment):
    _storage,store,registry=check_environment
    original=original_request('art',locale='en-US',project_id=store.manifest.project_id)
    original.source={'text':'The cup must visibly bear the exact nonspoken label Mira.'}
    from plotloom.provider_literals import freeze_provider_context
    freeze_provider_context(original)
    candidate={'lang':'en','props':[{'image':{'prompt':'A plain unmarked yellow cup.'}}]}
    checking,result=prepared(store,registry,original,candidate)
    assert checking.input_artifacts[CHECK_INPUT]['providerLiterals']['context']['facts']==[]
    assert checking.input_artifacts[CHECK_INPUT]['providerLiterals']['claims']==[]
    fact=discover(checking,result,'Mira',presence='reject')
    assert bind_language_result(checking,result).verdict=='reject'
    completed_check(store,checking.job_id,result)
    from plotloom.content_language_persistence import require_language_pass
    from plotloom.exceptions import InvalidTransitionError
    with store.repository._read() as session,pytest.raises(InvalidTransitionError):require_language_pass(session,original,candidate)
    forged=deepcopy(result)
    target=next(item for row in forged[DISCOVERY]['sources'] for item in row['facts'])
    target['presence']='pass';refresh_verdict(forged)
    with pytest.raises(ValueError,match='omission'):bind_language_result(checking,forged)
    assert fact['candidateOccurrences']==[]


def test_arbitrary_source_name_is_not_intended_lettering_by_equality(check_environment):
    _storage,store,registry=check_environment
    original=original_request('art',locale='en-US',project_id=store.manifest.project_id)
    original.source={'text':'Mira is a person in the story. The cup is explicitly unmarked; do not put her name on it.'}
    from plotloom.provider_literals import freeze_provider_context, bind_provider_literals
    from tests.provider_literal_fixtures import claim
    freeze_provider_context(original)
    candidate={'lang':'en','props':[{'image':{'prompt':'A plain cup bearing Mira.'}}]}
    claim(original,candidate,'$.props[0].image.prompt','Mira')
    assert len(bind_provider_literals(original,candidate))==1  # Provenance only.
    checking,reply=prepared(store,registry,original,candidate)
    discover(checking,reply,'Mira',candidate_paths=['$.props[0].image.prompt'],intent='reject',presence='reject')
    reply['literalReview']['claims'][0]['verdict']='reject';refresh_verdict(reply)
    assert bind_language_result(checking,reply).verdict=='reject'
    forged=deepcopy(reply);forged['literalReview']['claims'][0]['verdict']='pass'
    with pytest.raises(ValueError,match='source-intent'):bind_language_result(checking,forged)


def test_retained_literal_fact_review_keeps_its_original_id_mapping_rule():
    from plotloom.provider_literal_review import ProviderLiteralReview, bind_literal_review
    fact={'id':'old-fact','role':'literal_visible_text','sourceSpan':{'path':'$.source.text','start':0,'end':4,'text':'Mira'},'sourceFieldHash':'a'*64}
    claim={key:fact[key] for key in ('role','sourceSpan','sourceFieldHash')} | {'sourceFactId':'another-fact'}
    frozen={'providerLiterals':{'claims':[claim],'context':{'facts':[fact]}}}
    review=ProviderLiteralReview.model_validate({'claims':[{'index':0,'verdict':'pass','explanation':'Retained synthetic review.'}],
        'facts':[{'factId':'old-fact','relevance':'required','verdict':'pass','explanation':'Retained synthetic review.'}]})
    with pytest.raises(ValueError,match='omissions'):bind_literal_review(frozen,review)
    claim['sourceFactId']='old-fact'
    bind_literal_review(frozen,review)
