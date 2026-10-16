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
