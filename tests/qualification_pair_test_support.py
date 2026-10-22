"""Fixed current-source control imports scoped to one test; no retained packet dependency."""
import importlib.util
import hashlib
import json
import sqlite3
import sys
import time
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


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_ledger(root, controls, *, count=1, images=0):
    """Typed synthetic receipts and an isolated ledger; no real process identities."""
    from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt
    from plotloom.codex_exec_receipt_contracts import image_arguments_hash, output_manifest_hash
    rows = []
    for index in range(count):
        row = controls.exports['successful_text'](pid=910001 + index * 2)
        current, receipt = row.current, row.receipt
        if index < images:
            outputs = [receipt.outputs[0].model_copy(update={'output_relative_path': 'delivery/outputs/fixture.png'})]
            output_hash = output_manifest_hash(outputs)
            current = CodexExecAttempt.model_validate(current.model_dump() | dict(
                domain='image', job_id='ij_' + str(current.attempt_id).replace('-', ''),
                reserved_image_outputs=1, image_budget_state='consumed', remote_tool_state='completed',
                output_hash=output_hash, remote_output_hash='4' * 64))
            image = dict(attemptId=str(current.attempt_id), sessionId=str(current.session_id),
                callId='synthetic-call', callOrdinal=1, eventId='synthetic-event',
                eventType='image_gen.generation', eventStatus='completed', promptHash='7' * 64,
                referenceHashes=[], transparentBackground=False, numLastImagesToInclude=None,
                argumentsHash=image_arguments_hash(prompt_hash='7' * 64, reference_hashes=(),
                    transparent_background=False, num_last_images_to_include=None),
                outputHash='4' * 64, outputRelativePath='delivery/outputs/fixture.png')
            receipt = CodexExecReceipt.model_validate(receipt.model_dump() | dict(expected_image_outputs=1,
                remote_tool_state='completed', output_hash=output_hash, remote_output_hash='4' * 64,
                outputs=outputs, image_evidence=[image]))
        rows.append(SimpleNamespace(current=current, receipt=receipt, worker_group_id=row.worker_group_id))
    database = root / 'private/codex-exec/supervisor.sqlite3'
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.executescript('CREATE TABLE exec_attempts(status_json,receipt_json,worker_group_id);'
            'CREATE TABLE exec_slot(domain); CREATE TABLE exec_queue(attempt_id,enabled);'
            'CREATE TABLE exec_validation_process(process_group_id);')
        connection.executemany('INSERT INTO exec_attempts VALUES(?,?,?)', [(
            row.current.model_dump_json(by_alias=True), row.receipt.model_dump_json(by_alias=True),
            row.worker_group_id) for row in rows])
    return SimpleNamespace(database=database, rows=rows,
        groups={group for row in rows for group in (row.worker_group_id, row.current.process_group_id)})


def historical_case(root, controls, monkeypatch):
    guard = controls.modules['campaign_guard']
    ledger = synthetic_ledger(root, controls, count=25, images=16)
    timeline = root / 'timeline.jsonl'
    timeline.write_text('synthetic retained material\n')
    result = dict(sourceRevision=guard.HISTORICAL_SOURCE, passed=False, quiescent=False,
        failure=None, timelineSha256=hashlib.sha256(timeline.read_bytes()).hexdigest())
    result_sha = write_json(root / 'result.json', result)
    # Bind the synthetic result locally; never point this fixture at retained operator evidence.
    monkeypatch.setattr(guard, 'HISTORICAL_RESULT_SHA', result_sha)
    write_json(root / 'post_exit_quiescence.json', dict(sourceRevision=guard.HISTORICAL_SOURCE,
        originalResultSha256=result_sha, originalResultUnchanged=result, driverAbsent=True,
        groupsPresent=[], held=0, queue=0, validators=0, allTerminalSuccess=True,
        recordedGroups=sorted(ledger.groups), driverPid=920001, attemptCount=25))
    attempts = [row.current.model_dump(mode='json', by_alias=True) for row in ledger.rows]
    write_json(root / 'latest_primary.json', dict(attempts=attempts[:24],
        run=dict(state='awaiting_review', bundle={'synthetic': True}, handoff=None)))
    write_json(root / 'latest_sidecar.json', dict(attempts=attempts[24:], run=dict(state='paused')))
    return ledger


def current_arm_case(root, controls):
    ledger = synthetic_ledger(root, controls)
    rpc = root / 'rpc_observations.jsonl'
    rpc.write_text('synthetic current RPC\n')
    result = dict(sourceRevision='b' * 40, passed=True, quiescent=True,
        cleanupOutcome='complete_success', completeSuccess=True, zeroLiveWork=True, allWorkQuiescent=True,
        rpcObservation=dict(recordsEmitted=1, recordsFinished=1, discardedRecords=0,
            activeRpcCount=0, halted=False, persistenceFailure=None, frozenJobs=1,
            recordsSha256=hashlib.sha256(rpc.read_bytes()).hexdigest()))
    write_json(root / 'result.json', result)
    return SimpleNamespace(**vars(ledger), result=result)


def preservation_case(root, controls, monkeypatch):
    preservation = controls.modules['preservation']
    source, work, bundle = (root / name for name in ('source', 'work', 'bundle'))
    for path in (source, work, bundle):
        path.mkdir(parents=True)
    write_json(bundle / 'qa-interpreter.json', dict(prefix=sys.prefix))
    original = source / 'retained/campaign'
    parked = dict(recordedGroups=[930001, 930003], parkedAllDispatchDisabled=True,
        parkedAttemptIds=['synthetic-' + str(index) for index in range(5)])
    parked_sha = write_json(original / 'post_exit_safe_parking.json', parked)
    delivery = original / 'delivery.json'
    delivery.write_text('retained synthetic asset')
    write_json(source / 'retained/baseline.json', dict(originalOfflineInputsAndProof={}, retainedEvidence={
        'post_exit_safe_parking.json': parked_sha, 'delivery.json': hashlib.sha256(delivery.read_bytes()).hexdigest()}))
    pins = dict(sourceRevision='old-source', oldCampaignRoot='retained/campaign',
        baselinePath='retained/baseline.json', pinnedFiles={
            'retained/baseline.json': hashlib.sha256((source / 'retained/baseline.json').read_bytes()).hexdigest()})
    pins_sha = write_json(work / 'preservation_inputs.json', pins)
    manifest_sha = write_json(source / 'retained/manifest.json', dict(historical_evidence=dict(files={}, roots={})))
    live = source / 'current.py'
    live.write_text('current synthetic source')
    cli = source / 'synthetic-cli'
    cli.write_text('never executed')
    write_json(work / 'current_source.json', dict(sourceRevision='new-source', sourceTree='new-tree',
        historicalSourceRevision='old-source', historicalDescriptor='preservation_inputs.json',
        historicalDescriptorSha256=pins_sha, currentSourceInputs={'current.py': hashlib.sha256(live.read_bytes()).hexdigest()},
        cli=dict(path=str(cli), sha256=hashlib.sha256(cli.read_bytes()).hexdigest()),
        qualifiedCurrentEvidence={}, historicalHashManifest='retained/manifest.json', historicalHashManifestSha256=manifest_sha))
    for name, value in (('ROOT', source), ('WORK', work), ('CONTROLS', bundle)):
        monkeypatch.setattr(preservation, name, value)
    def source_query(argv, **kwargs):
        assert kwargs == dict(cwd=source, text=True)
        return {('git', 'rev-parse', 'HEAD'): 'new-source',
            ('git', 'rev-parse', 'HEAD^{tree}'): 'new-tree',
            ('git', 'status', '--porcelain', '--untracked-files=no'): ''}[tuple(argv)]
    monkeypatch.setattr(preservation.subprocess, 'check_output', source_query)
    return SimpleNamespace(source=source, work=work, original=original, delivery=delivery, parked=parked)
