"""Fixed current-source control imports scoped to one test; no retained packet dependency."""
import importlib.util
import sys
import time
from pathlib import Path
from types import ModuleType,SimpleNamespace

import pytest
from tests.cli_handoff_fixtures import ReadOnlyLoader,ROOT

CONTROLS=ROOT/'scripts/autopilot/handoff'


def load(monkeypatch,name,path):
    loader=ReadOnlyLoader(name,str(path))
    spec=importlib.util.spec_from_file_location(name,path,loader=loader)
    module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,module)
    loader.exec_module(module)
    return module


@pytest.fixture
def pair_controls(monkeypatch,tmp_path):
    """Only loop tests replace runtime composition. Production gates are not bypassed."""
    monkeypatch.syspath_prepend(str(ROOT/'services/creator_workbench'))
    context=ModuleType('pair_context')
    context.CONTROLS=CONTROLS
    context.current=lambda:SimpleNamespace(work=tmp_path,source=ROOT,campaign=tmp_path)
    monkeypatch.setitem(sys.modules,'pair_context',context)
    runtime=ModuleType('pair_runtime')
    runtime.activate=lambda _runtime:None
    runtime.settlement_deadline=lambda _runtime:time.monotonic()+10
    monkeypatch.setitem(sys.modules,'pair_runtime',runtime)
    modules={}
    for name in ('handoff_files','handoff_source','handoff_qa','admission_observation','parking_observation',
            'campaign_cleanup','canary_evidence','campaign_observation','campaign_guard','observe',
            'pair_workload','session_measurements','pair_sidecar','preservation','run_arm','run_pair'):
        modules[name]=load(monkeypatch,name,CONTROLS/(name+'.py'))
    observation=load(monkeypatch,'observation_fixtures',ROOT/'tests/qualification_pair_observation_fixtures.py')
    exports={}
    for module,names in ((modules['admission_observation'],('AdmissionObserver','LedgerRow','LedgerSample','ObservationError')),
            (modules['campaign_observation'],('CampaignObservation',)),(modules['campaign_cleanup'],('cleanup_snapshot',)),
            (modules['canary_evidence'],('prepared_package_snapshot',)),(modules['parking_observation'],('CleanupResult',)),
            (observation,('attempt','frozen','queued','successful_text','receipt_bound_sessions'))):
        exports.update({name:getattr(module,name) for name in names})
    return SimpleNamespace(modules=modules,exports=exports,context=context,runtime=runtime)
