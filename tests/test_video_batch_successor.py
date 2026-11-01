"""Native owner/CAS checks for fresh corrected-source work, without providers."""
from contextlib import closing
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecHostStatus
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.schema import VideoBatchRow
from plotloom.shot_presentation import ShotPresentationRequest
from plotloom.video_batch_contracts import BatchControl, BatchSetup
from plotloom.video_batch_inventory import source_binding
from plotloom.video_batch_successor import CorrectedSourceSuccessor
from plotloom.video_contracts import VideoJobRequest
from tests.autopilot_controller_fixtures import PIN
from tests.codex_exec_fixtures import install_profile
from tests.video_batch_fixtures import batch_environment


@pytest.fixture
def cancelled(tmp_path):
    storage, client, service, provider, pid, initial = batch_environment(tmp_path)
    service.control(pid, BatchControl(batchId=initial['id'], expectedControlRevision=initial['controlRevision'], action='cancel'))
    target = initial['manifest']['targets'][0]; args = target['args']; sid = target['shotId']
    request = VideoJobRequest(approvalId=args['approval_id'], shotId=sid, storyboardRevision=args['storyboard_revision'],
        expectedSelectionRevision=args['expected_selection_revision'], idempotencyKey='cancelled-source', seed=17,
        requestedDurationSeconds=5, resolution='576x1024', audio=True, aspectPolicy='reject_mismatch',
        profileId='minimax_h3_quality8_portrait_576x1024_v2', playbackIntent='whole_take', automaticRetryLimit=0)
    setup = BatchSetup(profileId=request.profile_id, shotIds=[sid], singleRequest=request, automaticRetryLimit=0,maxJobs=1,maxRequestedSeconds=5)
    historical=service.setup(pid,setup.model_copy(update={'single_request':request.model_copy(update={'idempotency_key':'historical-key'})}))
    service.control(pid,BatchControl(batchId=historical['id'],expectedControlRevision=historical['controlRevision'],action='cancel'))
    before = service.setup(pid, setup)
    install_profile(service.registry)
    with patch.object(CreativeHandoffExchange, 'current_execution_pin', return_value=PIN):
        before = service.draft(pid, before['revision'])
    draft = deepcopy(before['execution']['draft'])
    attempt = CodexExecAttempt.model_validate(draft['attempt']).model_copy(update={
        'state':'outcome_unknown', 'execution_failure':'cancelled', 'process_id':61000,
        'process_group_id':61000, 'process_birth_identity':'fixture:cancelled-text'})
    draft |= {'attempt':attempt.model_dump(mode='json', by_alias=True), 'localExecutionStopped':True}
    def freeze(row):
        row.state='cancelled'; row.execution = row.execution | {'draft':draft}
    with closing(storage.projects.open(pid)) as store:
        before = store.repository.video_batches.change(pid, before['id'], mutate=freeze)
    proof = CodexExecHostStatus(state='outcome_unknown', attempt=attempt, localExecutionStopped=True)
    service.registry.codex_exec_status = lambda _identifier: proof
    def no_dispatch(*_args, **_kwargs):
        raise AssertionError('successor preparation must not admit text or submit media')
    service.registry.codex_exec_admit = no_dispatch
    return dict(storage=storage, client=client, service=service, provider=provider, pid=pid,
                before=before, attempt=attempt, setup=setup, proof=proof, sid=sid)


def corrected(env, *, change_source=True):
    storage, pid, old = env['storage'], env['pid'], env['before']
    target=old['manifest']['targets'][0]; args=target['args']; shot=target['snapshot']['shot']
    with closing(storage.projects.open(pid)) as store:
        if change_source:
            state=store.media.shot_presentations.get(pid, env['sid'])
            physical={k:shot[k] for k in ('action','composition','visualIntent','motionIntent','cameraMovement')}
            physical['composition']='Preserve the actual pictured hand arrangement; do not reset the earlier pose.'
            physical['cameraMovement']=physical['cameraMovement'] or 'Static Shot'
            result=store.media.shot_presentations.review(pid,env['sid'],ShotPresentationRequest(
                expectedRevision=state['revision'],sourceHash=state['source']['sourceHash'],approvalId=args['approval_id'],
                storyboardRevision=args['storyboard_revision'],physical=physical,literalSources=[],messagePresentation='source',
                reason='Disposable corrected-source fixture, original dialogue retained.',reviewed=True))
            asset=target['snapshot']['keyframe']['assetId']
            intent=store.media.create_visual_intent(pid,asset,{'role':'shot_keyframe','compositionIntent':physical['composition'],'sourceRefs':[env['sid']]})
            store.media.select_reviewed_keyframe(pid,asset_id=asset,shot_id=env['sid'],scene_id=shot['sceneId'],
                expected_selection_revision=store.media.visual_selection_revision(pid),storyboard_revision=args['storyboard_revision'],
                approval_id=args['approval_id'],compatibility_note='Same retained frame, corrected presentation reviewed.',
                visual_intent_id=intent['id'],visual_intent_revision=intent['revision'],expected_presentation_revision=result['revision'])
        setup=env['setup'].model_copy(update={'single_request':env['setup'].single_request.model_copy(update={
            'idempotency_key':'corrected-source','expected_selection_revision':store.media.visual_selection_revision(pid)})})
        return CorrectedSourceSuccessor(commandId=uuid4(),predecessorBatchId=old['id'],expectedRevision=old['revision'],
            predecessorJobId=env['attempt'].job_id,predecessorAttemptId=env['attempt'].attempt_id,
            expectedSourceHash=stable_hash(source_binding(store)),setup=setup)


def rows(env):
    with closing(env['storage'].projects.open(env['pid'])) as store, store.repository._read() as session:
        return {r.id:store.repository.video_batches.view(r) for r in session.scalars(select(VideoBatchRow))}


def test_explicit_successor_preserves_unknown_and_needs_fresh_authorization(cancelled):
    env=cancelled; command=corrected(env); before=deepcopy(rows(env))
    with pytest.raises(InvalidTransitionError,match='unsettled'):
        env['service'].setup(env['pid'],command.setup)
    response=env['client'].post(f"/api/v2/projects/{env['pid']}/video-batch/corrected-source-successor",json=command.model_dump(mode='json',by_alias=True))
    assert response.status_code==200,response.text
    result=response.json()
    assert result['id']!=env['before']['id'] and result['state']=='setup'
    assert result['execution']['jobs']=={} and 'authorizedManifestHash' not in result['execution']
    assert not result['execution'].get('draft') and not result['execution'].get('fidelity')
    link=result['execution']['correctedSourcePredecessor']
    assert link['attempt']==env['attempt'].model_dump(mode='json',by_alias=True)
    assert link['possiblePriorCost'] is True and link['nativeLocalExecutionStopped'] is True
    old=rows(env)[env['before']['id']]
    assert old['state']=='cancelled' and old['execution']['draft']==before[old['id']]['execution']['draft']
    assert env['service'].corrected_source_successor(env['pid'],command)==result
    assert len(rows(env))==len(before)+1 and not env['provider'].submits
    changed=command.model_copy(update={'expected_source_hash':'0'*64})
    with pytest.raises(InvalidTransitionError,match='different inputs'):
        env['service'].corrected_source_successor(env['pid'],changed)


@pytest.mark.parametrize('case',['same-source','stale-revision','stale-source','wrong-attempt','host-running',
    'wrong-host-identity','image','permission','changed-settings','same-request','historical-key'])
def test_refusals_leave_every_row_unchanged(cancelled,case):
    env=cancelled; command=corrected(env,change_source=case!='same-source')
    if case=='stale-revision':command=command.model_copy(update={'expected_revision':1})
    elif case=='stale-source':command=command.model_copy(update={'expected_source_hash':'0'*64})
    elif case=='wrong-attempt':command=command.model_copy(update={'predecessor_attempt_id':uuid4()})
    elif case=='host-running':env['service'].registry.codex_exec_status=lambda _:env['proof'].model_copy(update={'local_execution_stopped':False})
    elif case=='wrong-host-identity':env['service'].registry.codex_exec_status=lambda _:env['proof'].model_copy(update={'attempt':env['attempt'].model_copy(update={'job_id':'ch_'+'f'*32})})
    elif case=='image':env['service'].registry.codex_exec_status=lambda _:env['proof'].model_copy(update={'attempt':env['attempt'].model_copy(update={'domain':'image','reserved_image_outputs':1,'image_budget_state':'reserved'})})
    elif case=='permission':
        def mutate(row):
            data=deepcopy(row.execution['draft']);data['attempt']['executionFailure']='permission'
            row.execution=row.execution|{'draft':data}
        with closing(env['storage'].projects.open(env['pid'])) as store:
            value=store.repository.video_batches.change(env['pid'],env['before']['id'],mutate=mutate)
        command=command.model_copy(update={'expected_revision':value['revision']})
    elif case in {'changed-settings','same-request','historical-key'}:
        request=command.setup.single_request.model_copy(update={'requested_duration_seconds':8} if case=='changed-settings' else {'idempotency_key':'historical-key' if case=='historical-key' else 'cancelled-source'})
        command=command.model_copy(update={'setup':command.setup.model_copy(update={'single_request':request})})
    before=rows(env)
    with pytest.raises(InvalidTransitionError):env['service'].corrected_source_successor(env['pid'],command)
    assert rows(env)==before and not env['provider'].submits


def test_production_authorization_cannot_use_this_successor(tmp_path):
    from tests.video_batch_fixtures import ready_batch,start_batch
    storage,_client,service,provider,pid,view=batch_environment(tmp_path)
    started=start_batch(service,pid,ready_batch(service,pid,view))
    stopped=service.control(pid,BatchControl(batchId=started['id'],expectedControlRevision=started['controlRevision'],action='cancel'))
    data=stopped['execution']['fidelity']
    with closing(storage.projects.open(pid)) as store:
        command=CorrectedSourceSuccessor(commandId=uuid4(),predecessorBatchId=stopped['id'],expectedRevision=stopped['revision'],
            predecessorJobId=data['attempt']['jobId'],predecessorAttemptId=data['attempt']['attemptId'],
            expectedSourceHash=stable_hash(source_binding(store)),setup=BatchSetup.model_validate(stopped['manifest']['setup']))
    with pytest.raises(InvalidTransitionError,match='unstarted'):
        service.corrected_source_successor(pid,command)
    assert service.current(pid)['id']==stopped['id'] and not provider.submits


def test_late_failure_rolls_back_both_successor_and_predecessor_link(cancelled,monkeypatch):
    env=cancelled; command=corrected(env); before=rows(env)
    from plotloom.persistence.project.video_batches import VideoBatches
    original=VideoBatches.change
    def fail(self,project_id,batch_id,**kwargs):
        if batch_id!=env['before']['id']:raise RuntimeError('fixture late link failure')
        return original(self,project_id,batch_id,**kwargs)
    monkeypatch.setattr(VideoBatches,'change',fail)
    with pytest.raises(RuntimeError,match='late link failure'):
        env['service'].corrected_source_successor(env['pid'],command)
    assert rows(env)==before and not env['provider'].submits


def test_competing_commands_create_only_one_successor(cancelled):
    from concurrent.futures import ThreadPoolExecutor
    env=cancelled;command=corrected(env);second=command.model_copy(update={'command_id':uuid4()})
    def create(value):
        try:return env['service'].corrected_source_successor(env['pid'],value)['id']
        except InvalidTransitionError:return None
    before=len(rows(env))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(create,[command,second]))
    assert sum(value is not None for value in results)==1
    assert len(rows(env))==before+1 and not env['provider'].submits


def test_reopening_refuses_a_changed_predecessor_link(cancelled):
    from plotloom.project_storage.format import ProjectStorageCorruptionError
    env=cancelled;command=corrected(env)
    result=env['service'].corrected_source_successor(env['pid'],command)
    with closing(env['storage'].projects.open(env['pid'])) as store:
        def corrupt(row):
            link=deepcopy(row.execution['correctedSourcePredecessor']);link['attempt']['state']='failed'
            row.execution=row.execution|{'correctedSourcePredecessor':link}
        store.repository.video_batches.change(env['pid'],result['id'],mutate=corrupt)
    with pytest.raises(ProjectStorageCorruptionError):env['storage'].projects.open(env['pid'])


def test_reopening_cannot_widen_a_rehashed_successor_grant(cancelled):
    from plotloom.project_storage.format import ProjectStorageCorruptionError
    env=cancelled;command=corrected(env)
    result=env['service'].corrected_source_successor(env['pid'],command)
    with closing(env['storage'].projects.open(env['pid'])) as store,store.repository.manual_command() as session:
        row=session.get(VideoBatchRow,result['id']);old=session.get(VideoBatchRow,env['before']['id'])
        manifest=deepcopy(row.manifest);manifest['setup']|={'maxJobs':2,'maxRequestedSeconds':10}
        execution=deepcopy(row.execution);link=execution['correctedSourcePredecessor']
        link['request']['setup']|={'maxJobs':2,'maxRequestedSeconds':10};link['requestHash']=stable_hash(link['request'])
        back=deepcopy(old.execution);back['correctedSourceSuccessor']['requestHash']=link['requestHash']
        row.manifest=manifest;row.manifest_hash=stable_hash(manifest);row.execution=execution;old.execution=back
    with pytest.raises(ProjectStorageCorruptionError):env['storage'].projects.open(env['pid'])


def test_fresh_native_draft_check_and_authorization_can_prepare_its_own_job(cancelled):
    from tests.autopilot_fake_exec_host import FakeCodexExecHost
    from tests.video_batch_fixtures import draft_for,start_batch
    from tests.video_fidelity_fixtures import fidelity_for
    env=cancelled;service=env['service'];pid=env['pid']
    current=service.corrected_source_successor(pid,corrected(env))
    def candidate(_store,request):
        if request.source['operation']=='fidelity-check':return fidelity_for(request)
        return draft_for({'manifest':request.input_artifacts['video-targets.json']}).model_dump(mode='json',by_alias=True)
    host=FakeCodexExecHost(env['storage'],service.registry,candidate_factory=candidate)
    service.registry.codex_exec_admit=host.admit
    service.registry.codex_exec_status=lambda identifier:env['proof'] if identifier==env['attempt'].attempt_id else host.status(identifier)
    with patch.object(CreativeHandoffExchange,'current_execution_pin',return_value=PIN):
        current=service.draft(pid,current['revision'])
        for _ in range(8):
            service.step(pid);current=service.current(pid)
            if current['state']=='ready':break
    assert current['state']=='ready',current['execution'].get('error')
    assert current['execution']['draft']['attempt']['attemptId']!=str(env['attempt'].attempt_id)
    assert current['execution']['fidelity']['attempt']['attemptId']!=str(env['attempt'].attempt_id)
    start_batch(service,pid,current);service.step(pid)
    linked=service.current(pid)
    assert len(linked['execution']['jobs'])==1 and not env['provider'].submits
    assert rows(env)[env['before']['id']]['execution']['draft']['attempt']==env['attempt'].model_dump(mode='json',by_alias=True)
