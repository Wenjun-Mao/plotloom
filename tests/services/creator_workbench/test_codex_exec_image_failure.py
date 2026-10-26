"""Real supervisor decisions with a simulated CLI; no provider or host-process probes."""
import io
import json
import os
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from codex_exec_supervisor_test_support import _insert_attempt_row, _write_fake_cli

from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReadiness
from plotloom.codex_exec_runtime import package_tree_hash

NATIVE_PID = 54321


def _execute_image(supervisor, tmp_path, monkeypatch, mode, *, reconnect=False):
    import codex_exec_supervisor_process as process_owner

    import codex_exec_terminal_inspection as telemetry_owner

    profile = _write_fake_cli(supervisor, 'raise SystemExit(0)\n')
    monkeypatch.setattr(supervisor, 'profile', lambda: profile)
    monkeypatch.setattr(supervisor, 'codex_exec_readiness', lambda: CodexExecReadiness(state='ready'))
    home = supervisor.outputs_root / 'synthetic-image-project'
    job_id = 'ij_' + uuid4().hex
    job = home / 'runs' / ('synthetic__' + job_id) / 'jobs' / job_id
    (job / 'package').mkdir(parents=True)
    (job / 'delivery').mkdir()
    request = {'packageVersion': 8, 'executorBackend': 'codex_exec', 'executionContract': 'codex_exec.v1',
               'jobId': job_id, 'requestHash': 'a' * 64, 'references': []}
    import subprocess
    from hashlib import sha256
    request['specialistPreflight'] = {
        'version': 'p1.5-pin.v2', 'skillVersion': 'plotloom-image-specialist.v4',
        'executionContract': 'codex_exec.v1',
        'codeRevision': subprocess.run(['git', '-C', str(supervisor.source_root), 'rev-parse', 'HEAD'],
            check=True, capture_output=True, text=True).stdout.strip(),
        'skillHash': sha256((supervisor.source_root / '.agents/skills/plotloom-image-specialist/SKILL.md').read_bytes()).hexdigest(),
    }
    same_bytes = mode.startswith('same-bytes')
    if same_bytes:
        from tests.project_folder_image_delivery_fixtures import png
        content = png((20, 30, 40), width=3, height=2)
        references = job / 'package' / 'references'
        references.mkdir()
        request['references'] = [
            {'role': role, 'filename': f'references/{name}.png', 'sha256': sha256(content).hexdigest()}
            for role, name in [('character_identity:C01', 'identity'), ('parent_output', 'continuity')]]
        for item in request['references']:
            (job / 'package' / item['filename']).write_bytes(content)
    (job / 'package/request.json').write_text(json.dumps(request))
    (job / 'package/COPY_ASSIGNMENT.txt').write_text('Synthetic immutable assignment; no generation.')
    attempt = CodexExecAttempt(attemptId=uuid4(), runId=uuid4(), projectId=uuid4(), jobId=job_id,
        operationKey='image:synthetic', domain='image', requestHash=request['requestHash'],
        packageHash=package_tree_hash(job, max_total_bytes=profile.max_output_bytes),
        profileHash=profile.profile_hash, reservedImageOutputs=1, imageBudgetState='reserved', state='spawn_intent')
    if same_bytes:
        attempt = attempt.model_copy(update={'plotloom_code_revision': request['specialistPreflight']['codeRevision']})
    _insert_attempt_row(supervisor, attempt, attempt)
    private = supervisor.private_root / 'attempts' / str(attempt.attempt_id)
    private.mkdir(parents=True)
    worker = os.getpid()
    with closing(supervisor._connect()) as connection:
        connection.execute('UPDATE exec_attempts SET project_home=?,job_root=?,worker_pid=?,worker_group_id=?,worker_birth_identity=? WHERE attempt_id=?',
            (str(home), str(job), worker, worker, 'synthetic-worker', str(attempt.attempt_id)))
        connection.execute('INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)', (str(attempt.attempt_id), 'image'))
        connection.execute('INSERT INTO exec_queue(attempt_id,enabled) VALUES (?,1)', (str(attempt.attempt_id),))
    monkeypatch.setattr(supervisor, '_process_identity', lambda pid: (pid, 'synthetic-native' if pid == NATIVE_PID else 'synthetic-worker'))
    session_id = uuid4()
    today = datetime.now(UTC).date()
    folder = supervisor.codex_home / 'sessions' / f'{today.year:04d}' / f'{today.month:02d}' / f'{today.day:02d}'
    if mode != 'missing-session':
        folder.mkdir(parents=True)
        rows = [{'type': 'session_meta', 'ordinal': 0, 'payload': {'id': str(session_id)}},
            {'type': 'response_item', 'ordinal': 34, 'payload': {'type': 'custom_tool_call', 'name': 'exec',
                'call_id': 'synthetic-image-call', 'input': 'await tools.image_gen__imagegen({prompt:"SANITIZED",transparent_background:false});'}}]
        if mode != 'missing-terminal':
            event = {'type': 'Extension', 'kind': 'image_gen.generation', 'id': 'synthetic-image-event',
                     'status': 'failed', 'failure': None, 'result': '', 'revisedPrompt': ''}
            if mode != 'failed-absent':
                event['transparentBackground'] = None
            rows.append({'type': 'event_msg', 'ordinal': 68, 'payload': {'item': event}})
            if mode == 'duplicate-terminal':
                rows.append({'type': 'event_msg', 'ordinal': 69, 'payload': {'item': event}})
        (folder / f'rollout-synthetic-{session_id}.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in rows))
        if same_bytes:
            from tests.test_codex_exec_telemetry import (
                _extension, _image_call, _image_view_event, _inline_image_output, _view_call,
            )
            saved = supervisor.codex_home / 'generated_images' / str(session_id) / 'frame.png'
            saved.parent.mkdir(parents=True)
            saved.write_bytes(content)
            paths = [str(job / 'package' / item['filename']) for item in request['references']]
            attached = list(reversed(paths)) if mode == 'same-bytes-wrong-path-order' else paths
            viewed = list(reversed(paths)) if mode == 'same-bytes-wrong-view-order' else paths
            records = []
            for index, path in enumerate(viewed):
                records.extend([_view_call(path, f'view-{index}', ordinal=index * 3 + 1),
                    _image_view_event(Path(path).as_uri(), event_id=f'view-event-{index}', ordinal=index * 3 + 2),
                    _inline_image_output(f'view-{index}', ordinal=index * 3 + 3)])
            event = json.loads(_extension('completed', event_id='generation-event', ordinal=8))
            event['payload']['item']['savedPath'] = str(saved)
            records.extend([_image_call(references=tuple(attached), ordinal=7), (json.dumps(event) + '\n').encode()])
            header = {'type': 'session_meta', 'ordinal': 0, 'payload': {'id': str(session_id)}}
            (folder / f'rollout-synthetic-{session_id}.jsonl').write_bytes((json.dumps(header) + '\n').encode() + b''.join(records))
        if mode == 'no-remote-call':
            from tests.codex_exec_recovery_fixtures import write_readonly_turn
            write_readonly_turn(job, supervisor.source_root, private,
                folder / f'rollout-synthetic-{session_id}.jsonl', session_id)
            (private / 'stdout.jsonl').unlink()
            (private / 'stderr.log').unlink()
    observations, parser_calls = [], []
    def group_exists(group_id):
        assert group_id == NATIVE_PID
        observations.append(group_id)
        return mode == 'group-not-exited'
    monkeypatch.setattr(type(supervisor), '_process_group_exists', staticmethod(group_exists))
    strict_exit = supervisor._wait_for_process_group_exit
    # Keep the actual strict group-exit decision; a zero grace bounds this simulated OS seam.
    monkeypatch.setattr(supervisor, '_wait_for_process_group_exit', lambda group: strict_exit(group, grace_seconds=0))
    read_session = telemetry_owner.read_cli_session
    def observed_parse(*args, **kwargs):
        parser_calls.append(args[1])
        return read_session(*args, **kwargs)
    monkeypatch.setattr(telemetry_owner, 'read_cli_session', observed_parse)
    real_popen = process_owner.subprocess.Popen
    class SimulatedCLI:
        pid = NATIVE_PID
        def __init__(self, stdout):
            self.stdin = io.BytesIO()
            events = [{'type': 'thread.started', 'thread_id': str(session_id)}, {'type': 'turn.started'}]
            if reconnect:
                events.append({'type': 'error', 'message': 'Reconnecting... 2/5 (exceeded retry limit, last status: 429 Too Many Requests)'})
            events.append({'type': 'turn.completed'})
            for event in events:
                stdout.write((json.dumps(event) + '\n').encode())
        def poll(self):
            return 0
        def wait(self, timeout=None):
            return 0
    def launch(command, *args, **kwargs):
        if len(command) > 1 and command[0] == str(supervisor.executable) and command[1] == 'exec':
            filesystem = next(value for value in command if '.filesystem=' in value)
            skill = supervisor.source_root / '.agents/skills/plotloom-image-specialist/SKILL.md'
            assert f'{json.dumps(str(skill))}="read"' in filesystem
            assert f'{json.dumps(str(supervisor.source_root))}=' not in filesystem
            return SimulatedCLI(kwargs['stdout'])
        return real_popen(command, *args, **kwargs)
    monkeypatch.setattr(process_owner.subprocess, 'Popen', launch)
    # Execute the production owner path through spawn authorization, group exit, telemetry and settlement.
    supervisor._run(attempt, profile, request, job, private)
    return attempt, supervisor._load(supervisor._row(attempt.attempt_id)), session_id, observations, parser_calls


@pytest.mark.parametrize('mode', ['failed-null', 'failed-absent'])
def test_bound_failed_image_settles_only_after_strict_group_exit(supervisor, tmp_path, monkeypatch, mode):
    attempt, result, session, groups, parsed = _execute_image(supervisor, tmp_path, monkeypatch, mode)
    assert groups == [NATIVE_PID]
    assert parsed == [session]
    assert result.state == 'failed'
    assert result.attempt.process_id == result.attempt.process_group_id == NATIVE_PID
    assert result.attempt.session_id == session
    assert result.attempt.process_exit_code == 0
    assert result.attempt.terminal_result == 'failure'
    assert result.attempt.remote_tool_state == 'failed'
    assert result.attempt.image_budget_state == 'released'
    assert result.attempt.evidence_hash is not None
    assert result.attempt.remote_output_hash is None
    assert result.receipt is None
    with closing(supervisor._connect()) as connection:
        assert connection.execute('SELECT * FROM exec_slot WHERE attempt_id=?', (str(attempt.attempt_id),)).fetchone() is None
        witness = json.loads(connection.execute('SELECT evidence_json FROM exec_process_exits WHERE attempt_id=?',
            (str(attempt.attempt_id),)).fetchone()[0])
        assert witness['processExitCode'] == 0 and witness['processId'] == NATIVE_PID
        assert witness['processGroupId'] == NATIVE_PID


@pytest.mark.parametrize('mode', ['missing-session', 'missing-terminal', 'duplicate-terminal', 'group-not-exited'])
def test_missing_ambiguous_or_unsettled_image_proof_keeps_unknown_capacity(supervisor, tmp_path, monkeypatch, mode):
    attempt, result, _session, groups, parsed = _execute_image(supervisor, tmp_path, monkeypatch, mode)
    assert groups == [NATIVE_PID]
    assert result.state == 'outcome_unknown'
    assert result.attempt.image_budget_state == 'reserved'
    assert result.attempt.terminal_result is None
    assert result.attempt.session_id is None
    assert result.receipt is None
    if mode in {'missing-session', 'group-not-exited'}:
        assert parsed == []
    with closing(supervisor._connect()) as connection:
        assert connection.execute('SELECT * FROM exec_slot WHERE attempt_id=?', (str(attempt.attempt_id),)).fetchone()


def test_live_waiter_with_complete_no_dispatch_proof_records_genuine_failure(supervisor, tmp_path, monkeypatch):
    attempt, result, session, groups, parsed = _execute_image(supervisor, tmp_path, monkeypatch, 'no-remote-call')
    assert groups == [NATIVE_PID] and parsed and set(parsed) == {session}
    assert result.state == 'failed' and result.attempt.terminal_result == 'failure'
    assert result.attempt.remote_tool_state == 'not_applicable'
    assert result.attempt.process_exit_code == 0 and result.attempt.session_id == session
    assert result.attempt.image_budget_state == 'released' and result.receipt is None
    with closing(supervisor._connect()) as connection:
        assert connection.execute('SELECT * FROM exec_slot WHERE attempt_id=?', (str(attempt.attempt_id),)).fetchone() is None
        witness = json.loads(connection.execute('SELECT evidence_json FROM exec_process_exits WHERE attempt_id=?',
            (str(attempt.attempt_id),)).fetchone()[0])
        assert witness['processExitCode'] == 0


@pytest.mark.parametrize("mode", ["failed-null", "no-remote-call"])
def test_recovered_image_transport_preserves_unknown_budget_and_slot_before_settlement(supervisor, tmp_path, monkeypatch, mode):
    attempt, result, session, groups, parsed = _execute_image(supervisor, tmp_path, monkeypatch, mode, reconnect=True)
    assert groups == [NATIVE_PID] and parsed and set(parsed) == {session}
    assert result.state == "outcome_unknown" and result.receipt is None
    assert result.attempt.session_id == session
    assert result.attempt.image_budget_state == "reserved"
    assert result.attempt.reserved_image_outputs == 1
    assert result.attempt.terminal_result is None and result.attempt.process_exit_code is None
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT * FROM exec_slot WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
        assert connection.execute("SELECT * FROM exec_recovery_evidence WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone() is None
