"""Failed output metadata is unavailable, never a fabricated successful setting."""
import json
from uuid import UUID

import pytest

from plotloom.codex_exec_telemetry import CodexExecTelemetryError, read_cli_session

SESSION = UUID('22222222-2222-4222-8222-222222222222')
ABSENT = object()


def _rows(status='failed', transparency=None, *, output_path=ABSENT):
    item = {'type': 'Extension', 'id': 'sanitized-image-event', 'kind': 'image_gen.generation', 'status': status,
            'failure': None, 'result': '', 'revisedPrompt': ''}
    if transparency is not ABSENT:
        item['transparentBackground'] = transparency
    if output_path is not ABSENT:
        item['savedPath'] = output_path
    return [
        {'type': 'session_meta', 'ordinal': 0, 'payload': {'id': str(SESSION)}},
        {'type': 'response_item', 'ordinal': 34, 'payload': {'type': 'custom_tool_call', 'name': 'exec',
            'call_id': 'sanitized-image-call',
            'input': 'await tools.image_gen__imagegen({prompt:"SANITIZED PLACEHOLDER",transparent_background:false});'}},
        {'type': 'event_msg', 'ordinal': 68, 'payload': {'item': item}},
    ]


def _read(tmp_path, rows):
    path = tmp_path / 'sanitized-session.jsonl'
    path.write_bytes(b''.join((json.dumps(row) + '\n').encode() for row in rows))
    return read_cli_session(path, SESSION, max_event_bytes=8192, max_total_bytes=32768)


@pytest.mark.parametrize('transparency', [None, ABSENT], ids=['null', 'absent'])
def test_failed_terminal_preserves_unavailable_output_metadata(tmp_path, transparency):
    evidence = _read(tmp_path, _rows(transparency=transparency))
    assert evidence.image_calls[0].transparent_background is False
    event, = evidence.image_events
    assert event.status == 'failed'
    assert event.transparent_background is None
    assert event.saved_path is None


@pytest.mark.parametrize('transparency', [0, 1, 'false', [], {}, True])
def test_failed_terminal_rejects_wrong_type_or_mismatched_supplied_metadata(tmp_path, transparency):
    with pytest.raises(CodexExecTelemetryError, match='transparency'):
        _read(tmp_path, _rows(transparency=transparency))


@pytest.mark.parametrize('transparency', [None, ABSENT], ids=['null', 'absent'])
def test_completed_terminal_still_requires_boolean_transparency(tmp_path, transparency):
    with pytest.raises(CodexExecTelemetryError, match='transparency'):
        _read(tmp_path, _rows('completed', transparency, output_path='/synthetic/not-opened.png'))


@pytest.mark.parametrize('output_path', [ABSENT, None, ''])
def test_completed_terminal_still_requires_output_path(tmp_path, output_path):
    with pytest.raises(CodexExecTelemetryError, match='output path'):
        _read(tmp_path, _rows('completed', False, output_path=output_path))


@pytest.mark.parametrize('mutation', ['unbound', 'duplicate', 'order', 'event-id', 'session'])
def test_failed_terminal_does_not_weaken_binding_or_order(tmp_path, mutation):
    rows = _rows()
    if mutation == 'unbound':
        rows.pop(1)
    elif mutation == 'duplicate':
        rows.append({'type': 'event_msg', 'ordinal': 69, 'payload': rows[-1]['payload']})
    elif mutation == 'order':
        rows[-1]['ordinal'] = 33
    elif mutation == 'event-id':
        rows.insert(2, {'type': 'event_msg', 'ordinal': 35, 'payload': {'item': {'type': 'Extension',
            'id': 'different-progress-id', 'kind': 'image_gen.generation', 'status': 'in_progress'}}})
    else:
        rows[0]['payload']['id'] = str(UUID(int=1))
    with pytest.raises(CodexExecTelemetryError):
        _read(tmp_path, rows)
