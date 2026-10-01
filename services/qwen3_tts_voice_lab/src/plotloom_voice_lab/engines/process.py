"""One reaped process group per job; inference dependencies never enter the API."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from .catalog import validate_snapshot
from .protocol import RunnerEvent, RunnerRequest
from .resources import admission


class EngineFailure(RuntimeError):
    pass


def runtime_config() -> dict:
    location = os.environ.get("VOICE_LAB_RUNTIME_CONFIG")
    if not location:
        return {}
    with Path(location).open() as source:
        return json.load(source)


def runtime_fingerprint(runtime: dict) -> str:
    return hashlib.sha256(json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ProcessEngine:
    def __init__(self, *, config=None, resource_probe=admission, command_factory=None):
        self.config = runtime_config() if config is None else config
        self.resource_probe = resource_probe
        self.command_factory = command_factory or (lambda runtime: [runtime["python"], "-m", "plotloom_voice_lab.engines.runner"])
        self.cancelled = threading.Event()
        self.lock = threading.Lock()
        self.process = None

    def availability(self) -> dict:
        return {engine: bool(Path(config["python"]).is_file() and Path(config["modelDir"]).is_dir())
                for engine, config in self.config.items()}

    def stop(self) -> None:
        self.cancelled.set()
        with self.lock:
            if self.process is not None:
                self._reap(self.process)

    def release_confirmed(self) -> bool:
        with self.lock:
            return self.process is None

    @staticmethod
    def _reap(process) -> None:
        # Include descendants even if the leader has already exited.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)

    def run(self, snapshot: dict, values: dict, output_dir: Path, phase, evidence) -> tuple[Path, dict]:
        try:
            validate_snapshot(snapshot)
        except ValueError as error:
            raise EngineFailure("engine.snapshot_unavailable") from error
        runtime = self.config.get(snapshot["engineId"])
        if runtime is None:
            raise EngineFailure("model.unavailable")
        if runtime_fingerprint(runtime) != snapshot.get("runtimeFingerprint"):
            raise EngineFailure("engine.snapshot_unavailable")
        started = time.monotonic()
        phase("waiting_for_resources")
        while self.resource_probe(runtime):
            if self.cancelled.wait(1):
                raise EngineFailure("generation.interrupted")
            if time.monotonic() - started > runtime["resourceWaitSeconds"]:
                raise EngineFailure("resource.headroom_unavailable")
        if self.cancelled.is_set():
            raise EngineFailure("generation.interrupted")
        output_dir.mkdir(parents=True, exist_ok=False)
        events, output = output_dir / "events.jsonl", output_dir / "audio.wav"
        request = RunnerRequest(snapshot=snapshot, runtime=runtime, output=str(output), events=str(events), **values)
        request_path = output_dir / "request.json"
        request_path.write_text(request.model_dump_json(), encoding="utf-8")
        os.chmod(request_path, 0o600)
        env = {**os.environ, **runtime.get("env", {}), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        seen, failure, complete, delivery_seen = 0, None, None, False
        process_started = time.monotonic()
        with (output_dir / "runtime.log").open("wb") as log:
            with self.lock:
                if self.cancelled.is_set():
                    raise EngineFailure("generation.interrupted")
                process = subprocess.Popen(self.command_factory(runtime) + [str(request_path)], stdout=log, stderr=log,
                                           env=env, start_new_session=True)
                self.process = process
            try:
                while True:
                    if events.exists():
                        if events.stat().st_size > 65536:
                            raise EngineFailure("runner.protocol_invalid")
                        lines = events.read_text().splitlines(keepends=True)
                        for line in lines[seen:]:
                            if not line.endswith("\n"):
                                break
                            try:
                                event = RunnerEvent.model_validate_json(line)
                            except ValueError as error:
                                raise EngineFailure("runner.protocol_invalid") from error
                            seen += 1
                            if event.kind == "phase":
                                phase(event.phase)
                            elif event.kind == "delivery":
                                if delivery_seen or snapshot['stage'] != 'reuse':
                                    raise EngineFailure("runner.duplicate_evidence")
                                if event.evidence.mode != request.delivery.mode or (
                                        request.delivery.mode == 'manual' and event.evidence.effectiveVector != request.delivery.vector):
                                    raise EngineFailure('runner.protocol_invalid')
                                evidence(event.evidence.model_dump(exclude_none=True))
                                delivery_seen = True
                            elif event.kind == "failure":
                                failure = event.errorCode
                            else:
                                if complete is not None:
                                    raise EngineFailure('runner.protocol_invalid')
                                complete = event
                    if process.poll() is not None:
                        # Drain once after exit: a final write can race the poll.
                        if events.exists():
                            remaining = events.read_text().splitlines(keepends=True)[seen:]
                            if remaining and not remaining[-1].endswith("\n"):
                                raise EngineFailure("runner.protocol_invalid")
                            if remaining:
                                continue
                        break
                    if self.cancelled.is_set():
                        raise EngineFailure("generation.interrupted")
                    if time.monotonic() - process_started > runtime["timeoutSeconds"]:
                        raise EngineFailure("generation.timeout")
                    time.sleep(0.1)
                if failure or process.returncode != 0 or complete is None:
                    raise EngineFailure(failure or "generation.process_failed")
                if snapshot["stage"] == "reuse" and not delivery_seen:
                    raise EngineFailure("runner.evidence_missing")
                if output.is_symlink() or not output.is_file():
                    raise EngineFailure("audio.invalid")
                return output, {"processElapsedSeconds": round(time.monotonic() - process_started, 3),
                                "peakTorchGiB": complete.peakTorchGiB, "processId": process.pid}
            finally:
                self._reap(process)
                with self.lock:
                    self.process = None
