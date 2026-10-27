"""Actual Art head/correction/adoption/reopen over a controlled CLI child."""
import json
import time
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_autopilot import register_autopilot_routes
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_failures import failure_context
from plotloom.project_storage import ProjectFolderStorage
from plotloom.text_correction_contracts import logical_checkpoint
from tests.art_structure_host_fixtures import environment


@pytest.mark.parametrize('exhaust,limit', [(False,1),(True,1),(True,0)])
def test_art_real_child_head_correction_adoption_or_exhaustion(supervisor,tmp_path,monkeypatch,exhaust,limit):
    storage,registry,service,run = environment(supervisor,tmp_path,monkeypatch,exhaust=exhaust,limit=limit)
    try:
        deadline = time.monotonic()+45
        while time.monotonic()<deadline:
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                current = store.repository.autopilot.current(run.project_id)
                cp = logical_checkpoint(current,'art')
                if current.state=='blocked' or cp and cp['state']=='adopted':break
            time.sleep(.05)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
            cp = logical_checkpoint(current,'art')
            original = next(c for c in current.checkpoints if c['operationKey']=='art')
            failed = store.repository.autopilot.exec_attempt_for_operation(run.id,'art')
            assert failed.content_rejection is not None,current.blocker
            assert failed.content_rejection.stage=='art' and original['state']=='failed'
            original_path = store.creative_handoff_exchange().root/'jobs'/failed.job_id/'delivery/art.json'
            original_bytes = original_path.read_bytes()
            from hashlib import sha256
            assert sha256(original_bytes).hexdigest()==failed.content_rejection.candidate_hash
            rows = [c for c in current.checkpoints if c['evidence']['owner']=='art']
            assert len(rows)==(2 if limit else 1),current.blocker
            context = failure_context(store,registry,stage='art')
            assert context and context['canRetry'] is exhaust and context['automaticLimit']==limit
            app=FastAPI()
            @contextmanager
            def opened(project_id):
                with closing(storage.projects.open(project_id)) as current_store:yield current_store
            register_autopilot_routes(app,opened,service)
            with TestClient(app) as client:
                public=client.get(f'/api/v2/projects/{run.project_id}/autopilot/text-failure?stage=art')
                assert public.status_code==200 and public.json()['canRetry'] is exhaust
            if exhaust:
                assert current.state=='blocked' and cp['state']=='failed'
                assert store.art_state().accepted_art is None
            else:
                assert cp['state']=='adopted',current.blocker
                corrective,receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id,'art:correction:1')
                assert corrective.job_id!=failed.job_id and corrective.attempt_id!=failed.attempt_id
                assert receipt and [step.step_id for step in receipt.text_validation.steps]==['validate','render']
                assert store.art_state().accepted_art.candidate_job_id==corrective.job_id
                assert context['resolved'] and len(context['history'])==2
            assert original_path.read_bytes()==original_bytes
        service.close();service=AutopilotService(storage,registry);assert service.acquire_controller()
        if exhaust:service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            reread=store.repository.autopilot.current(run.project_id)
            assert next(c for c in reread.checkpoints if c['operationKey']=='art')==original
            assert len([c for c in reread.checkpoints if c['evidence']['owner']=='art'])==(2 if limit else 1)
            assert not any(c['operationKey']=='art:correction:2' for c in reread.checkpoints)
        if not exhaust:service.control(run.project_id,RunControlRequest(expected_revision=reread.revision,action='pause'))
        service.close()
        snapshot=storage.recovery.create_snapshot(run.project_id)
        restored=ProjectFolderStorage(outputs_root=tmp_path/'restored',application_data_root=tmp_path/'restored-app')
        restored.recovery.restore(Path(snapshot.location))
        with closing(restored.projects.open(run.project_id)) as store:
            assert logical_checkpoint(store.repository.autopilot.current(run.project_id),'art')['state']==cp['state']
        (tmp_path/'art-correction-proof.json').write_text(json.dumps({'scope':'controlled child; actual Python/Node validation and real Art head',
            'originalAttempt':failed.model_dump(mode='json',by_alias=True),'history':context},ensure_ascii=False))
    finally:service.close()
