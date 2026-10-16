"""Setup-only binding and original-attempt records for the fixed production driver."""
import json
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from handoff_files import canonical, exclusive_bytes, read_owned, require
from paid_outline_state import path_identity
from pair_context import current, assert_origins
from plotloom.codex_exec_qualification_contracts import QualificationProject
from plotloom.persistence.codec import stable_hash


def register_project(runtime, project_id, role, claim):
    context = current()
    storage = runtime.app.state.project_folder_storage
    with closing(storage.projects.open(project_id)) as store:
        view = store.repository.autopilot.claim(project_id,claim)
        require(not view.checkpoints, 'actual project must register before its first original step')
        registration = QualificationProject(role=role, projectId=project_id, runId=view.id,claim=claim,
            home=path_identity(store.home),database=path_identity(store.database_path),
            manifestSha256=sha256((store.home/'project.json').read_bytes()).hexdigest(),
            policyHash=stable_hash(view.policy.model_dump(mode='json',by_alias=True)))
    runtime.bridge.exec_supervisor().register_qualification_project(registration)
    exclusive_bytes(context.work,'registration_'+role+'.json',canonical(registration.model_dump(mode='json',by_alias=True)))
    return registration


def activate(runtime):
    context = current()
    started = json.loads(read_owned(context.work/'arm-start.json'))
    ns = getattr(context.allocation,context.arm).namespace
    require(started['namespaceId']==str(ns.namespace_id), 'original arm start belongs to another namespace')
    serial = None
    if context.arm=='parallel':
        from campaign_guard import require_successful_current_arm
        require_successful_current_arm(context.campaign/'serial',expected_source=context.allocation.source.revision)
        serial=sha256(read_owned(context.campaign/'serial/result.json')).hexdigest()
    return runtime.bridge.exec_supervisor().activate_qualification(prior_serial_receipt_sha256=serial,
        started_wall_ns=started['wallNs'],started_monotonic_ns=started['monotonicNs'])


def freeze_attempt(runtime, attempt, *, settlement_only=False):
    host=runtime.bridge.exec_supervisor()
    host.freeze_qualification_attempt(attempt,settlement_only=settlement_only)
    target=current().work/('frozen-attempt-'+str(attempt.attempt_id)+'.json')
    if target.exists():
        from plotloom.codex_exec_contracts import CodexExecAttempt
        require(host._identity(CodexExecAttempt.model_validate_json(read_owned(target)))==host._identity(attempt),
            'original frozen attempt record changed')
    else:
        exclusive_bytes(current().work,target.name,canonical(attempt.model_dump(mode='json',by_alias=True)))


def settlement_deadline(runtime):
    host=runtime.bridge.exec_supervisor()
    with closing(host._connect()) as connection:
        row=connection.execute('SELECT activation_json FROM exec_qualification_arm WHERE identity=1').fetchone()
    if row[0] is None:
        started=json.loads(read_owned(current().work/'arm-start.json'))['monotonicNs']/1e9
    else:
        started=json.loads(row[0])['startedMonotonicNs']/1e9
    ns=getattr(current().allocation,current().arm).namespace
    return min(time.monotonic()+ns.max_settlement_seconds,started+ns.max_wall_seconds+ns.max_settlement_seconds)


def configure_runtime(plan):
    from isolated import RuntimeConfig
    context=current()
    arm=getattr(context.allocation,context.arm)
    assert_origins()
    return RuntimeConfig(context.work/'installation',context.source/'src/plotloom/static',
        Path(plan['cliExecutable']),context.work/'private/bridge-token',0,0,False,
        arm.namespace.limits,arm.namespace_binding_sha256)
