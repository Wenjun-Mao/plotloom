"""Migrated strict completion/preservation control cases; no native launch."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace as Namespace
import pytest
from tests.qualification_pair_test_support import pair_controls,CONTROLS,load  # noqa: F401
WORK=CONTROLS


@pytest.mark.parametrize('gates,images,success',[
    ({'cross':1,'images':2,'texts':3},2,True),
    ({'cross':1,'images':2},2,False),
    ({'cross':3,'images':2,'texts':1},2,False),
    ({'cross':1,'images':2,'texts':3},1,False)])
def test_material_completion_does_not_substitute_for_current_overlap(pair_controls,tmp_path,monkeypatch,gates,images,success):
    guard=pair_controls.modules['campaign_guard']
    sessions=receipt_bound_sessions()[:images]
    if success:
        assert guard.require_arm_overlap(gates,sessions)['capacityOnlySpeedupEstablished'] is False
    else:
        with pytest.raises(RuntimeError,match='current pair lacks'):
            guard.require_arm_overlap(gates,sessions)


@pytest.mark.parametrize('completion',['immediate','late'])
def test_actual_project_owner_sidecar_retains_receipt_without_adoption(pair_controls,tmp_path,monkeypatch,completion):
    from plotloom.autopilot_contracts import RunControlRequest
    from tests.autopilot_controller_fixtures import environment
    storage,registry,service,run,calls=environment(tmp_path/'actual-owner',monkeypatch,auto_deliver=False)
    fake=registry._codex_exec_test_host
    original=registry.codex_exec_admit
    if completion=='immediate':
        def immediate(attempt):
            original(attempt)
            with closing(storage.projects.open(str(attempt.project_id))) as store:
                return fake.complete(store,fake.request(store,attempt),attempt)
        monkeypatch.setattr(registry,'codex_exec_admit',immediate)
    def snapshot():
        with closing(storage.projects.open(run.project_id)) as store:
            view=store.repository.autopilot.current(run.project_id)
            attempts=[]
            for checkpoint in view.checkpoints:
                attempt,_receipt=store.repository.autopilot.exec_attempt_evidence_for_operation(view.id,checkpoint['operationKey'])
                if attempt is not None:attempts.append(attempt.model_dump(mode='json',by_alias=True))
            return view,dict(run=view.model_dump(mode='json',by_alias=True),attempts=attempts)
    try:
        assert service.acquire_controller() and service._thread is None
        for _ in range(3):service.step(run.project_id)
        view,before=snapshot()
        assert pair_controls.modules['pair_sidecar'].requires_pause(before)
        service.control(run.project_id,RunControlRequest(expectedRevision=view.revision,action='pause'))
        fake.auto_deliver=True
        for _ in range(3):service.step(run.project_id)
        view,after=snapshot()
        assert view.state=='paused' and len(calls)==1 and fake.image_calls==[]
        assert {item['operationKey']:item['state'] for item in view.checkpoints}=={'source':'adopted','outline':'delivered'}
        assert after['attempts'][0]['terminalResult']=='success'
        with closing(storage.projects.open(run.project_id)) as store:
            assert store.source_outline_state().accepted_outline is None
    finally:
        service.close()


def test_interruption_halts_original_driver_without_an_adopting_continuation(pair_controls,tmp_path,monkeypatch):
    import signal
    from contextlib import contextmanager
    arm,plan,observed=successful_arm_path(tmp_path,monkeypatch,None)
    original=arm.controlled
    @contextmanager
    def interrupted(plan):
        with original(plan) as (runtime,client,service,capture):
            step=service.step
            def stop_before_sidecar(project):
                if project=='sidecar' and not arm.SETTLING:
                    arm.stop(signal.SIGTERM,None)
                step(project)
            service.step=stop_before_sidecar
            yield runtime,client,service,capture
    monkeypatch.setattr(arm,'controlled',interrupted)
    assert arm.execute(plan)==1
    result=json.loads((arm.WORK/'result.json').read_bytes())
    assert arm.STOP_REQUESTED and result['passed'] is False and observed.halts
    assert result['failure'].startswith('KeyboardInterrupt:')


def test_moved_work_root_keeps_historical_input_ownership(pair_controls,tmp_path,monkeypatch):
    preservation=pair_controls.modules['preservation']
    source=tmp_path/'source'
    historical=source/'retained'
    (historical/'old-campaign').mkdir(parents=True)
    (historical/'offline').mkdir()
    original=historical/'offline/result.json'
    original.write_text('original retained evidence')
    moved=tmp_path/'elsewhere/new-campaign'
    moved.mkdir(parents=True)
    (moved.parent/'offline').mkdir()
    (moved.parent/'offline/result.json').write_text('wrong sibling must not be read')
    baseline={'originalOfflineInputsAndProof':{'offline/result.json':hashlib.sha256(original.read_bytes()).hexdigest()}}
    pins={'oldCampaignRoot':'retained/old-campaign'}
    monkeypatch.setattr(preservation,'ROOT',source)
    monkeypatch.setattr(preservation,'WORK',moved)
    preservation.require_original_offline_inputs(baseline,pins)
    original.write_text('changed original')
    with pytest.raises(RuntimeError,match='original failed offline evidence changed'):
        preservation.require_original_offline_inputs(baseline,pins)


@pytest.mark.parametrize('checkpoint,pid',[('sent',123),('delivered',None),('delivered',123)])
def test_sidecar_pauses_before_any_next_step_for_late_immediate_or_retained_delivery(
        pair_controls,tmp_path,monkeypatch,checkpoint,pid):
    arm,plan,observed=successful_arm_path(tmp_path,monkeypatch,None)
    original=arm.snapshot
    paused=[]
    def snapshot(runtime,project,capture):
        value=original(runtime,project,capture)
        if project=='sidecar':
            value=dict(value,run=dict(value['run'],state='paused' if paused else 'running',bundle=None,
                checkpoints=[dict(operationKey='outline',state=checkpoint,evidence={})]))
            value['attempts']=[dict(value['attempts'][0],processId=pid)]
        return value
    monkeypatch.setattr(arm,'snapshot',snapshot)
    def pause(_client,project,_reason):
        if project=='sidecar':paused.append(True)
    monkeypatch.setattr(arm,'pause',pause)
    runtime_step=observed.steps
    # The existing fake service records calls; the real runner must have paused
    # before it can reach that sidecar call, which is then reconciliation-only.
    def check_before_step(_runtime,project,_view,_role,_capture):
        if project=='sidecar':
            assert paused
    monkeypatch.setattr(arm,'freeze_prepared',check_before_step)
    assert arm.execute(plan)==0
    assert paused and 'sidecar' in runtime_step


def test_failed_sidecar_pause_stops_before_sidecar_step(pair_controls,tmp_path,monkeypatch):
    arm,plan,observed=successful_arm_path(tmp_path,monkeypatch,None)
    original=arm.snapshot
    def snapshot(runtime,project,capture):
        value=original(runtime,project,capture)
        return dict(value,run=dict(value['run'],state='running')) if project=='sidecar' else value
    monkeypatch.setattr(arm,'snapshot',snapshot)
    def refuse(_client,project,_reason):
        if project=='sidecar':raise RuntimeError('synthetic pause refused')
    monkeypatch.setattr(arm,'pause',refuse)
    assert arm.execute(plan)==1
    assert 'sidecar' not in observed.steps
    assert observed.halts


def test_arm_restart_guard_precedes_preflight_or_controller_step(pair_controls,tmp_path,monkeypatch):
    import sys
    entry=load(monkeypatch,'pair_arm_receiver',CONTROLS/'pair_arm_receiver.py')
    monkeypatch.setattr(entry,'admit',lambda _role:None)
    monkeypatch.setitem(sys.modules,'handoff_phase',Namespace(R=CONTROLS.parents[2]))
    pair_controls.context.install=lambda **_options:Namespace(work=tmp_path)
    (tmp_path/'arm-start.json').write_text('retained original clock')
    monkeypatch.setattr(sys,'argv',['pair_arm_receiver.py','--arm','serial','--execute'])
    monkeypatch.setattr(pair_controls.modules['run_arm'],'main',lambda *_args:pytest.fail('restart advanced original sidecar'))
    with pytest.raises(RuntimeError,match='restart cannot advance or resend'):
        entry.main()

@pytest.fixture(autouse=True)
def bind_current_controls(pair_controls,monkeypatch):
    for name,value in pair_controls.exports.items():
        monkeypatch.setitem(globals(),name,value)
    helper=load(monkeypatch,'campaign_completion_fixtures',Path(__file__).parent/'qualification_pair_completion_fixtures.py')
    monkeypatch.setitem(globals(),'successful_arm_path',helper.successful_arm_path)
    monkeypatch.setitem(globals(),'successful_pair_path',helper.successful_pair_path)

@pytest.mark.parametrize("failure", [None, "primary", "sidecar", "rpc"])
def test_final_observation_failure_invalidates_otherwise_successful_real_arm(tmp_path, monkeypatch, failure):
    arm, plan, observed = successful_arm_path(tmp_path, monkeypatch, failure)
    assert arm.execute(plan) == (0 if failure is None else 1)
    result = json.loads((arm.WORK / "result.json").read_text())
    assert observed.verified == [True] and observed.material == [True]
    assert observed.final == ["primary", "sidecar"]
    assert result["cleanupOutcome"] == "complete_success" and result["completeSuccess"] is True
    assert result["passed"] is (failure is None)
    if failure in {"primary", "sidecar"}:
        assert "final_snapshot_failed: " + failure in result["failure"]
    elif failure == "rpc":
        assert observed.completeness == 2 and "final_rpc_observation_failed" in result["failure"]
    else:
        assert result["failure"] is None and observed.completeness == 2


@pytest.mark.parametrize("failure", [None, "rpc", "parked"])
def test_pair_runs_existing_strict_gate_after_both_successful_children(tmp_path, monkeypatch, failure):
    pair, sealed, observed = successful_pair_path(tmp_path, monkeypatch, failure)
    assert pair.execute(sealed) == (0 if failure is None else 1)
    result = json.loads((pair.WORK / "result.json").read_text())
    assert observed.children == ["serial", "parallel"]
    assert observed.gates == ["serial", "serial", "parallel"]
    assert all(arm["passed"] and arm["quiescent"] for arm in result["arms"].values())
    assert result["complete"] is (failure is None)
    assert set(result["successfulCurrentArmGates"]) == ({"serial", "parallel"} if failure is None else {"serial"})
    if failure:
        assert set(result["strictArmGateFailures"]) == {"parallel"}
        assert ("RPC evidence" if failure == "rpc" else "safe parking") in result["strictArmGateFailures"]["parallel"]


def test_current_source_descriptor_keeps_historical_maps_and_original_pins_immutable(tmp_path, monkeypatch):
    import hashlib
    import preservation
    assert Path(preservation.__file__).resolve() == WORK / "preservation.py"
    source, controls = tmp_path / "source", tmp_path / "controls"
    source.mkdir()
    controls.mkdir()
    live = source / "source.py"
    live.write_text("current bytes")
    historical = {"sourceRevision": "old", "sourceInputs": {"source.py": "retired-hash"}}
    original=json.dumps(historical).encode()
    retained=tmp_path/'original-preservation.json'
    retained.write_bytes(original)
    descriptor = controls / "preservation_inputs.json"
    descriptor.write_text(json.dumps(historical))
    current = {"sourceRevision": "current", "sourceTree": "current-tree",
        "historicalSourceRevision": "old", "historicalDescriptor": descriptor.name,
        "historicalDescriptorSha256": hashlib.sha256(descriptor.read_bytes()).hexdigest(),
        "currentSourceInputs": {"source.py": {"sha256": hashlib.sha256(live.read_bytes()).hexdigest(), "bytes": live.stat().st_size}}}
    monkeypatch.setattr(preservation, "ROOT", source)
    monkeypatch.setattr(preservation, "WORK", controls)
    arguments = {"revision": "current", "source_tree": "current-tree", "dirty": ""}
    assert preservation.require_current_source_inputs(current, historical, **arguments) == 1
    with pytest.raises(RuntimeError, match="exact clean current source"):
        preservation.require_current_source_inputs(current, historical, **(arguments | {"revision": "old"}))
    live.write_text("changed bytes")
    with pytest.raises(RuntimeError, match="pinned file identity"):
        preservation.require_current_source_inputs(current, historical, **arguments)
    descriptor.write_text("changed historical copy")
    with pytest.raises(RuntimeError, match="immutable historical descriptor"):
        preservation.require_current_source_inputs(current, historical, **arguments)
    assert retained.read_bytes() == original


@pytest.mark.parametrize("mutation", [None, "added", "deleted", "drifted"])
def test_frozen_historical_root_retains_exact_filtered_inventory(tmp_path, mutation):
    import hashlib
    import preservation
    root = tmp_path / "historical"
    root.mkdir()
    retained = root / "retained.json"
    retained.write_bytes(b"retained evidence")
    expected = {retained.name: {"sha256": hashlib.sha256(retained.read_bytes()).hexdigest(), "bytes": retained.stat().st_size}}
    for excluded in ("auth.json", "bridge-token", "sessions/entry", "__pycache__/entry.pyc"):
        path = root / excluded
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"excluded synthetic sentinel")
    (root / "helper-link").symlink_to(retained)
    preservation.require_historical_tree(root, expected)
    if mutation == "added":
        (root / "additional.json").write_bytes(b"unapproved evidence")
    elif mutation == "deleted":
        retained.unlink()
    elif mutation == "drifted":
        retained.write_bytes(b"changed evidence")
    if mutation:
        with pytest.raises(RuntimeError, match="historical root path inventory or bytes"):
            preservation.require_historical_tree(root, expected)
    else:
        preservation.require_historical_tree(root, expected)


