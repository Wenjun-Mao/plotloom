"""Both passive owners preserve a genuine checker package and native-equivalent proof."""
import json

from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.content_language_contract import CHECK_INPUT, CHECK_OPERATION
from plotloom.content_language_persistence import verified_check
from plotloom.creative_handoff_identity import canonical_json
from plotloom.creative_package_projection import project_creative_package
from plotloom.persistence.project.autopilot_bindings import _retained_checkpoint_validation_plan
from plotloom.project_storage.creative_evidence_inventory import _retained_codex_request_projection
from tests.content_language_fixtures import completed_check, result_for
from tests.test_content_language_persistence import check_environment as _check_environment, prepare

check_environment = _check_environment


def test_actual_storyboard_checker_receipt_uses_checker_plan_through_both_passive_owners(check_environment,monkeypatch):
    _storage,store,registry=check_environment
    _service,original,_candidate,job,request=prepare(store,registry,'storyboard')
    done,receipt=completed_check(store,job,result_for(request))
    request,data=store.repository.content_language.load(original.project_id,job)
    assert request.stage=='storyboard' and request.source['operation']==CHECK_OPERATION
    assert 'dialogue-timing-contract.json' not in request.input_artifacts and CHECK_INPUT in request.input_artifacts
    from plotloom.persistence.schema import SourceOutlineCandidateRow
    with store.repository._read() as session:
        checked=verified_check(session.get(SourceOutlineCandidateRow,job))
    assert checked[-1].verdict=='pass' and checked[-2]==receipt
    profile=CodexExecProfile.model_validate(data['profile'])
    pin=store.creative_handoff_execution_pin(request)
    job_root=store.creative_handoff_exchange().root/'jobs'/job
    files={path.relative_to(job_root):path.read_bytes() for path in job_root.rglob('*') if path.is_file()}
    before_request=canonical_json(request.model_dump(mode='json',by_alias=True))
    before_evidence=canonical_json(data)
    expected,instructions,*_=project_creative_package(job_root,request,pin,executor_backend='codex_exec',plotloom_code_revision=done.plotloom_code_revision)
    assert files[next(path for path in files if str(path)=='package/request.json')]==canonical_json(expected)
    assert files[next(path for path in files if str(path)=='package/COPY_ASSIGNMENT.txt')]==instructions
    assert expected['validationPlanHash']==done.validation_plan_hash==receipt.text_validation.plan_hash
    def primary_forbidden(*_args,**_kwargs):
        raise AssertionError('a checker cannot acquire primary Storyboard timing/style ownership')
    monkeypatch.setattr('plotloom.codex_exec_retained_storyboard.retained_storyboard_package_projection',primary_forbidden)
    plan=_retained_checkpoint_validation_plan(request,execution_pin=pin,source_revision=done.plotloom_code_revision)
    projection=_retained_codex_request_projection(request,pin,profile,job_root.parent,plotloom_code_revision=done.plotloom_code_revision)
    assert plan.model_dump(mode='json',by_alias=True)==expected['validationPlan']
    assert plan.plan_hash==receipt.text_validation.plan_hash
    assert canonical_json(projection)==canonical_json(expected)
    assert before_request==canonical_json(request.model_dump(mode='json',by_alias=True))
    assert before_evidence==canonical_json(store.repository.content_language.load(original.project_id,job)[1])
    assert {path.relative_to(job_root):path.read_bytes() for path in job_root.rglob('*') if path.is_file()}==files
    assert json.loads(before_request)['source']['operation']==CHECK_OPERATION
