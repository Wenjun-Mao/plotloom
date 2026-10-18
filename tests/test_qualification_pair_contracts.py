"""Finite transport/data/origin fixtures; no operator allocation or native qualification."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from tests.cli_handoff_fixtures import ROOT,builder,current_test_qa,exclusive,private_directory
from tests.paid_outline_fixtures import paid_source, rebind_allocation  # noqa: F401
from tests.paid_outline_processes import owned_processes
from tests.codex_exec_platform_fixtures import provider_free_host_runtime
from tests.qualification_pair_test_support import pair_controls  # noqa: F401
from tests.qualification_pair_test_support import historical_case, preservation_case, current_arm_case, write_json, load

FIXTURE=ROOT/'tests/qualification_pair_schema_fixture.py'


def prepare_case(root,paid_source,owner):
    root.chmod(0o700)
    for name in ('work','bundle','phase','functional','auth-home'):
        private_directory(root/name)
    exclusive(root/'fixture-owner.json',builder.canonical(dict(syntheticEvidence=True,qualification=False)))
    qa=json.loads(current_test_qa())
    qa['projectRoot']=str(paid_source)
    exclusive(root/'qa.json',builder.canonical(qa))
    fake=("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
        "if sys.argv[1:]==['--version']:\n print('codex-cli 0.162.0-alpha.17.2');raise SystemExit(0)\n"
        "if sys.argv[-2:]==['login','status']:raise SystemExit(0)\n"
        "Path("+repr(str(root/'forbidden-native'))+").write_text('unexpected exec');raise SystemExit(19)\n")
    exclusive(root/'fake-codex',fake.encode())
    (root/'fake-codex').chmod(0o700)
    exclusive(root/'functional/result.json',builder.canonical(dict(syntheticEvidence=True,qualification=False)))
    provider_free_host_runtime(root/'provider-free-host',paid_source)
    env=os.environ|dict(CODEX_HOME=str(root/'auth-home'),PYTHONDONTWRITEBYTECODE='1')
    result=owner.run([sys.executable,'-B',str(FIXTURE),'prepare','--root',str(root),'--source',str(paid_source)],
        env=env,capture_output=True,text=True,timeout=45)
    exclusive(root/'receipts/preparation-stdout.log',result.stdout.encode())
    exclusive(root/'receipts/preparation-stderr.log',result.stderr.encode())
    assert result.returncode==0,result.stdout+result.stderr
    return dict(root=root,source=paid_source,env=env,allocation=json.loads((root/'allocation.json').read_bytes()))


@pytest.fixture(scope='module')
def pair_schema(tmp_path_factory,paid_source):
    root=tmp_path_factory.mktemp('pair-schema-unit').resolve()
    with owned_processes(root) as owner:
        return prepare_case(root,paid_source,owner)


def test_pair_allocation_has_acyclic_code_pin_and_no_project_placeholders(pair_schema):
    case=pair_schema
    root=case['root']
    allocation=case['allocation']
    code=json.loads((root/'bundle/pair-controls.json').read_bytes())
    controls=json.loads((root/'bundle/source-controls.json').read_bytes())
    assert not {'pair-allocation.json','pair-controls.json','source-controls.json'} & set(code['files'])
    assert controls['files']['pair-controls.json']==builder.digest((root/'bundle/pair-controls.json').read_bytes())
    for arm in ('serial','parallel'):
        ns=allocation[arm]['namespace']
        assert ns['controlsSha256']==controls['files']['pair-controls.json']
        assert not {'attempt','projectId','runId'} & set(ns)
        import sqlite3
        with sqlite3.connect(ns['database']['path']) as connection:
            assert connection.execute('SELECT count(*) FROM exec_attempts').fetchone()[0]==0
        assert list(Path(ns['outputsRoot']['path']).iterdir())==[]
    assert not (root/'forbidden-native').exists()
    assert set(path.name for path in (root/'phase').iterdir())=={'phase.json'}


@pytest.mark.parametrize('action,success',[('inspect',True),('shadow',False)])
def test_fixed_pair_context_accepts_verified_roots_and_refuses_shadowed_controls(pair_schema,tmp_path,action,success):
    case=pair_schema
    tmp_path.chmod(0o700)
    (tmp_path/'receipts').mkdir(mode=0o700)
    with owned_processes(tmp_path) as owner:
        result=owner.run([sys.executable,'-B',str(FIXTURE),action,'--root',str(case['root']),'--source',str(case['source'])],
            env=case['env'],capture_output=True,text=True,timeout=20)
    assert (result.returncode==0) is success,result.stdout+result.stderr
    if not success:assert 'shadowed' in result.stderr


def test_actual_node_helper_recognizes_finite_pair_without_intent_or_native_call(pair_schema,tmp_path):
    node=shutil.which('node')
    assert node
    tmp_path.chmod(0o700)
    (tmp_path/'receipts').mkdir(mode=0o700)
    with owned_processes(tmp_path) as owner:
        result=owner.run([node,str(ROOT/'tests/qualification_pair_capability_fixture.mjs'),str(pair_schema['root'])],
            capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    reply=json.loads(result.stdout)
    assert reply['syntheticEvidence'] and reply['qualification'] is False and reply['reply']['status']=='OK'
    assert set(path.name for path in (pair_schema['root']/'phase').iterdir())=={'phase.json'}
    assert not (pair_schema['root']/'forbidden-native').exists()


@pytest.mark.parametrize('fault,boundary,message',[
    ('qa','node','pair finite authority differs'),
    ('limit','registered','maxImageOutputs'),
    ('physical','namespace','namespace ledger physical identity changed'),
    ('input','inspect','pair frozen input bytes differ'),
])
def test_rebound_data_refuses_at_its_owning_boundary(tmp_path,paid_source,fault,boundary,message):
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as owner:
        case=prepare_case(tmp_path,paid_source,owner)
        def change(value):
            if fault=='qa':value['validatorRuntime']['qaPinSha256']='0'*64
            if fault=='limit':value['serial']['namespace']['maxImageOutputs']=33
            if fault=='physical':
                ns=value['serial']['namespace']
                ns['database']['inode']+=1
                raw=builder.canonical(ns)
                (Path(ns['privateRoot']['path'])/'namespace-binding.json').write_bytes(raw)
                value['serial']['namespaceBindingSha256']=builder.digest(raw)
        if fault=='input':
            Path(case['allocation']['inputs'][0]['path']).write_bytes(b'{}\n')
        else:rebind_allocation(case,change,filename='pair-allocation.json')
        command=([shutil.which('node'),str(ROOT/'tests/qualification_pair_capability_fixture.mjs'),str(tmp_path)]
            if boundary=='node' else [sys.executable,'-B',str(FIXTURE),boundary,'--root',str(tmp_path),'--source',str(paid_source)])
        result=owner.run(command,env=case['env'],capture_output=True,text=True,timeout=20)
        assert result.returncode!=0,result.stdout+result.stderr
        assert message in result.stdout+result.stderr
        assert set(path.name for path in (tmp_path/'phase').iterdir())=={'phase.json'}
        assert not (tmp_path/'forbidden-native').exists()
        assert all(list(Path(case['allocation'][arm]['namespace']['outputsRoot']['path']).iterdir())==[]
            for arm in ('serial','parallel'))


def test_historical_preservation_never_probes_old_numeric_ids(pair_controls, tmp_path, monkeypatch):
    case = preservation_case(tmp_path, pair_controls, monkeypatch)
    probes = []
    monkeypatch.setattr(os, 'kill', lambda *args: probes.append(('pid', args)))
    monkeypatch.setattr(os, 'killpg', lambda *args: probes.append(('group', args)))
    before = {path: path.read_bytes() for path in case.original.rglob('*') if path.is_file()}
    result = pair_controls.modules['preservation'].require_preserved_inputs()
    assert probes == []  # Synthetic old numbers would appear present if sampled.
    assert result['oldParkedAttempts'] == case.parked['parkedAttemptIds']
    assert result['historicalLiveness'] == 'UNKNOWN'
    assert all(path.read_bytes() == raw for path, raw in before.items())


def test_historical_material_never_probes_old_numeric_ids(pair_controls, tmp_path, monkeypatch):
    case = historical_case(tmp_path / 'historical', pair_controls, monkeypatch)
    probes = []
    monkeypatch.setattr(os, 'kill', lambda *args: probes.append(('pid', args)))
    monkeypatch.setattr(os, 'killpg', lambda *args: probes.append(('group', args)))
    before = case.database.read_bytes()
    result = pair_controls.modules['campaign_guard'].require_historical_material(tmp_path / 'historical')
    assert probes == []
    assert result['historicalLiveness'] == 'UNKNOWN' and 'currentOriginalWork' not in result
    assert result['retainedOriginalWork']['attempts'] == 25
    assert 'groupsAbsent' not in result['retainedOriginalWork']
    assert result['historicalInProcessPassed'] is False and result['historicalInProcessQuiescent'] is False
    assert result['newSourceQualification'] is False and case.database.read_bytes() == before


@pytest.mark.parametrize('fault', ['delivery', 'parking', 'baseline', 'manifest'])
def test_historical_preservation_still_refuses_corruption(pair_controls, tmp_path, monkeypatch, fault):
    case = preservation_case(tmp_path, pair_controls, monkeypatch)
    paths = dict(delivery=case.delivery, parking=case.original / 'post_exit_safe_parking.json',
        baseline=case.source / 'retained/baseline.json', manifest=case.source / 'retained/manifest.json')
    paths[fault].write_text('{}')
    monkeypatch.setattr(os, 'kill', lambda *_args: pytest.fail('historical PID probe'))
    monkeypatch.setattr(os, 'killpg', lambda *_args: pytest.fail('historical group probe'))
    with pytest.raises(RuntimeError, match='changed'):
        pair_controls.modules['preservation'].require_preserved_inputs()


@pytest.mark.parametrize('fault', ['dispatch-enabled', 'attempt-count'])
def test_historical_parking_facts_still_refuse_under_rebound_synthetic_pins(pair_controls, tmp_path, monkeypatch, fault):
    case = preservation_case(tmp_path, pair_controls, monkeypatch)
    case.parked['parkedAllDispatchDisabled'] = fault != 'dispatch-enabled'
    if fault == 'attempt-count':
        case.parked['parkedAttemptIds'].pop()
    parked_sha = write_json(case.original / 'post_exit_safe_parking.json', case.parked)
    baseline_path = case.source / 'retained/baseline.json'
    baseline = json.loads(baseline_path.read_bytes())
    baseline['retainedEvidence']['post_exit_safe_parking.json'] = parked_sha
    pins = json.loads((case.work / 'preservation_inputs.json').read_bytes())
    pins['pinnedFiles']['retained/baseline.json'] = write_json(baseline_path, baseline)
    current = json.loads((case.work / 'current_source.json').read_bytes())
    current['historicalDescriptorSha256'] = write_json(case.work / 'preservation_inputs.json', pins)
    write_json(case.work / 'current_source.json', current)
    monkeypatch.setattr(os, 'killpg', lambda *_args: pytest.fail('historical group probe'))
    with pytest.raises(RuntimeError, match='original five-job safe parking proof differs'):
        pair_controls.modules['preservation'].require_preserved_inputs()


@pytest.mark.parametrize('fault', ['result', 'timeline', 'post', 'material', 'slot', 'queue', 'validator',
                                  'nonterminal', 'unsuccessful', 'missing-receipt', 'mismatched-receipt'])
def test_historical_material_still_refuses_corruption(pair_controls, tmp_path, monkeypatch, fault):
    root = tmp_path / 'historical'
    case = historical_case(root, pair_controls, monkeypatch)
    corrupt_guard_case(root, case, fault)
    monkeypatch.setattr(os, 'kill', lambda *_args: pytest.fail('historical PID probe'))
    monkeypatch.setattr(os, 'killpg', lambda *_args: pytest.fail('historical group probe'))
    with pytest.raises(ValueError if fault == 'mismatched-receipt' else RuntimeError):
        pair_controls.modules['campaign_guard'].require_historical_material(root)


def corrupt_guard_case(root, case, fault):
    import sqlite3
    if fault in {'result', 'timeline'}:
        (root / ('result.json' if fault == 'result' else 'timeline.jsonl')).write_text('{}')
    elif fault in {'post', 'material'}:
        name = 'post_exit_quiescence.json' if fault == 'post' else 'latest_primary.json'
        value = json.loads((root / name).read_bytes())
        if fault == 'post':
            value['attemptCount'] = 24
        else:
            value['run']['state'] = 'running'
        write_json(root / name, value)
    else:
        with sqlite3.connect(case.database) as db:
            if fault in {'slot', 'queue', 'validator'}:
                table, values = {'slot': ('exec_slot', ('text',)), 'queue': ('exec_queue', ('synthetic', 0)),
                    'validator': ('exec_validation_process', (940001,))}[fault]
                db.execute('INSERT INTO ' + table + ' VALUES(' + ','.join('?' * len(values)) + ')', values)
            elif fault in {'missing-receipt', 'mismatched-receipt'}:
                receipt = case.rows[0].receipt.model_dump(mode='json', by_alias=True)
                receipt['requestHash'] = '9' * 64
                db.execute('UPDATE exec_attempts SET receipt_json=? WHERE rowid=1',
                    (None if fault == 'missing-receipt' else json.dumps(receipt),))
            else:
                value = case.rows[0].current.model_dump(mode='json', by_alias=True)
                if fault == 'nonterminal':
                    value.update(state='outcome_unknown', terminalResult=None, evidenceHash=None,
                        remoteToolState=None, outputHash=None, remoteOutputHash=None, processExitCode=None,
                        imageBudgetState='reserved' if value['domain'] == 'image' else 'none')
                else:
                    value.update(state='failed', terminalResult='failure', processExitCode=1)
                db.execute('UPDATE exec_attempts SET status_json=? WHERE rowid=1', (json.dumps(value),))


@pytest.mark.parametrize('fault', [None, 'present', 'unknown', 'slot', 'queue', 'validator', 'nonterminal',
                                  'unsuccessful', 'missing-receipt', 'mismatched-receipt', 'frozen-jobs'])
def test_current_arm_retains_real_ledger_receipt_and_absence_guards(pair_controls, tmp_path, monkeypatch, fault):
    root = tmp_path / 'serial'
    case = current_arm_case(root, pair_controls)
    probes = []
    def observed(group, signal):
        assert group in case.groups and signal == 0
        probes.append(group)
        if fault == 'present':
            return
        if fault == 'unknown':
            raise PermissionError('synthetic unknown ownership')
        raise ProcessLookupError
    monkeypatch.setattr(os, 'killpg', observed)
    monkeypatch.setattr(os, 'kill', lambda *_args: pytest.fail('unexpected PID probe'))
    if fault == 'frozen-jobs':
        case.result['rpcObservation']['frozenJobs'] = 2
        write_json(root / 'result.json', case.result)
    elif fault not in {None, 'present', 'unknown'}:
        corrupt_guard_case(root, case, fault)
    before = case.database.read_bytes()
    guard = pair_controls.modules['campaign_guard']
    if fault is None:
        result = guard.require_successful_current_arm(root, expected_source=case.result['sourceRevision'])
        assert set(probes) == case.groups and result['groupsAbsent'] == len(case.groups)
    else:
        with pytest.raises((RuntimeError, ValueError)):
            guard.require_successful_current_arm(root, expected_source=case.result['sourceRevision'])
    assert case.database.read_bytes() == before


def test_failed_serial_still_refuses_parallel_order(pair_controls, tmp_path, monkeypatch):
    historical_case(tmp_path / 'historical', pair_controls, monkeypatch)
    campaign = tmp_path / 'campaign'
    case = current_arm_case(campaign / 'serial', pair_controls)
    case.result['passed'] = False
    write_json(campaign / 'serial/result.json', case.result)
    write_json(campaign / 'campaign_intent.json', dict(sourceRevision=case.result['sourceRevision'], sealedPlanSha256='8' * 64))
    monkeypatch.setattr(os, 'kill', lambda *_args: pytest.fail('historical PID probe'))
    monkeypatch.setattr(os, 'killpg', lambda *_args: pytest.fail('failed serial must refuse before live probes'))
    plan = dict(arm='parallel', sourceRevision=case.result['sourceRevision'], sealedPlanSha256='8' * 64,
        functionalProofRoot=str(tmp_path / 'historical'))
    with pytest.raises(RuntimeError, match='new arm has not established success'):
        pair_controls.modules['campaign_guard'].require_execution_order(campaign / 'parallel', plan)


def test_campaign_preflight_uses_historical_material_without_old_probes(pair_controls, tmp_path, monkeypatch):
    from types import SimpleNamespace as Namespace
    import hashlib
    history = tmp_path / 'historical'
    historical_case(history, pair_controls, monkeypatch)
    campaign = tmp_path / 'campaign'
    profiles = {arm: dict(maxProcesses=total, maxTextProcesses=text, maxImageProcesses=image, maxQueuedJobs=4)
        for arm, total, text, image in [('serial', 1, 1, 1), ('parallel', 4, 2, 2)]}
    plans = {arm: dict(profile=profile, profileHash=arm + '-synthetic', functionalProofRoot=str(history))
        for arm, profile in profiles.items()}
    prepared_sha = write_json(campaign / 'prepared_inputs.json', dict(arms=plans))
    sealed = dict(sourceRevision='b' * 40, order=['serial', 'parallel'], totalDispatchEnvelope=dict(text=18, image=64),
        preparedInputsSha256=prepared_sha, functionalResultSha256=hashlib.sha256((history / 'result.json').read_bytes()).hexdigest())
    sealed_sha = write_json(campaign / 'plan.json', sealed)
    allocation = Namespace(source=Namespace(revision=sealed['sourceRevision']))
    for arm, profile in profiles.items():
        write_json(campaign / arm / 'plan.json', plans[arm] | dict(sealedPlanSha256=sealed_sha))
        bound = Namespace(profile_hash=plans[arm]['profileHash'], model_dump=lambda *, mode, by_alias, value=profile: value)
        setattr(allocation, arm, Namespace(namespace=Namespace(profile=bound)))
    for name in ('assert_control_bytes', 'assert_origins'):
        monkeypatch.setattr(pair_controls.context, name,
            lambda: pytest.fail('unit source fence must be supplied explicitly'), raising=False)
    preflight = load(monkeypatch, 'pair_preflight', ROOT / 'scripts/autopilot/handoff/pair_preflight.py')
    source_checks = []
    # This unit supplies the admitted source fence; it never runs operator preflight or runtime inspection.
    monkeypatch.setattr(preflight, '_source', lambda: source_checks.append('admitted synthetic source'))
    monkeypatch.setattr(preflight, 'current', lambda: Namespace(campaign=campaign, allocation=allocation))
    monkeypatch.setattr(os, 'kill', lambda *_args: pytest.fail('historical PID probe'))
    monkeypatch.setattr(os, 'killpg', lambda *_args: pytest.fail('historical group probe'))
    assert preflight.preflight_campaign() == sealed and len(source_checks) == 1


def test_pair_original_handle_attendance_before_deliberately_held_callback(tmp_path,paid_source):
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as owner:
        case=prepare_case(tmp_path,paid_source,owner)
        result=owner.run([shutil.which('node'),str(ROOT/'tests/paid_outline_capsule_fixture.mjs'),str(tmp_path),
            sys.executable,str(ROOT/'tests/paid_outline_native_fixture.py'),str(paid_source),'pair-transport'],
            env=case['env'],capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stdout+result.stderr
        report=json.loads((tmp_path/'capsule-result-pair-transport.json').read_bytes())
        assert report['outcome']['status']=='RECEIVER_ACCEPTED'
        assert report['actualFixtureChildTerminal']['code']==1
        callback=json.loads((tmp_path/'phase/synthetic-pair-callback.json').read_bytes())
        assert callback==dict(syntheticEvidence=True,qualification=False,nativeExecHandle=42,
            generationDispatches=0,heldBeforeProjects=True)
        assert not (tmp_path/'forbidden-native').exists()
        assert not (tmp_path/'work/campaign_intent.json').exists()


@pytest.mark.parametrize('arm',['serial','parallel'])
@pytest.mark.parametrize('execute',[False,True])
def test_sealed_arm_entry_uses_real_qa_source_and_stops_at_driver_boundary(tmp_path,paid_source,arm,execute):
    import sqlite3
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as owner:
        case=prepare_case(tmp_path,paid_source,owner)
        command=[sys.executable,'-B',str(FIXTURE),'arm-entry','--root',str(tmp_path),
            '--source',str(paid_source),'--arm',arm]
        if execute:command.append('--execute')
        result=owner.run(command,env=case['env'],capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        report=json.loads((tmp_path/'receipts/arm-entry.json').read_bytes())
        assert report['source']==str(paid_source)
        assert report['work']==str(tmp_path/'work'/arm) and report['arm']==arm
        assert report['entryArgv']==[str(tmp_path/'bundle/pair_arm_receiver.py'),'--arm',arm]+(['--execute'] if execute else [])
        assert report['driverArgv']==(['--execute'] if execute else [])
        assert report['qa']['role']=='inner' and 'projectRoot' not in report['qa']
        assert report['downstreamMainHeld'] and report['qualification'] is False
        assert report['projectsCreated']==report['generationDispatches']==0
        assert report['armStartExists'] is execute
        start=tmp_path/'work'/arm/'arm-start.json'
        if execute:
            original=start.read_bytes()
            value=json.loads(original)
            assert set(value)=={'namespaceId','wallNs','monotonicNs'}
            assert value['namespaceId']==case['allocation'][arm]['namespace']['namespaceId']
            assert value['wallNs']>0 and value['monotonicNs']>0
            boundary=(tmp_path/'receipts/arm-entry.json').read_bytes()
            duplicate=owner.run(command,env=case['env'],capture_output=True,text=True,timeout=30)
            assert duplicate.returncode!=0
            assert 'restart cannot advance or resend' in duplicate.stderr
            assert start.read_bytes()==original
            assert (tmp_path/'receipts/arm-entry.json').read_bytes()==boundary
        for name in ('serial','parallel'):
            ns=case['allocation'][name]['namespace']
            assert list(Path(ns['outputsRoot']['path']).iterdir())==[]
            with sqlite3.connect(f"file:{ns['database']['path']}?mode=ro",uri=True) as db:
                assert all(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
                    for table in ('exec_attempts','exec_slot','exec_queue','exec_validation_process'))
                assert db.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'exec_qualification_%'").fetchone()[0]==0
            with sqlite3.connect(f"file:{ns['applicationDatabase']['path']}?mode=ro",uri=True) as db:
                assert db.execute('SELECT count(*) FROM application_project_create_requests').fetchone()[0]==0
            assert not (tmp_path/'work'/name/'launch_intent.json').exists()
            if name!=arm:assert not (tmp_path/'work'/name/'arm-start.json').exists()
        assert not (tmp_path/'work/campaign_intent.json').exists()
        assert not (tmp_path/'forbidden-native').exists()
