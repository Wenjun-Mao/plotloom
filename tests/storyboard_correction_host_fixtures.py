"""Actual controlled child/Node validators and real Storyboard persistence, no provider."""
import json
import sys
import subprocess
from contextlib import closing
from pathlib import Path

from codex_exec_supervisor_test_support import _write_fake_cli
from plotloom.autopilot_contracts import LaunchRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.codex_exec_contracts import CodexExecReadiness
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_controller_fixtures import candidate, default_brief
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.test_specialist_settings import configured

ROOT = Path(__file__).resolve().parents[1]


def storyboard_cli(*, exhaust):
    return f'''
import json, os, sys, time
from datetime import date
from pathlib import Path
from uuid import uuid4
if len(sys.argv)>1 and sys.argv[1]=="sandbox":
    args=sys.argv[sys.argv.index("--")+1:]
    if Path(args[0]).name=="uv" and "python" in args:
        args=[{sys.executable!r},*args[args.index("python")+1:]]
    elif args[0].endswith("/.local/codex-exec/python-env/bin/python"):
        args[0]={sys.executable!r}
    os.execv(args[0],args)
sys.stdin.read()
sys.path.insert(0,{str(ROOT)!r})
from tests.storyboard_correction_fixtures import board_for_request, bad_segment
request=json.loads((Path.cwd().parent/"package/request.json").read_bytes())
doc=board_for_request(request)
if not request.get("textCorrection") or {exhaust!r}:doc=bad_segment(doc)
if not request.get("textCorrection"):time.sleep(1)
(Path.cwd()/"storyboard.json").write_text(json.dumps(doc))
session=str(uuid4());folder=Path(os.environ["CODEX_HOME"])/"sessions"/date.today().strftime("%Y/%m/%d")
folder.mkdir(parents=True,exist_ok=True)
(folder/f"rollout-fixture-{{session}}.jsonl").write_text(json.dumps({{"type":"session_meta","payload":{{"id":session}},"ordinal":0}})+"\\n")
for event in [{{"type":"thread.started","thread_id":session}},{{"type":"turn.started"}},{{"type":"turn.completed"}}]:
    print(json.dumps(event),flush=True)
'''


def environment(supervisor, tmp_path, monkeypatch, *, exhaust, limit):
    from plotloom import autopilot_service
    profile = _write_fake_cli(supervisor, storyboard_cli(exhaust=exhaust))
    original_pin = CreativeHandoffExchange.current_execution_pin
    revision = subprocess.check_output(['git','-C',str(supervisor.source_root),'rev-parse','HEAD'],text=True).strip()
    monkeypatch.setattr(CreativeHandoffExchange,'current_execution_pin',lambda self,stage:
        {'upstreamRevision':revision,'upstreamSkillHash':'b'*64,'specialistSkillHash':'c'*64}
        if stage in {'bridge-intent','bridge-presentation'} else original_pin(self,stage))
    storage = ProjectFolderStorage(outputs_root=supervisor.outputs_root,application_data_root=tmp_path/'application')
    with closing(storage.projects.create(default_brief())) as store:project = store.manifest.project_id
    registry,_ = configured(storage.application.root)
    registry.codex_exec_profile = lambda:profile
    registry.host_client.codex_exec_readiness = lambda:CodexExecReadiness(state='ready')
    registry.require_codex_exec_readiness = lambda:CodexExecReadiness(state='ready')
    host = FakeCodexExecHost(storage,registry,candidate_factory=candidate)
    registry.codex_exec_admit = lambda att:supervisor.admit(att) if att.operation_key.startswith('storyboard') else host.admit(att)
    registry.codex_exec_status = lambda aid:host.status(aid) if str(aid) in host.statuses else supervisor.status(aid)
    registry.codex_exec_cancel = supervisor.cancel
    registry.codex_exec_suspend = supervisor.suspend
    freeze = autopilot_service.freeze_launch_policy
    monkeypatch.setattr(autopilot_service,'freeze_launch_policy',lambda *args:freeze(*args).model_copy(update={'early_reference_limit':0}))
    service = AutopilotService(storage,registry)
    run = service.launch(project,LaunchRequest(expected_brief_revision=1,render_style='realistic',
        art_render_style='realistic',text_correction_limit=limit))
    assert service.acquire_controller()
    return storage,registry,service,run
