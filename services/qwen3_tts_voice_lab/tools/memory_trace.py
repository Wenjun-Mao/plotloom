"""CPU-only Spark memory time series. No CUDA context, service stop or eviction."""

from __future__ import annotations

import argparse
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

MEMORY_KEYS = {'MemTotal', 'MemFree', 'MemAvailable', 'Buffers', 'Cached',
               'SReclaimable', 'Slab', 'AnonPages', 'PageTables', 'SwapTotal', 'SwapFree'}
PROCESS_MARKERS = (
    ('comfy', b'main.py', b'--listen'),
    ('qwen_image', b'sglang', None),
    ('voice_engine', b'plotloom_voice_lab.engines.runner', None),
    ('embedding', b'vllm', None),
)


def counters(text: str, keys: set[str]) -> dict[str, int]:
    values = {}
    for line in text.splitlines():
        parts = line.replace(':', ' ').split()
        if len(parts) >= 2 and parts[0] in keys:
            values[parts[0]] = int(parts[1])
    return values


def sample(proc: Path = Path('/proc')) -> dict:
    memory = counters((proc / 'meminfo').read_text(), MEMORY_KEYS)
    if not {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'} <= memory.keys():
        raise ValueError('memory.required_counters_missing')
    processes = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / 'cmdline').read_bytes()
            label = next((label for label, marker, extra in PROCESS_MARKERS
                          if marker in command and (extra is None or extra in command)), None)
            if label:
                status = counters((entry / 'status').read_text(), {'VmRSS', 'VmHWM', 'VmSwap'})
                processes.append({'label': label, 'pid': int(entry.name), 'memoryKiB': status})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue  # Process exit during sampling is ordinary, not zero RSS.
    pressure_path = proc / 'pressure' / 'memory'
    pressure = {}
    if pressure_path.exists():
        for line in pressure_path.read_text().splitlines():
            parts = line.split()
            pressure[parts[0]] = {key: float(value) for key, value in
                                  (part.split('=') for part in parts[1:])}
    vmstat = counters((proc / 'vmstat').read_text(),
                      {'pswpin', 'pswpout', 'pgmajfault', 'oom_kill'})
    return {'utc': datetime.now(timezone.utc).isoformat(), 'monotonicSeconds': time.monotonic(),
            'memoryKiB': memory, 'pressure': pressure, 'vmstat': vmstat,
            'processes': sorted(processes, key=lambda item: item['pid'])}


class MemoryTrace:
    """Independent sampler, so a slow HTTP poll does not create a memory blind spot."""

    def __init__(self, path: Path, interval: float = 1.0):
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError('memory.invalid_interval')
        self.interval = interval
        self.path = path
        self.context = {'phase': 'preflight', 'jobId': None, 'case': None}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.error = None
        self.summary = {'samples': 0, 'minAvailableKiB': None, 'maxSwapUsedKiB': 0,
                        'maxSampleGapSeconds': 0.0, 'peakRssKiBByLabel': {}}
        self.previous_time = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = os.fdopen(os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w')
        self.file.write(json.dumps({'kind': 'memory_trace.v1', 'requestedIntervalSeconds': self.interval,
            'cudaMemory': None, 'cudaMemoryReason': 'not_measured_no_extra_cuda_context',
            'units': 'KiB; overlapping UMA views, never add RSS to host use'}) + '\n')
        self.file.flush()
        os.fsync(self.file.fileno())
        try:
            self._append()
        except (OSError, ValueError, KeyError):
            self.file.close()
            raise
        self.thread = threading.Thread(target=self._run, name='cpu-memory-observer', daemon=True)
        self.thread.start()
        return self

    def mark(self, **context):
        with self.lock:
            self.context.update(context)
        self.check()

    def check(self):
        if self.error is not None:
            raise RuntimeError('memory.observer_failed') from self.error

    def _append(self):
        value = sample()
        with self.lock:
            value.update(self.context)
        self.file.write(json.dumps(value) + '\n')
        self.file.flush()
        memory = value['memoryKiB']
        available = memory['MemAvailable']
        prior = self.summary['minAvailableKiB']
        self.summary['minAvailableKiB'] = available if prior is None else min(prior, available)
        self.summary['maxSwapUsedKiB'] = max(self.summary['maxSwapUsedKiB'],
                                            memory['SwapTotal'] - memory['SwapFree'])
        now = value['monotonicSeconds']
        if self.previous_time is not None:
            self.summary['maxSampleGapSeconds'] = max(self.summary['maxSampleGapSeconds'], now - self.previous_time)
        self.previous_time = now
        self.summary['samples'] += 1
        peaks = self.summary['peakRssKiBByLabel']
        for process in value['processes']:
            label = process['label']
            peaks[label] = max(peaks.get(label, 0), process['memoryKiB'].get('VmRSS', 0))

    def _run(self):
        try:
            while not self.stop_event.wait(self.interval):
                self._append()
        except (OSError, ValueError, KeyError) as error:
            self.error = error

    def __exit__(self, kind, value, traceback):
        self.stop_event.set()
        self.thread.join()
        try:
            self._append()
            os.fsync(self.file.fileno())
        except (OSError, ValueError, KeyError) as error:
            self.error = self.error or error
        finally:
            self.file.close()
        self.summary['observerFailed'] = self.error is not None
        # Keep an active job exception authoritative, but retain observer failure
        # independently in its receipt. Successful jobs must not hide trace loss.
        if kind is None:
            self.check()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration-seconds', type=float, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.duration_seconds) or args.duration_seconds <= 0:
        parser.error('duration must be positive and finite')
    with MemoryTrace(args.output) as trace:
        deadline = time.monotonic() + args.duration_seconds
        while time.monotonic() < deadline:
            trace.check()
            time.sleep(min(1, max(0, deadline - time.monotonic())))
    print(json.dumps(trace.summary))


if __name__ == '__main__':
    main()
