"""Run the complete Python suite in two isolated, case-balanced processes."""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[2]
WORKER_COUNT = 2
WORKER_SHUTDOWN_GRACE_SECONDS = 5.0


class SuiteError(ValueError):
    """The native Python test collection cannot be safely partitioned."""


def parse_collected_cases(stdout: str, *, root: Path = ROOT) -> list[str]:
    cases: list[str] = []
    resolved_root = root.resolve(strict=True)
    test_root = (resolved_root / "tests").resolve(strict=True)
    for raw_line in stdout.splitlines():
        case_id = raw_line.strip()
        if not case_id.startswith("tests/"):
            continue
        if "::" not in case_id or not case_id.split("::", 1)[1]:
            raise SuiteError(f"unrecognized pytest collection row: {case_id}")
        relative_path = case_id.split("::", 1)[0]
        candidate = resolved_root / relative_path
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(test_root)
        except (OSError, RuntimeError, ValueError) as error:
            raise SuiteError(f"unsafe pytest collection row: {case_id}") from error
        if not resolved.is_file() or resolved.suffix != ".py":
            raise SuiteError(f"pytest collection row is not a test file: {case_id}")
        if resolved.relative_to(resolved_root).as_posix() != relative_path:
            raise SuiteError(f"pytest collection row is not normalized: {case_id}")
        cases.append(case_id)
    if not cases:
        raise SuiteError("pytest collection returned no case IDs")
    if len(cases) != len(set(cases)):
        raise SuiteError("pytest collection returned duplicate case IDs")
    return cases


def partition_test_files(
    cases: Sequence[str], worker_count: int = WORKER_COUNT
) -> tuple[tuple[str, ...], ...]:
    if worker_count < 1:
        raise SuiteError("worker count must be positive")
    if not cases:
        raise SuiteError("cannot partition an empty pytest collection")
    if len(cases) != len(set(cases)):
        raise SuiteError("cannot partition duplicate pytest case IDs")

    file_case_counts = Counter(case_id.split("::", 1)[0] for case_id in cases)
    assignments: list[list[str]] = [[] for _ in range(worker_count)]
    case_totals = [0] * worker_count
    for path, case_count in sorted(
        file_case_counts.items(), key=lambda item: (-item[1], item[0])
    ):
        worker_index = min(range(worker_count), key=case_totals.__getitem__)
        assignments[worker_index].append(path)
        case_totals[worker_index] += case_count

    if any(not assignment for assignment in assignments):
        raise SuiteError("native pytest collection is too small for all workers")
    flattened = [path for assignment in assignments for path in assignment]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(file_case_counts):
        raise SuiteError("pytest worker file assignment is not an exact cover")
    return tuple(tuple(sorted(assignment)) for assignment in assignments)


def _command(files: Sequence[str], basetemp: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--durations=20",
        "-p",
        "no:cacheprovider",
        f"--basetemp={basetemp}",
        *files,
    ]


def _process_group_exists(process: subprocess.Popen[str]) -> bool:
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def _stop_processes(processes: Sequence[subprocess.Popen[str]]) -> None:
    if not processes:
        return

    if os.name == "posix":
        for process in processes:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        deadline = time.monotonic() + WORKER_SHUTDOWN_GRACE_SECONDS
        remaining_groups = list(processes)
        while remaining_groups and time.monotonic() < deadline:
            for process in processes:
                process.poll()
            remaining_groups = [
                process for process in processes if _process_group_exists(process)
            ]
            if remaining_groups:
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))

        for process in remaining_groups:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for process in processes:
            process.wait()
        return

    for process in processes:
        if process.poll() is not None:
            continue
        process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=WORKER_SHUTDOWN_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def run_python_suite(
    *, root: Path = ROOT, environment: dict[str, str] | None = None
) -> int:
    received_sigterm: int | None = None

    def record_sigterm(signum: int, _frame: object) -> None:
        nonlocal received_sigterm
        received_sigterm = signum

    previous_sigterm_handler = signal.signal(signal.SIGTERM, record_sigterm)
    processes: list[subprocess.Popen[str]] = []

    def sigterm_exit_code() -> int:
        if received_sigterm is None:
            raise RuntimeError("SIGTERM exit requested without a received signal")
        print(f"[python-suite] TERMINATED signal={received_sigterm}", flush=True)
        return 128 + received_sigterm

    try:
        env = os.environ.copy() if environment is None else environment.copy()
        if env.get("PYTEST_ADDOPTS"):
            print(
                "Python suite refuses ambient PYTEST_ADDOPTS",
                file=sys.stderr,
                flush=True,
            )
            return 2
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        collector = [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ]
        print(f"[python-suite] COLLECT {shlex.join(collector)}", flush=True)
        collector_process: subprocess.Popen[str] | None = None
        collector_stdout = ""
        collector_stderr = ""
        collection_interrupted = False
        try:
            try:
                collector_process = subprocess.Popen(
                    collector,
                    cwd=root,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=os.name == "posix",
                    text=True,
                )
            except OSError as error:
                print(
                    f"Python collection could not start: {error}",
                    file=sys.stderr,
                    flush=True,
                )
                return 127

            while True:
                if received_sigterm is not None:
                    collection_interrupted = True
                    break
                try:
                    collector_stdout, collector_stderr = collector_process.communicate(
                        timeout=0.25
                    )
                    break
                except subprocess.TimeoutExpired:
                    continue
            if received_sigterm is not None:
                collection_interrupted = True
        finally:
            if collector_process is not None:
                _stop_processes([collector_process])

        if collection_interrupted:
            return sigterm_exit_code()
        if collector_process is None:
            raise RuntimeError("pytest collector was not started")
        if collector_stderr:
            print(collector_stderr, end="", file=sys.stderr, flush=True)
        if collector_process.returncode:
            print(collector_stdout, end="", flush=True)
            return collector_process.returncode
        try:
            cases = parse_collected_cases(collector_stdout, root=root)
            assignments = partition_test_files(cases)
        except SuiteError as error:
            print(
                f"Python suite refused collection: {error}",
                file=sys.stderr,
                flush=True,
            )
            return 2

        file_case_counts = Counter(case_id.split("::", 1)[0] for case_id in cases)
        shard_case_counts = [
            sum(file_case_counts[path] for path in shard) for shard in assignments
        ]
        print(
            f"[python-suite] native_cases={len(cases)} files={len(file_case_counts)} "
            f"workers={WORKER_COUNT} shard_cases={'/'.join(map(str, shard_case_counts))} "
            f"shard_files={'/'.join(str(len(shard)) for shard in assignments)}",
            flush=True,
        )

        with tempfile.TemporaryDirectory(prefix="plotloom-python-suite-") as directory:
            temporary_root = Path(directory)
            logs: list[Path] = []
            handles: list[TextIO] = []
            started_at: list[float] = []
            parallel_started = time.perf_counter()
            try:
                for index, files in enumerate(assignments, start=1):
                    if received_sigterm is not None:
                        return sigterm_exit_code()
                    basetemp = temporary_root / f"worker-{index}"
                    log_path = temporary_root / f"worker-{index}.log"
                    handle = log_path.open("w", encoding="utf-8")
                    handles.append(handle)
                    started_at.append(time.perf_counter())
                    process = subprocess.Popen(
                        _command(files, basetemp),
                        cwd=root,
                        env=env,
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                        start_new_session=os.name == "posix",
                        text=True,
                    )
                    processes.append(process)
                    logs.append(log_path)
                    print(
                        f"[python-suite] START worker={index} "
                        f"cases={shard_case_counts[index - 1]} files={len(files)} "
                        f"basetemp={basetemp}",
                        flush=True,
                    )
                    if received_sigterm is not None:
                        return sigterm_exit_code()

                remaining = set(range(len(processes)))
                exit_codes = []
                last_heartbeat = parallel_started
                while remaining:
                    if received_sigterm is not None:
                        return sigterm_exit_code()
                    for index in sorted(remaining):
                        exit_code = processes[index].poll()
                        if exit_code is None:
                            continue
                        handles[index].flush()
                        print(
                            f"[python-suite] RESULT worker={index + 1} "
                            f"elapsed_seconds={time.perf_counter() - started_at[index]:.3f} "
                            f"exit_code={exit_code}",
                            flush=True,
                        )
                        print(
                            logs[index].read_text(encoding="utf-8"),
                            end="",
                            flush=True,
                        )
                        exit_codes.append(exit_code)
                        remaining.remove(index)
                    if received_sigterm is not None:
                        return sigterm_exit_code()
                    now = time.perf_counter()
                    if remaining and now - last_heartbeat >= 30:
                        print(
                            f"[python-suite] RUNNING elapsed_seconds={now - parallel_started:.1f} "
                            f"workers={','.join(str(index + 1) for index in sorted(remaining))}",
                            flush=True,
                        )
                        last_heartbeat = now
                    if remaining:
                        time.sleep(0.25)
                if received_sigterm is not None:
                    return sigterm_exit_code()
                result = 1 if any(exit_codes) else 0
                print(
                    f"[python-suite] SUMMARY elapsed_seconds="
                    f"{time.perf_counter() - parallel_started:.3f} exit_code={result}",
                    flush=True,
                )
                return result
            except KeyboardInterrupt:
                return 130
            except OSError as error:
                print(
                    f"Python worker could not start: {error}",
                    file=sys.stderr,
                    flush=True,
                )
                return 127
            finally:
                _stop_processes(processes)
                for handle in handles:
                    handle.close()
    except KeyboardInterrupt:
        _stop_processes(processes)
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm_handler)


def main() -> int:
    return run_python_suite()


if __name__ == "__main__":
    raise SystemExit(main())
