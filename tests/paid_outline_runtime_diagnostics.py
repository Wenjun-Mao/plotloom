"""Opt-in metadata-only exception evidence for disposable paid-Outline tests."""
import json
import os
import sys
import traceback
from pathlib import Path


def install_runtime_tree_diagnostics(case: Path, source: Path) -> None:
    if os.environ.get("PLOTLOOM_TEST_RUNTIME_TREE_DIAGNOSTIC") != "1":
        return
    case, source = case.resolve(strict=True), source.resolve(strict=True)
    receipts = case / "receipts"
    target = source / "src/plotloom/codex_exec_runtime_tree.py"
    seen = set()

    def inventory():
        values = {}
        for path in (source / "src").rglob("*.pyc"):
            if len(values) >= 5000:
                raise ValueError("test bytecode inventory exceeds diagnostic bound")
            try:
                info = path.lstat()
            except FileNotFoundError:
                values[str(path.relative_to(source))] = {"observationError": "disappeared"}
                continue
            values[str(path.relative_to(source))] = {
                "inode": info.st_ino, "size": info.st_size, "mtimeNs": info.st_mtime_ns,
            }
        return values

    def save(label, values):
        path = receipts / f"runtime-tree-diagnostic-{os.getpid()}-{label}.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(values, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())

    initial = inventory()
    save("start", {"pid": os.getpid(), "ppid": os.getppid(),
        "source": str(source), "case": str(case), "bytecode": initial})

    def record_exception(frame, kind, error):
        current = inventory()
        metadata = {}
        for name in ("root", "path", "prefix", "name", "relative"):
            value = frame.f_locals.get(name)
            if isinstance(value, (str, Path, tuple)):
                metadata[name] = str(value)
        save(str(len(seen)), {"pid": os.getpid(), "exceptionType": kind.__name__,
            "message": str(error), "filename": frame.f_code.co_filename,
            "line": frame.f_lineno, "function": frame.f_code.co_name,
            "metadata": metadata, "stack": [{"filename": item.filename,
                "line": item.lineno, "function": item.name}
                for item in traceback.extract_stack(frame)],
            "bytecode": current, "createdBytecode": sorted(current.keys() - initial.keys()),
            "changedBytecode": sorted(k for k in current.keys() & initial.keys()
                if current[k] != initial[k])})

    def exception_trace(frame, event, arg):
        if event == "exception":
            kind, error, _tb = arg
            if kind.__name__ == "CodexExecRuntimeTreeError" and id(error) not in seen:
                seen.add(id(error))
                try:
                    record_exception(frame, kind, error)
                except (OSError, ValueError):
                    # Missing diagnostic evidence never replaces the actual refusal.
                    pass
        return exception_trace

    def trace(frame, event, _arg):
        if event == "call" and frame.f_code.co_filename == str(target):
            frame.f_trace_lines = False
            frame.f_trace_opcodes = False
            return exception_trace
        return None

    sys.settrace(trace)
