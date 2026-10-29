"""Receipt-backed fact reuse uses synthetic native proofs, never live acceptance."""
from copy import deepcopy

import pytest

from plotloom.content_language_contract import CHECK_INPUT, bind_language_result, identity
from plotloom.content_language_service import ContentLanguageService
from plotloom.persistence.project.creative_execution_pins import freeze_execution_pin
from plotloom.provider_literal_preparation import prepare_provider_literals
from plotloom.provider_literals import LITERAL_INPUT
from tests.content_language_fixtures import original_request, result_for, completed_check, checking_request
from tests.test_content_language_persistence import check_environment as _check_environment

check_environment = _check_environment
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION


def test_only_exact_checked_upstream_artifact_reuses_receipt_bound_visible_fact(check_environment):
    _storage,store,registry=check_environment
    original=original_request('outline',project_id=store.manifest.project_id)
    original.source['text']='杯上写着安。'
    candidate={'lang':'zh','adaptation':{'core':'杯上保留安字。'}}
    with store.repository._write() as session:freeze_execution_pin(session,original,PIN)
    service=ContentLanguageService(registry)
    job=service.prepare(store,original,candidate,code_revision=SOURCE_REVISION)
    checking,_=store.repository.content_language.load(original.project_id,job)
    result=result_for(checking)
    next(row for row in result['coverage'] if row['path']=='$.adaptation.core')['exceptions']=[{
        'kind':'literal_visible_text',
        'candidateSpan':{'path':'$.adaptation.core','start':4,'end':5,'text':'安'},
        'sourceSpan':{'path':'$.source.text','start':4,'end':5,'text':'安'}}]
    from tests.provider_literal_discovery_fixtures import discover
    discover(checking, result, '安', candidate_paths=['$.adaptation.core'])
    _done,receipt=completed_check(store,job,result)
    downstream=original_request('art',project_id=original.project_id)
    downstream.source=deepcopy(original.source);downstream.input_artifacts['outline.json']=candidate
    with store.repository._read() as session:
        packet=prepare_provider_literals(session,downstream)
        assert len(packet['facts'])==1
        fact=packet['facts'][0]
        assert fact['sourceSpan']=={'path':'$.source.text','start':4,'end':5,'text':'安'}
        assert fact['evidence'][0]['checkJobId']==job and fact['evidence'][0]['receiptHash']==receipt.evidence_hash
        assert fact['evidence'][0]['bindingHash']==checking.source['bindingHash']
        # A similar source or a different upstream candidate cannot borrow proof.
        downstream.input_artifacts['outline.json']={'lang':'zh','adaptation':{'core':'杯上另写安字。'}}
        assert prepare_provider_literals(session,downstream)['facts']==[]
        downstream.input_artifacts['outline.json']=candidate
        downstream.source['text']='新来源：杯上写着安。'
        assert prepare_provider_literals(session,downstream)['facts']==[]


def test_v4_augmented_sources_remain_original_read_identity(tmp_path):
    from tests.provider_literal_fixtures import art_literal_case
    request,candidate=art_literal_case(tmp_path)
    request.input_artifacts.pop(LITERAL_INPUT);candidate.pop('providerLiterals')
    checking=checking_request(request,candidate)
    frozen=checking.input_artifacts[CHECK_INPUT]
    assert frozen['sources'].get('authorDirection')
    frozen['classifierVersion']='plotloom.content-language-classifier.v4'
    frozen['bindingHash']=identity({key:value for key,value in frozen.items() if key!='bindingHash'})
    checking.source['bindingHash']=frozen['bindingHash']
    result=result_for(checking)
    assert bind_language_result(checking,result,require_current=False).verdict=='pass'
    with pytest.raises(ValueError):bind_language_result(checking,result)
    original_hash=frozen['bindingHash']
    frozen['sources'].pop('authorDirection')
    frozen['bindingHash']=identity({key:value for key,value in frozen.items() if key!='bindingHash'})
    result['bindingHash']=checking.source['bindingHash']=frozen['bindingHash']
    assert frozen['bindingHash']!=original_hash
    with pytest.raises(ValueError):bind_language_result(checking,result,require_current=False)
