"""Actual Storyboard head/correction/adoption/reopen over a controlled CLI child."""
import json
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_autopilot import register_autopilot_routes
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_failures import failure_context, retry_text
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage import ProjectFolderStorage
from plotloom.text_correction_contracts import logical_checkpoint, TextRetryGrant
from tests.storyboard_correction_host_fixtures import environment


@pytest.mark.parametrize('exhaust,limit', [(False,1),(True,1),(True,0),(True,2)])
def test_storyboard_real_child_head_correction_adoption_or_exhaustion(supervisor,tmp_path,monkeypatch,exhaust,limit):
    storage,registry,service,run = environment(supervisor,tmp_path,monkeypatch,exhaust=exhaust,limit=limit)
    try:
        deadline = time.monotonic()+45
        while time.monotonic()<deadline:
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                current = store.repository.autopilot.current(run.project_id)
                cp = logical_checkpoint(current,'storyboard')
                if current.state=='blocked' or cp and cp['state']=='adopted':break
            time.sleep(.05)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
            cp = logical_checkpoint(current,'storyboard')
            original = next(c for c in current.checkpoints if c['operationKey']=='storyboard')
            failed = store.repository.autopilot.exec_attempt_for_operation(run.id,'storyboard')
            assert failed.content_rejection is not None,current.blocker
            assert failed.content_rejection.stage=='storyboard' and original['state']=='failed'
            original_path = store.creative_handoff_exchange().root/'jobs'/failed.job_id/'delivery/storyboard.json'
            original_bytes = original_path.read_bytes()
            from hashlib import sha256
            assert sha256(original_bytes).hexdigest()==failed.content_rejection.candidate_hash
            rows = [c for c in current.checkpoints if c['evidence']['owner']=='storyboard']
            assert len(rows)==(2 if limit else 1),current.blocker
            context = failure_context(store,registry,stage='storyboard')
            assert context and context['canRetry'] is False and context['automaticLimit']==min(limit,1)
            app=FastAPI()
            @contextmanager
            def opened(project_id):
                with closing(storage.projects.open(project_id)) as current_store:yield current_store
            register_autopilot_routes(app,opened,service)
            with TestClient(app) as client:
                public=client.get(f'/api/v2/projects/{run.project_id}/autopilot/text-failure?stage=storyboard')
                assert public.status_code==200 and public.json()['canRetry'] is False
            with pytest.raises(InvalidTransitionError):
                retry_text(store,registry,TextRetryGrant(command_id=uuid4(),expected_run_id=run.id,
                    expected_revision=current.revision,failed_attempt_id=failed.attempt_id,
                    rejection_hash=failed.content_rejection.rejection_hash))
            if exhaust:
                assert current.state=='blocked' and cp['state']=='failed'
                assert store.storyboard_review_state().accepted_review is None
                if limit == 0:
                    assert_publication_refusals(store, failed, run)
            else:
                assert cp['state']=='adopted',current.blocker
                corrective,receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id,'storyboard:correction:1')
                assert corrective.job_id!=failed.job_id and corrective.attempt_id!=failed.attempt_id
                assert receipt and [step.step_id for step in receipt.text_validation.steps]==['validate','render']
                assert store.storyboard_review_state().accepted_review.candidate_job_id==corrective.job_id
                assert context['resolved'] and len(context['history'])==2
            assert original_path.read_bytes()==original_bytes
        service.close();service=AutopilotService(storage,registry);assert service.acquire_controller()
        if exhaust:service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            reread=store.repository.autopilot.current(run.project_id)
            assert next(c for c in reread.checkpoints if c['operationKey']=='storyboard')==original
            assert len([c for c in reread.checkpoints if c['evidence']['owner']=='storyboard'])==(2 if limit else 1)
            assert not any(c['operationKey']=='storyboard:correction:2' for c in reread.checkpoints)
        if not exhaust:service.control(run.project_id,RunControlRequest(expected_revision=reread.revision,action='pause'))
        service.close()
        snapshot=storage.recovery.create_snapshot(run.project_id)
        restored=ProjectFolderStorage(outputs_root=tmp_path/'restored',application_data_root=tmp_path/'restored-app')
        restored.recovery.restore(Path(snapshot.location))
        with closing(restored.projects.open(run.project_id)) as store:
            assert logical_checkpoint(store.repository.autopilot.current(run.project_id),'storyboard')['state']==cp['state']
        (tmp_path/'storyboard-correction-proof.json').write_text(json.dumps({'scope':'controlled child; actualNodevalidation/realStoryBoardhead',
            'originalAttempt':failed.model_dump(mode='json',by_alias=True),'history':context},ensure_ascii=False))
    finally:service.close()


def assert_publication_refusals(store, failed, run):
    """Both real lifecycle consumers require frozen v4 + exact terminal evidence."""
    import sqlite3
    from plotloom.project_storage.operational_state import storyboard_review_publication_blockers
    from plotloom.persistence.project.production_rebuild_quiescence import assert_production_quiescent
    def quiescent():
        with store.repository._read() as session:
            return assert_production_quiescent(store.repository._project_access, session, run.project_id)
    assert storyboard_review_publication_blockers(store) == []
    quiescent()
    with sqlite3.connect(store.database_path) as connection:
        snapshot = connection.execute('SELECT snapshot FROM v2_autopilot_exec_attempts WHERE id=?', (str(failed.attempt_id),)).fetchone()[0]
        policy = connection.execute('SELECT policy FROM v2_autopilot_runs WHERE id=?', (run.id,)).fetchone()[0]
        evidence = connection.execute("SELECT evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key='storyboard'", (run.id,)).fetchone()[0]
        for mutation in ['no-rejection', 'unknown', 'v3', 'foreign-rejection', 'foreign-checkpoint']:
            changed = json.loads(snapshot)
            changed_policy, changed_evidence = json.loads(policy), json.loads(evidence)
            if mutation == 'no-rejection': changed.pop('contentRejection')
            elif mutation == 'unknown':
                changed.pop('contentRejection')
                changed.update(state='outcome_unknown', processExitCode=None, terminalResult=None,
                    remoteToolState=None, evidenceHash=None, outputHash=None, remoteOutputHash=None)
            elif mutation == 'v3': changed_policy['executorBinding']['textCorrectionContract'] = 'plotloom.text-correction.v3'
            elif mutation == 'foreign-rejection': changed['contentRejection']['sourceAttemptId'] = str(uuid4())
            else: changed_evidence['executorAttemptId'] = str(uuid4())
            try:
                connection.execute('UPDATE v2_autopilot_exec_attempts SET snapshot=? WHERE id=?', (json.dumps(changed), str(failed.attempt_id)))
                connection.execute('UPDATE v2_autopilot_runs SET policy=? WHERE id=?', (json.dumps(changed_policy), run.id))
                connection.execute("UPDATE v2_autopilot_checkpoints SET evidence=? WHERE run_id=? AND operation_key='storyboard'", (json.dumps(changed_evidence), run.id))
                connection.commit()
                if mutation == 'foreign-rejection':
                    with pytest.raises(ValueError): storyboard_review_publication_blockers(store)
                else:
                    assert storyboard_review_publication_blockers(store) == ['storyboard_review_publication_active']
                with pytest.raises((InvalidTransitionError, ValueError)): quiescent()
            finally:
                connection.execute('UPDATE v2_autopilot_exec_attempts SET snapshot=? WHERE id=?', (snapshot, str(failed.attempt_id)))
                connection.execute('UPDATE v2_autopilot_runs SET policy=? WHERE id=?', (policy, run.id))
                connection.execute("UPDATE v2_autopilot_checkpoints SET evidence=? WHERE run_id=? AND operation_key='storyboard'", (evidence, run.id))
                connection.commit()
    assert storyboard_review_publication_blockers(store) == []
    quiescent()
