"""Bounded, passive failure context for the synthetic paid test boundary."""
import json
import os
import stat
from pathlib import Path

MAX_FILE_BYTES = 262_144
MAX_ITEMS = 8
MAX_MESSAGE_CHARS = 4096
STATES = frozenset({"RECEIVER_ACCEPTED", "TERMINAL_WITHOUT_HANDOFF", "HELD",
    "POSSIBLY_COMMITTED_UNKNOWN", "CAPABILITY_VERIFIED", "RECEIPT_AND_VALIDATED_DELIVERY",
    "NOT_ADMITTED", "UNKNOWN", "FAILED", "COMPLETED", "SETTLED", "OUTCOME_UNKNOWN",
    "reserved", "starting", "running", "completed", "failed", "settled", "outcome_unknown", "missing"})
REASONS = frozenset({"observation_stopped_or_runtime_elapsed", "RuntimeError", "ValueError",
    "OSError", "PermissionError", "FileNotFoundError", "TimeoutExpired", "SubprocessError",
    "UnicodeDecodeError", "JSONDecodeError", "AssertionError", "TypeError"})


def _integer(value):
    return value if type(value) is int and -(2**31) <= value < 2**31 else None


def _token(value, allowed):
    return value if isinstance(value, str) and value in allowed else "<omitted>"


def _records(rows):
    return {"count": len(rows), "items": [
        {key: _integer(row[key]) for key in ("pid", "ppid", "pgid", "parentPid", "exitCode") if key in row}
        for row in rows[:MAX_ITEMS] if isinstance(row, dict)]}


def _pids(rows):
    values = sorted({value for row in rows if isinstance(row, dict)
        and (value := _integer(row.get("pid"))) is not None})
    return {"count": len(values), "items": values[:MAX_ITEMS]}


def _read_case_file(root, relative):
    root = Path(root).absolute()
    path = root / relative
    if root.resolve(strict=True) != root or path.resolve(strict=True) != path:
        return "unsafe", {}
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1:
        return "unsafe", {}
    if before.st_size > MAX_FILE_BYTES:
        return "too-large", {}
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            return "changed", {}
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        return "too-large", {}
    value = json.loads(raw)
    return ("read", value) if isinstance(value, dict) else ("not-object", {})


def _outcome(root, relative, capsule=False):
    try:
        status, value = _read_case_file(root, relative)
    except FileNotFoundError:
        return {"file": "absent"}
    except Exception:  # noqa: BLE001 -- diagnostic reads cannot replace the original assertion
        return {"file": "unreadable"}
    result = {"file": status}
    selected = value.get("outcome", {}) if capsule else value
    if isinstance(selected, dict):
        for field in (("status", "reason") if capsule else ("outcome", "reason", "attemptState")):
            if field in selected:
                result[field] = _token(selected[field], REASONS if field == "reason" else STATES)
    if capsule and isinstance(value.get("actualFixtureChildTerminal"), dict):
        result["childExitCode"] = _integer(value["actualFixtureChildTerminal"].get("code"))
    return result


def _diagnostic(build):
    try:
        result = json.dumps(build(), sort_keys=True, ensure_ascii=True)
        return result if len(result) <= MAX_MESSAGE_CHARS else '{"diagnostics":"bounded-output-omitted"}'
    except Exception:  # noqa: BLE001 -- even diagnostic formatting must preserve the original failure
        return '{"diagnostics":"unavailable"}'


def cli_failure_context(case, startup, sandbox, expected):
    def build():
        invocations = {name: sum(row.get("invocation") == name for row in startup)
            for name in ("version", "login", "exec", "sandbox")}
        invocations["other"] = len(startup) - sum(invocations.values())
        return {"expectedSandboxCount": _integer(expected), "startupCount": len(startup),
            "sandboxCount": len(sandbox), "startupPids": _pids(startup), "sandboxPids": _pids(sandbox),
            "sandboxStartupPids": _pids([row for row in startup if row.get("invocation") == "sandbox"]),
            "invocations": invocations,
            "capsules": {mode: _outcome(case["root"], f"capsule-result-{mode}.json", capsule=True)
                for mode in ("success", "invalid-candidate")},
            "paid": _outcome(case["root"], "phase/paid-result.json")}
    return _diagnostic(build)


def settlement_failure_context(report):
    def build():
        # Exception text can contain arbitrary argv or paths. Retain categories only.
        errors = report["errors"]
        categories = ("identity:", "signal:", "refresh:", "direct child did not reap:",
            "owned test observer did not stop", "unresolved spawn/group ownership; cannot attest quiet",
            "incomplete final spawn journal row")
        groups = report.get("unresolvedGroups", {})
        return {"remaining": _records(report["remaining"]),
            "errors": {"count": len(errors), "categories": [
                next((prefix for prefix in categories if isinstance(error, str) and error.startswith(prefix)),
                    "<omitted>") for error in errors[:MAX_ITEMS]]},
            "observerError": None if report.get("observerError") is None else _token(report["observerError"], REASONS),
            "unresolvedSpawns": _records(report.get("unresolvedSpawns", [])),
            "unresolvedGroups": {"count": len(groups), "items": [
                {"pgid": _integer(int(key)) if str(key).isdigit() and len(str(key)) <= 10 else None,
                 "members": {"count": len(values), "items": [_integer(v) for v in values[:MAX_ITEMS]]}}
                for key, values in list(groups.items())[:MAX_ITEMS]]},
            "directExits": _records(report.get("directExits", []))}
    return _diagnostic(build)
