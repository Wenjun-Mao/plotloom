"""CPU observer records measured counters, not a fabricated GPU capacity."""

import importlib
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1] / 'tools'


@pytest.fixture
def observer(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    return importlib.import_module('memory_trace')


def test_sample_has_timestamps_and_no_commands_or_cuda(observer, tmp_path):
    (tmp_path / 'meminfo').write_text('MemTotal: 1000 kB\nMemAvailable: 600 kB\nSwapTotal: 100 kB\nSwapFree: 90 kB\n')
    (tmp_path / 'vmstat').write_text('pswpout 42\n')
    process = tmp_path / '123'
    process.mkdir()
    (process / 'cmdline').write_bytes(b'python\0main.py\0--listen\0private-path\0')
    (process / 'status').write_text('VmRSS: 50 kB\nVmHWM: 60 kB\n')
    value = observer.sample(tmp_path)
    assert value['memoryKiB']['MemAvailable'] == 600
    assert value['processes'] == [{'label': 'comfy', 'pid': 123, 'memoryKiB': {'VmRSS': 50, 'VmHWM': 60}}]
    assert value['utc'] and value['monotonicSeconds'] > 0
    assert 'private-path' not in json.dumps(value) and 'cudaFree' not in value


def test_trace_is_exclusive_private_and_labels_job(observer, tmp_path, monkeypatch):
    monkeypatch.setattr(observer, 'sample', lambda: {'utc': 'test', 'monotonicSeconds': 1,
        'memoryKiB': {'MemAvailable': 60, 'SwapTotal': 10, 'SwapFree': 7}, 'processes': []})
    path = tmp_path / 'trace.jsonl'
    with observer.MemoryTrace(path) as trace:
        trace.mark(phase='running', jobId='h3_test')
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert records[0]['cudaMemory'] is None
    assert records[-1]['phase'] == 'running' and records[-1]['jobId'] == 'h3_test'
    assert trace.summary['minAvailableKiB'] == 60 and trace.summary['maxSwapUsedKiB'] == 3
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError), observer.MemoryTrace(path):
        pytest.fail('must not overwrite evidence')


@pytest.mark.parametrize('interval', [0, -1, float('nan'), float('inf')])
def test_invalid_interval_rejected(observer, tmp_path, interval):
    with pytest.raises(ValueError, match='invalid_interval'):
        observer.MemoryTrace(tmp_path / 'unused', interval)


def test_sampler_failure_visible(observer, tmp_path, monkeypatch):
    monkeypatch.setattr(observer, 'sample', lambda: {'utc': 'test', 'monotonicSeconds': 1,
        'memoryKiB': {'MemAvailable': 60, 'SwapTotal': 10, 'SwapFree': 7}, 'processes': []})
    with observer.MemoryTrace(tmp_path / 'trace') as trace:
        trace.error = OSError('disk full')
        with pytest.raises(RuntimeError, match='observer_failed'):
            trace.check()
        trace.error = None


def test_final_sampling_failure_preserves_job_failure(observer, tmp_path, monkeypatch):
    monkeypatch.setattr(observer, 'sample', lambda: {'utc': 'test', 'monotonicSeconds': 1,
        'memoryKiB': {'MemAvailable': 60, 'SwapTotal': 10, 'SwapFree': 7}, 'processes': []})
    trace = observer.MemoryTrace(tmp_path / 'trace')
    with pytest.raises(ValueError, match='job.failed'), trace:
        monkeypatch.setattr(trace, '_append', lambda: (_ for _ in ()).throw(OSError('disk full')))
        raise ValueError('job.failed')
    assert trace.summary['observerFailed'] is True and trace.file.closed


def test_final_sampling_failure_rejects_clean_completion(observer, tmp_path, monkeypatch):
    monkeypatch.setattr(observer, 'sample', lambda: {'utc': 'test', 'monotonicSeconds': 1,
        'memoryKiB': {'MemAvailable': 60, 'SwapTotal': 10, 'SwapFree': 7}, 'processes': []})
    with pytest.raises(RuntimeError, match='observer_failed'), observer.MemoryTrace(tmp_path / 'trace') as trace:
        monkeypatch.setattr(trace, '_append', lambda: (_ for _ in ()).throw(OSError('disk full')))


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_post_redirect_is_not_followed(monkeypatch, status):
    import threading
    import urllib.error
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer

    monkeypatch.syspath_prepend(str(TOOLS))
    comparison = importlib.import_module('compare_h3_references')
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.path)
            self.send_response(status)
            self.send_header('Location', '/must-not-follow')
            self.end_headers()

        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/start', data=b'test')
            opener = urllib.request.build_opener(comparison.NoRedirect())
            with pytest.raises(urllib.error.HTTPError) as failure:
                opener.open(request, timeout=5)
            assert failure.value.code == status and requests == ['/start']
        finally:
            server.shutdown()
            thread.join()


def test_comparison_existing_receipt_refuses_before_preflight(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    comparison = importlib.import_module('compare_h3_references')
    path = tmp_path / 'receipt.json'
    path.write_text('{}')
    monkeypatch.setattr(sys, 'argv', ['comparison', '--receipt', str(path)])
    monkeypatch.setattr(comparison, 'idle', lambda: pytest.fail('unexpected preflight'))
    with pytest.raises(ValueError, match='receipt_exists_no_replay'):
        comparison.main()


def test_uncertain_first_post_stops_second_and_retains_trace(tmp_path, monkeypatch, observer):
    import hashlib

    comparison = importlib.import_module('compare_h3_references')
    source = tmp_path / 'source'
    source.write_bytes(b'source')
    digest = hashlib.sha256(b'source').hexdigest()
    monkeypatch.setattr(comparison, 'IMAGE', source)
    monkeypatch.setattr(comparison, 'IMAGE_HASH', digest)
    monkeypatch.setattr(comparison, 'CASES', [('identity', source, digest), ('take', source, digest)])
    monkeypatch.setattr(comparison, 'idle', dict)
    monkeypatch.setattr(comparison.subprocess, 'check_output', lambda *a, **k:
                        b'[{"Config":{"Env":["H3_API_KEY=test-only"]}}]')

    def prepare(source, output):
        output.write_bytes(source.read_bytes())
        return {}

    monkeypatch.setattr(comparison, 'prepare', prepare)
    monkeypatch.setattr(observer, 'sample', lambda: {'utc': 'test', 'monotonicSeconds': 1,
        'memoryKiB': {'MemAvailable': 60, 'SwapTotal': 10, 'SwapFree': 7}, 'processes': []})
    calls = []

    class UncertainOpener:
        def open(self, request, timeout):
            calls.append(request.get_method())
            raise TimeoutError('uncertain')

    monkeypatch.setattr(comparison.urllib.request, 'build_opener', lambda *a: UncertainOpener())
    path = tmp_path / 'receipt.json'
    monkeypatch.setattr(sys, 'argv', ['comparison', '--receipt', str(path)])
    with pytest.raises(TimeoutError):
        comparison.main()
    receipt = json.loads(path.read_text())
    assert calls == ['POST'] and receipt['generationCalls'] == 1
    assert receipt['status'] == 'failed_or_uncertain_no_replay'
    assert receipt['memorySummary']['samples'] == 2 and receipt['memoryTraceSha256']
    assert not receipt['cases'][1].get('dispatchIntent')
    assert 'test-only' not in path.read_text()
