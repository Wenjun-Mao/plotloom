"""Controlled CLI child + real Script validators/storage; no provider/model calls."""
import json
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest
from codex_exec_supervisor_test_support import _write_fake_cli

from plotloom.autopilot_contracts import LaunchRequest, RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.project_storage import ProjectFolderStorage
from plotloom.exceptions import InvalidTransitionError
from plotloom.text_correction_contracts import logical_checkpoint, TextRetryGrant
from tests.autopilot_controller_fixtures import candidate, default_brief
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.creative_delivery_fixtures import _pilot_script
from tests.test_specialist_settings import configured


def script_cli(*, exhaust):
    return f'''
import json, os, sys
from datetime import date
from pathlib import Path
from uuid import uuid4
if len(sys.argv)>1 and sys.argv[1]=="sandbox":
    args=sys.argv[sys.argv.index("--")+1:]
    # This fixture source owns a metadata-only Python. Run its actual receiver
    # with the explicit test interpreter; this is not native-envelope proof.
    if Path(args[0]).name=="uv" and "python" in args:
        args=[{sys.executable!r},*args[args.index("python")+1:]]
    elif args[0].endswith("/.local/codex-exec/python-env/bin/python"):
        args[0]={sys.executable!r}
    os.execv(args[0],args)
sys.stdin.read()
request=json.loads((Path.cwd().parent/"package/request.json").read_bytes())
doc={_pilot_script()!r};doc["lang"]="en"
from copy import deepcopy
doc["sectionBindings"]=request["inputArtifacts"]["script-admission.json"]["sectionBindings"]
template=doc["episodes"][0]
scene=request["inputArtifacts"]["art.json"]["scenes"][0]
template["scenes"][0].update(sceneId=scene["id"],lighting=scene["lighting"][0]["state"])
template["scenes"][0]["characters"]=[]
if not request.get("textCorrection") or {exhaust!r}:
    template["scenes"][0]["flow"]=template["scenes"][0]["flow"][:1]
doc["episodes"]=[dict(deepcopy(template),ep=b["episode"]) for b in doc["sectionBindings"]]
(Path.cwd()/"script.json").write_text(json.dumps(doc))
session=str(uuid4());folder=Path(os.environ["CODEX_HOME"])/"sessions"/date.today().strftime("%Y/%m/%d")
folder.mkdir(parents=True,exist_ok=True)
(folder/f"rollout-fixture-{{session}}.jsonl").write_text(json.dumps({{"type":"session_meta","payload":{{"id":session}},"ordinal":0}})+"\\n")
for event in [{{"type":"thread.started","thread_id":session}},{{"type":"turn.started"}},{{"type":"turn.completed"}}]:
    print(json.dumps(event),flush=True)
'''


def environment(supervisor, tmp_path, monkeypatch, *, exhaust, limit):
    import subprocess
    from plotloom import autopilot_service
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom.codex_exec_contracts import CodexExecReadiness
    profile = _write_fake_cli(supervisor, script_cli(exhaust=exhaust))
    original_pin = CreativeHandoffExchange.current_execution_pin
    revision = subprocess.check_output(["git","-C",str(supervisor.source_root),"rev-parse","HEAD"],text=True).strip()
    monkeypatch.setattr(CreativeHandoffExchange,"current_execution_pin",lambda self,stage:
        {"upstreamRevision":revision,"upstreamSkillHash":"b"*64,"specialistSkillHash":"c"*64}
        if stage in {"bridge-intent","bridge-presentation"} else original_pin(self,stage))
    storage = ProjectFolderStorage(outputs_root=supervisor.outputs_root, application_data_root=tmp_path/'application')
    with closing(storage.projects.create(default_brief())) as store:
        project = store.manifest.project_id
    registry, _ = configured(storage.application.root)
    registry.codex_exec_profile = lambda: profile
    registry.host_client.codex_exec_readiness = lambda: CodexExecReadiness(state='ready')
    registry.require_codex_exec_readiness = lambda: CodexExecReadiness(state='ready')
    host = FakeCodexExecHost(storage, registry, candidate_factory=candidate)
    registry.codex_exec_admit = lambda att: supervisor.admit(att) if att.operation_key.startswith('script') else host.admit(att)
    registry.codex_exec_status = lambda aid: host.status(aid) if str(aid) in host.statuses else supervisor.status(aid)
    registry.codex_exec_cancel = supervisor.cancel
    registry.codex_exec_suspend = supervisor.suspend
    freeze = autopilot_service.freeze_launch_policy
    monkeypatch.setattr(autopilot_service,'freeze_launch_policy',lambda *args:freeze(*args).model_copy(update={'early_reference_limit':0}))
    service = AutopilotService(storage,registry)
    run = service.launch(project,LaunchRequest(expected_brief_revision=1,render_style='realistic',art_render_style='realistic',text_correction_limit=limit))
    assert service.acquire_controller()
    return storage, registry, service, run


@pytest.mark.parametrize('exhaust,limit', [(False,1),(True,1),(True,0),(True,2)])
def test_script_real_host_one_correction_adoption_or_terminal_exhaustion(supervisor,tmp_path,monkeypatch,exhaust,limit):
    storage,registry,service,run=environment(supervisor,tmp_path,monkeypatch,exhaust=exhaust,limit=limit)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                current=store.repository.autopilot.current(run.project_id)
                cp=logical_checkpoint(current,'script')
                if current.state=='blocked' or cp and cp['state']=='adopted':break
            time.sleep(.05)
        with closing(storage.projects.open(run.project_id)) as store:
            current=store.repository.autopilot.current(run.project_id)
            cp=logical_checkpoint(current,'script')
            original=next(c for c in current.checkpoints if c['operationKey']=='script')
            failed=store.repository.autopilot.exec_attempt_for_operation(run.id,'script')
            assert failed.content_rejection is not None, current.blocker
            assert failed.content_rejection.stage=='script' and original['state']=='failed'
            rows=[c for c in current.checkpoints if c['evidence']['owner']=='script']
            assert len(rows)==(2 if limit else 1), current.blocker
            from plotloom.autopilot_text_failures import failure_context, retry_text
            context=failure_context(store,registry,stage='script')
            assert context and context['canRetry'] is False
            assert context['automaticLimit']==min(limit,1)
            from contextlib import contextmanager
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from plotloom.api.project_folder_autopilot import register_autopilot_routes
            app=FastAPI()
            @contextmanager
            def opened(project_id):
                with closing(storage.projects.open(project_id)) as current_store:yield current_store
            register_autopilot_routes(app,opened,service)
            with TestClient(app) as client:
                public=client.get(f'/api/v2/projects/{run.project_id}/autopilot/text-failure?stage=script')
                assert public.status_code==200 and public.json()['canRetry'] is False
            if exhaust:
                assert current.state=='blocked' and cp['state']=='failed'
                assert store.script_state().accepted_script is None
                from uuid import uuid4
                with pytest.raises(InvalidTransitionError,match='identity is unavailable'):
                    retry_text(store,registry,TextRetryGrant(command_id=uuid4(),expected_run_id=run.id,
                        expected_revision=current.revision,failed_attempt_id=failed.attempt_id,
                        rejection_hash=failed.content_rejection.rejection_hash))
            else:
                assert cp['state']=='adopted', current.blocker
                corrective,receipt=store.repository.autopilot.exec_attempt_evidence_for_operation(run.id,'script:correction:1')
                assert corrective.job_id!=failed.job_id and corrective.attempt_id!=failed.attempt_id
                assert receipt and len(receipt.text_validation.steps)==2
                assert store.script_state().accepted_script.candidate_job_id==corrective.job_id
                assert context['resolved'] and len(context['history'])==2
        service.close()
        service=AutopilotService(storage,registry)
        assert service.acquire_controller()
        if exhaust:service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            reread=store.repository.autopilot.current(run.project_id)
            assert next(c for c in reread.checkpoints if c['operationKey']=='script')==original
            assert len([c for c in reread.checkpoints if c['evidence']['owner']=='script'])==(2 if limit else 1)
        if not exhaust:service.control(run.project_id,RunControlRequest(expected_revision=reread.revision,action='pause'))
        service.close()
        snapshot=storage.recovery.create_snapshot(run.project_id)
        restored=ProjectFolderStorage(outputs_root=tmp_path/'restored',application_data_root=tmp_path/'restored-app')
        restored.recovery.restore(Path(snapshot.location))
        with closing(restored.projects.open(run.project_id)) as store:
            assert logical_checkpoint(store.repository.autopilot.current(run.project_id),'script')['state']==cp['state']
        (tmp_path/'script-correction-proof.json').write_text(json.dumps({'scope':'controlled CLI fixture; real Script validation/render/storage',
            'originalAttempt':failed.model_dump(mode='json',by_alias=True),'history':context},ensure_ascii=False))
    finally:
        service.close()
