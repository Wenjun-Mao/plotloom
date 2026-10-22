"""Synthetic races and corruption at real finite SQLite/grant/worker boundaries."""
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_errors import CodexExecSupervisorError
from plotloom.codex_exec_contracts import CodexExecAttempt,transition_exec_attempt
from tests.services.creator_workbench.qualification_fixtures import finite  # noqa: F401


def admitted(case):
    case.host.freeze_qualification_attempt(case.attempt)
    intent=transition_exec_attempt(case.attempt,state='spawn_intent')
    case.host.admit(intent)
    return intent


def fake_success(case,intent):
    """Explicit fake receipt fixture, never evidence of validator/provider execution."""
    from tests.autopilot_fake_exec_host import FakeCodexExecHost
    from tests.autopilot_controller_fixtures import candidate
    fake=FakeCodexExecHost(case.storage,SimpleNamespace(codex_exec_profile=case.host.profile),candidate_factory=candidate)
    with closing(case.storage.projects.open(str(intent.project_id))) as store:
        return fake.complete(store,fake.request(store,intent),intent)


@pytest.mark.parametrize('stop',['halt','expiry','insufficient_time'])
def test_populated_enabled_queue_cannot_grant_after_original_stop(finite,monkeypatch,stop):
    host=finite.host
    host.freeze_qualification_attempt(finite.attempt)
    intent=transition_exec_attempt(finite.attempt,state='spawn_intent')
    # Hold exactly the initial grant to expose the real delayed-grant window.
    with monkeypatch.context() as initial:
        initial.setattr(host,'_grant_one_in_transaction',lambda _connection:None)
        assert host.admit(intent).state=='queued'
    if stop=='halt':
        host.halt_qualification('test_stop_after_admission')
    else:
        import codex_exec_supervisor_qualification_admission as owner
        elapsed=5401 if stop=='expiry' else 3001
        monkeypatch.setattr(owner.time,'time_ns',lambda:finite.activation.started_wall_ns+elapsed*10**9)
        monkeypatch.setattr(owner.time,'monotonic_ns',lambda:finite.activation.started_monotonic_ns+elapsed*10**9)
    assert host._drain_queue() is None
    assert finite.starts==[]
    with closing(host._connect()) as connection:
        assert connection.execute('SELECT enabled FROM exec_queue').fetchone()[0]==1
        assert connection.execute('SELECT count(*) FROM exec_slot').fetchone()[0]==0
        assert connection.execute('SELECT halt_reason FROM exec_qualification_arm').fetchone()[0]
    assert host.suspend(intent).dispatch_enabled is False
    with pytest.raises(CodexExecSupervisorError,match='held'):
        host.resume(intent)


def test_unknown_halt_is_sticky_after_fake_late_successful_reconciliation(finite):
    host=finite.host
    intent=admitted(finite)
    host._store(transition_exec_attempt(intent,state='outcome_unknown'))
    late=fake_success(finite,intent)
    host._store(late.attempt,receipt=late.receipt)
    assert host.status(intent.attempt_id).state=='completed'
    assert host._drain_queue() is None
    with closing(host._connect()) as connection:
        assert connection.execute('SELECT halt_reason FROM exec_qualification_arm').fetchone()[0]=='attempt_outcome_unknown'


@pytest.mark.parametrize('mutation',['project','job','home','private','job_path','admitted_state','receipt','slot_domain'])
def test_finite_ledger_mutations_refuse_reconstruction_without_repair(finite,mutation):
    host=finite.host
    intent=admitted(finite)
    if mutation=='receipt':
        late=fake_success(finite,intent)
        host._store(late.attempt,receipt=late.receipt)
    with closing(sqlite3.connect(host.database)) as connection:
        if mutation=='project': connection.execute('UPDATE exec_attempts SET project_id=?',(str(uuid4()),))
        elif mutation=='job': connection.execute("UPDATE exec_attempts SET job_id='ch_foreign'")
        elif mutation=='home': connection.execute("UPDATE exec_attempts SET project_home='/foreign'")
        elif mutation=='private': connection.execute("UPDATE exec_attempts SET private_dir='/foreign'")
        elif mutation=='job_path': connection.execute("UPDATE exec_attempts SET job_root='/foreign'")
        elif mutation=='admitted_state': connection.execute("UPDATE exec_attempts SET attempt_json=json_set(attempt_json,'$.state','reserved')")
        elif mutation=='receipt':
            wrong=late.receipt.model_copy(update={'attempt_id':uuid4()})
            connection.execute('UPDATE exec_attempts SET receipt_json=?',(wrong.model_dump_json(by_alias=True),))
        else: connection.execute("UPDATE exec_slot SET domain='image'")
        connection.commit()
    before=host.database.read_bytes()
    with pytest.raises((ValueError,CodexExecSupervisorError)):
        CodexExecSupervisor(host.executable,**finite.kwargs)
    assert host.database.read_bytes()==before


def test_finite_cancel_tombstone_keeps_original_integrity_rules(finite):
    finite.host.freeze_qualification_attempt(finite.attempt)
    assert finite.host.cancel(finite.attempt).state=='settled'
    restarted=CodexExecSupervisor(finite.host.executable,**finite.kwargs)
    assert restarted.status(finite.attempt.attempt_id).attempt.terminal_result=='not_started'
    with closing(sqlite3.connect(restarted.database)) as connection:
        connection.execute("UPDATE exec_attempts SET status_json=json_set(status_json,'$.evidenceHash',?)",('d'*64,))
        connection.commit()
    with pytest.raises(CodexExecSupervisorError,match='tombstone'):
        CodexExecSupervisor(restarted.executable,**finite.kwargs)


def _image(base,outputs):
    return CodexExecAttempt.model_validate(base.model_dump(mode='python')|dict(attempt_id=uuid4(),
        job_id='ij_'+uuid4().hex[:24],operation_key='image:'+uuid4().hex,domain='image',
        validation_plan_hash=None,reserved_image_outputs=outputs,image_budget_state='reserved',state='spawn_intent'))


def test_concurrent_final_output_ceiling_counts_disabled_authorizations_and_duplicates(finite,monkeypatch):
    """Synthetic image reservations/packages isolate the real atomic budget owner."""
    host=finite.host
    with closing(host._connect()) as connection:
        for outputs in (4,4,4,4,4,4,4,3):
            item=_image(finite.attempt,outputs)
            connection.execute('INSERT INTO exec_qualification_attempt VALUES(?,?,?,?,?)',
                (str(item.attempt_id),str(item.project_id),item.job_id,item.operation_key,item.model_dump_json(by_alias=True)))
    other=CodexExecSupervisor(host.executable,**finite.kwargs)
    original_owner=host._qualification_owner_snapshot
    for owner in (host,other):
        # Real run/claim/policy are checked; synthetic image-job rows are this
        # budget test's seam, not a claim of prepared image package acceptance.
        monkeypatch.setattr(owner,'_qualification_owner_snapshot',lambda project,_attempt,**_options:original_owner(project,finite.attempt))
        def resolve(attempt):
            home=Path(finite.registration.home.path)
            job=home/'runs'/('synthetic__'+attempt.job_id)/'jobs'/attempt.job_id
            (job/'delivery').mkdir(parents=True,mode=0o700,exist_ok=True)
            return home,job
        monkeypatch.setattr(owner,'_resolve_job',resolve)
        monkeypatch.setattr(owner,'_verify_attempt_package',lambda *_args:None)
        monkeypatch.setattr(owner,'_start_worker',lambda _identity:pytest.fail('disabled budget fixture started a worker'))
    candidates=[_image(finite.attempt,1),_image(finite.attempt,1)]
    transaction_facts=[]
    def observe_admission(original):
        def observed_admission(connection,attempt,**options):
            transaction_facts.append(connection.in_transaction)
            return original(connection,attempt,**options)
        return observed_admission
    # Either independent host may win. Observe both owners without choosing
    # their scheduling order or weakening the transaction assertion.
    for owner in (host,other):
        monkeypatch.setattr(owner,'_qualification_admission',observe_admission(owner._qualification_admission))
    def authorize(pair):
        owner,attempt=pair
        try:
            owner.freeze_qualification_attempt(attempt)
            return owner._admit_with_authorization(attempt,enabled=False)
        except CodexExecSupervisorError:
            return None
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(authorize,zip((host,other),candidates)))
    accepted=[(attempt,result) for attempt,result in zip(candidates,results) if result is not None]
    assert len(accepted)==1
    winner,status=accepted[0]
    assert status.dispatch_enabled is False
    assert host._admit_with_authorization(winner,enabled=False)==status
    assert transaction_facts and all(transaction_facts)
    with closing(host._connect()) as connection:
        attempts=[CodexExecAttempt.model_validate_json(row[0]) for row in connection.execute('SELECT attempt_json FROM exec_qualification_attempt')]
        assert len(attempts)==9 and sum(item.reserved_image_outputs for item in attempts)==32
        assert connection.execute('SELECT count(*) FROM exec_attempts').fetchone()[0]==1
        assert connection.execute('SELECT sum(enabled) FROM exec_queue').fetchone()[0]==0


def test_real_fixture_worker_reconstructs_binding_and_halts_after_grant_before_native_popen(finite,tmp_path):
    from tests.paid_outline_processes import owned_processes
    intent=admitted(finite)
    finite.host.halt_qualification('test_stop_between_grant_and_native_spawn')
    ownership=tmp_path/'worker-ownership'
    ownership.mkdir(mode=0o700)
    (ownership/'receipts').mkdir(mode=0o700)
    command=[sys.executable,'-B',str(finite.host.source_root/'services/creator_workbench/codex_exec_supervisor_worker.py'),
        '--attempt-id',str(intent.attempt_id),'--executable',str(finite.host.executable),
        '--source-root',str(finite.host.source_root),'--outputs-root',str(finite.host.outputs_root),
        '--private-root',str(finite.host.private_root),'--namespace-binding-sha256',finite.kwargs['namespace_binding_sha256']]
    root=Path(__file__).resolve().parents[3]
    program=("import subprocess,sys;sys.path.insert(0,"+repr(str(root))+");"
        "from tests.paid_outline_processes import install_spawn_journal;install_spawn_journal("+repr(str(ownership))+");"
        "subprocess.run("+repr(command)+",check=True,start_new_session=True)")
    with owned_processes(ownership) as owner:
        result=owner.run([sys.executable,'-B','-c',program],env=finite.host._worker_environment(),capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
    assert not finite.native_marker.exists()
    with closing(finite.host._connect()) as connection:
        row=connection.execute('SELECT * FROM exec_attempts').fetchone()
        current=CodexExecAttempt.model_validate_json(row['status_json'])
        assert current.state=='queued' and current.process_id is None and row['worker_pid'] is None
        assert connection.execute('SELECT enabled FROM exec_queue').fetchone()[0]==0
        assert connection.execute('SELECT count(*) FROM exec_slot').fetchone()[0]==0
        assert connection.execute('SELECT binding_sha256 FROM exec_namespace_configuration').fetchone()[0]==finite.kwargs['namespace_binding_sha256']


def test_worker_entry_omitted_pin_cannot_reconstruct_unbound(finite,monkeypatch):
    import codex_exec_supervisor_worker
    monkeypatch.setattr(CodexExecSupervisor,'run_worker',lambda *_args:pytest.fail('unbound reconstructed worker advanced'))
    with pytest.raises(CodexExecSupervisorError,match='pin is required'):
        codex_exec_supervisor_worker.main(['--attempt-id',str(finite.attempt.attempt_id),'--executable',str(finite.host.executable),
            '--source-root',str(finite.host.source_root),'--outputs-root',str(finite.host.outputs_root),
            '--private-root',str(finite.host.private_root)])


@pytest.mark.parametrize('mutation',['activation_row','activation_null','activation_table','binding_table','role_column','authorization_column'])
def test_finite_metadata_loss_cannot_reset_activation_or_registration(finite,mutation):
    finite.host.freeze_qualification_attempt(finite.attempt)
    with closing(sqlite3.connect(finite.host.database)) as connection:
        if mutation=='activation_row':connection.execute('DELETE FROM exec_qualification_arm')
        elif mutation=='activation_null':connection.execute('UPDATE exec_qualification_arm SET activation_json=NULL')
        elif mutation=='activation_table':connection.execute('DROP TABLE exec_qualification_arm')
        elif mutation=='binding_table':connection.execute('DROP TABLE exec_namespace_configuration')
        elif mutation=='role_column':connection.execute('UPDATE exec_qualification_project SET project_id=?',(str(uuid4()),))
        else:connection.execute("UPDATE exec_qualification_attempt SET job_id='ch_foreign'")
        connection.commit()
    before=finite.host.database.read_bytes()
    with pytest.raises(CodexExecSupervisorError):
        CodexExecSupervisor(finite.host.executable,**finite.kwargs)
    assert finite.host.database.read_bytes()==before
    if mutation=='activation_null':
        with pytest.raises(CodexExecSupervisorError,match='activation'):
            finite.host.activate_qualification(prior_serial_receipt_sha256='c'*64)
        assert finite.host.database.read_bytes()==before


@pytest.mark.parametrize('location',['envelope','attempt','registration_route'])
def test_existing_rpc_cannot_configure_role_or_namespace(finite,monkeypatch,location):
    from io import BytesIO
    from host_bridge import handler_for
    host=finite.host
    bridge=SimpleNamespace(exec_supervisor=lambda:host)
    handler=object.__new__(handler_for(bridge))
    handler.path='/qualification-register' if location=='registration_route' else '/exec-admit'
    body={'attempt':transition_exec_attempt(finite.attempt,state='spawn_intent').model_dump(mode='json',by_alias=True)}
    if location=='envelope':body['registration']={'role':'primary'}
    else:body['attempt']['role']='primary'
    raw=json.dumps(body).encode()
    handler.headers={'Content-Length':str(len(raw))}
    handler.connection=SimpleNamespace(settimeout=lambda _seconds:None)
    handler.rfile=BytesIO(raw)
    handler.authenticated=lambda:True
    replies=[]
    handler.reply=lambda code,payload:replies.append((code,payload))
    monkeypatch.setattr(host,'register_qualification_project',lambda *_args:pytest.fail('RPC configured role'))
    handler.do_POST()
    assert replies[0][0]==(404 if location=='registration_route' else 409)
    with closing(host._connect()) as connection:
        assert connection.execute('SELECT count(*) FROM exec_attempts').fetchone()[0]==0
        assert connection.execute('SELECT count(*) FROM exec_qualification_project').fetchone()[0]==1
