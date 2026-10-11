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


def _stop_processes(processes: Sequence[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is not None:
            continue
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                process.wait()


def run_python_suite(
    *, root: Path = ROOT, environment: dict[str, str] | None = None
) -> int:
    env = os.environ.copy() if environment is None else environment.copy()
    if env.get("PYTEST_ADDOPTS"):
        print(
            "Python suite refuses ambient PYTEST_ADDOPTS", file=sys.stderr, flush=True
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
    collected = subprocess.run(
        collector,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if collected.stderr:
        print(collected.stderr, end="", file=sys.stderr, flush=True)
    if collected.returncode:
        print(collected.stdout, end="", flush=True)
        return collected.returncode
    try:
        cases = parse_collected_cases(collected.stdout, root=root)
        assignments = partition_test_files(cases)
    except SuiteError as error:
        print(f"Python suite refused collection: {error}", file=sys.stderr, flush=True)
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
        processes: list[subprocess.Popen[str]] = []
        logs: list[Path] = []
        handles: list[TextIO] = []
        started_at: list[float] = []
        parallel_started = time.perf_counter()
        try:
            for index, files in enumerate(assignments, start=1):
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

            remaining = set(range(len(processes)))
            exit_codes = []
            last_heartbeat = parallel_started
            while remaining:
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
                    print(logs[index].read_text(encoding="utf-8"), end="", flush=True)
                    exit_codes.append(exit_code)
                    remaining.remove(index)
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
            result = 1 if any(exit_codes) else 0
            print(
                f"[python-suite] SUMMARY elapsed_seconds="
                f"{time.perf_counter() - parallel_started:.3f} exit_code={result}",
                flush=True,
            )
            return result
        except KeyboardInterrupt:
            _stop_processes(processes)
            return 130
        except OSError as error:
            print(
                f"Python worker could not start: {error}", file=sys.stderr, flush=True
            )
            _stop_processes(processes)
            return 127
        finally:
            for handle in handles:
                handle.close()


def main() -> int:
    return run_python_suite()


if __name__ == "__main__":
    raise SystemExit(main())
