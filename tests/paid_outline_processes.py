"""Identity-bound ownership for disposable paid-source test subprocesses.

Only exact spawned children, their journaled descendants and their private
process groups are observed. No global process inventory or unrelated PID is a
cleanup target. This is test lifecycle support, not product dispatch authority.
"""
import json
import os
import signal
import stat
import subprocess
import time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from threading import Event, RLock, Thread

from tests.paid_outline_process_guard import (
    prepare_guard,
    release_guard,
    target_returncode,
)

_POPEN = subprocess.Popen


def _probe(command):
    process = _POPEN(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, _stderr = process.communicate(timeout=2)
    except BaseException:
        process.kill()
        process.wait()
        raise
    return process.returncode, stdout.decode("utf-8", "strict")


def process_identity(pid):
    code, text = _probe(["/bin/ps", "-p", str(pid), "-o", "pid=,ppid=,pgid=,lstart=,command="])
    if code == 1 and not text.strip():
        return None
    if code != 0:
        raise RuntimeError("owned test process identity unavailable")
    values = text.strip().split(maxsplit=8)
    if len(values) != 9 or int(values[0]) != pid:
        raise RuntimeError("incomplete owned test process identity")
    return {"pid": pid, "ppid": int(values[1]), "pgid": int(values[2]),
        "birth": " ".join(values[3:8]), "commandSha256": sha256(values[8].encode()).hexdigest()}


def _same_process(actual, expected):
    return actual is not None and all(actual[key] == expected[key] for key in ("pid", "birth", "commandSha256"))


def journal_spawn(case_root, child_pid, *, parent_pid=None, new_session=None):
    parent = process_identity(parent_pid or os.getpid())
    child = process_identity(child_pid)
    target = Path(case_root) / "receipts/fixture-spawns.jsonl"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise RuntimeError("unsafe owned test spawn journal")
        row = json.dumps({"parent": parent, "child": child, "spawnedPid": child_pid,
            "newSession": new_session}, sort_keys=True, separators=(",", ":")) + "\n"
        encoded = row.encode()
        if os.write(descriptor, encoded) != len(encoded):
            raise RuntimeError("incomplete owned test spawn journal write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def install_spawn_journal(case_root):
    """Observe external Popen only; every returned result stays the real result."""
    real_popen = subprocess.Popen
    def observed(command, *args, **kwargs):
        process = real_popen(command, *args, **kwargs)
        # Missing a fast leader's ps row is UNKNOWN, never evidence of no spawn.
        journal_spawn(case_root, process.pid, new_session=kwargs.get("start_new_session", False))
        return process
    subprocess.Popen = observed


class OwnedTestProcesses:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        for directory, create in ((self.root, False), (self.root / "receipts", True)):
            if create:
                directory.mkdir(mode=0o700, exist_ok=True)
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o700 or directory.resolve(strict=True) != directory):
                raise ValueError("owned fixture process roots require physical owner-0700 directories")
        self.processes = []
        self.known = {}
        self.groups = set()
        self.events = []
        self.errors = []
        self.rejected = []
        self._terminal = set()
        self._report = None
        self._journal_rows = 0
        self._pending = []
        self._missing = []
        self._unresolved_groups = {}
        self._lock = RLock()
        self._stop = Event()
        self._observer = Thread(target=self._watch, name="paid-source-test-ownership", daemon=True)
        self._observer_error = None
        self._observer.start()

    def _remember(self, value):
        if value["pgid"] == os.getpgrp() or value["pid"] == os.getpid():
            raise RuntimeError("fixture cannot own its caller process/group")
        key = (value["pid"], value["birth"], value["commandSha256"])
        self.known[key] = value
        self.groups.add(value["pgid"])

    def _reap(self):
        for process in self.processes:
            process.poll()

    def _refresh(self):
        with self._lock:
            journal = self.root / "receipts/fixture-spawns.jsonl"
            if journal.exists():
                raw = journal.read_bytes()
                if len(raw) > 2_000_000:
                    raise RuntimeError("owned test spawn journal exceeded bound")
                # An append in another process can be between write and fsync.
                # Defer only its unterminated last row; never drop malformed rows.
                complete = raw[:raw.rfind(b"\n") + 1].splitlines()
                self._pending.extend(json.loads(line) for line in complete[self._journal_rows:])
                pending = self._pending
                # Newly journaled parents may themselves have been journaled in
                # another process; resolve the finite ancestry graph in order.
                for _ in range(len(pending) + 1):
                    changed = False
                    # A descendant's trusted spawn record can retain the exact
                    # birth/command of its already-exited immediate parent.
                    for missing in self._missing:
                        for row in pending:
                            candidate = row["parent"]
                            if (candidate is not None and candidate["pid"] == missing["pid"]
                                    and candidate["ppid"] == missing["parentPid"]
                                    and not any(_same_process(candidate, value) for value in self.known.values())):
                                self._remember(candidate)
                                changed = True
                    for row in pending:
                        parent, child = row["parent"], row["child"]
                        if child is None:
                            if parent is not None and any(_same_process(parent, value) for value in self.known.values()):
                                missing = {"pid": row["spawnedPid"], "parentPid": parent["pid"]}
                                if missing not in self._missing:
                                    self._missing.append(missing)
                                    changed = True
                            continue
                        if parent is None:
                            continue
                        if child["ppid"] != parent["pid"]:
                            continue
                        owners = [value for value in self.known.values() if _same_process(parent, value)]
                        if not owners:
                            continue
                        actual_parent = process_identity(parent["pid"]) if parent["pgid"] != owners[0]["pgid"] else None
                        if _same_process(actual_parent, parent) and actual_parent["pgid"] == parent["pgid"]:
                            self._remember(parent)
                        key = (child["pid"], child["birth"], child["commandSha256"])
                        if key not in self.known:
                            actual_child = process_identity(child["pid"])
                            if (actual_child is not None and
                                    (not _same_process(actual_child, child) or actual_child["ppid"] not in {parent["pid"], 1})):
                                self.rejected.append({"reason": "child identity/ancestry changed", "child": child})
                                continue
                            self._remember(child)
                            changed = True
                    if not changed:
                        break
                unresolved = [row for row in pending if row["child"] is None or
                    not any(_same_process(row["child"], item) for item in self.known.values())]
                self._pending = unresolved
                self._journal_rows = len(complete)
            # A numeric group is only an observation scope. New cleanup targets
            # need a live exact anchor and actual parent ancestry in that group.
            for group in tuple(self.groups):
                code, output = _probe(["/usr/bin/pgrep", "-g", str(group)])
                if code not in {0, 1}:
                    raise RuntimeError("owned test group observation failed")
                if code == 1 and not output.strip():
                    self.groups.discard(group)
                    self._unresolved_groups.pop(group, None)
                    continue
                anchors = set()
                for expected in tuple(self.known.values()):
                    if expected["pgid"] != group:
                        continue
                    actual = process_identity(expected["pid"])
                    if _same_process(actual, expected) and actual["pgid"] == group:
                        anchors.add(actual["pid"])
                remaining = set(map(int, output.split())) - anchors
                while anchors and remaining:
                    discovered = set()
                    for pid in remaining:
                        current = process_identity(pid)
                        if current is not None and current["pgid"] == group and current["ppid"] in anchors:
                            self._remember(current)
                            discovered.add(pid)
                    if not discovered:
                        break
                    anchors.update(discovered)
                    remaining.difference_update(discovered)
                if remaining:
                    self._unresolved_groups[group] = sorted(remaining)
                else:
                    self._unresolved_groups.pop(group, None)

    def _watch(self):
        while not self._stop.wait(0.1):
            try:
                self._refresh()
            except BaseException as error:  # noqa: BLE001 -- observer failure must fail settlement after known-child cleanup
                self._observer_error = error
                return

    def run(self, command, *, timeout=60, capture_output=False, text=False, check=False,
            stdout=None, stderr=None, **kwargs):
        if kwargs.pop("start_new_session", True) is not True:
            raise ValueError("owned test commands require their own session")
        if capture_output:
            if stdout is not None or stderr is not None:
                raise ValueError("capture_output conflicts with streams")
            stdout = stderr = subprocess.PIPE
        if kwargs.get("shell"):
            raise ValueError("owned fixture commands require an explicit argv")
        guard, guard_argv = prepare_guard(self.root, command)
        process = _POPEN(guard_argv, stdout=stdout, stderr=stderr, text=text, start_new_session=True, **kwargs)
        try:
            with self._lock:
                self.processes.append(process)
                self.groups.add(process.pid)
                release_guard(guard, process, identify=process_identity, remember=self._remember, timeout=timeout)
            out, err = process.communicate(timeout=timeout)
            result = subprocess.CompletedProcess(command, target_returncode(guard, process), out, err)
            if check:
                result.check_returncode()
            return result
        except BaseException:
            self.settle()
            raise

    def settle(self):
        if self._report is not None:
            if self._report["remaining"] or self._report["errors"]:
                raise RuntimeError("owned test process settlement failed; evidence retained")
            return self._report
        self._stop.set()
        self._observer.join(timeout=3)
        if self._observer.is_alive():
            self.errors.append("owned test observer did not stop")
        if self._observer_error:
            self.errors.append(type(self._observer_error).__name__ + ": " + str(self._observer_error))
        self._safe_refresh()
        # Give successful workers/reapers a natural completion interval first.
        deadline = time.monotonic() + 2
        while self._live() and time.monotonic() < deadline:
            time.sleep(0.05)
            self._safe_refresh()
        for sig, grace in ((signal.SIGTERM, 2), (signal.SIGKILL, 2)):
            live = self._live()
            if not live:
                break
            for expected in reversed(live):
                try:
                    actual = process_identity(expected["pid"])
                    if _same_process(actual, expected) and actual["pgid"] == expected["pgid"]:
                        os.kill(expected["pid"], sig)
                        self.events.append({"signal": int(sig), "identity": expected})
                except ProcessLookupError:
                    pass
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                    self.errors.append("signal: " + str(error))
            until = time.monotonic() + grace
            while self._live() and time.monotonic() < until:
                time.sleep(0.05)
                self._safe_refresh()
        for process in self.processes:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.errors.append("direct child did not reap: " + str(process.pid))
        self._safe_refresh()
        live = self._live()
        unresolved_spawns = [item for item in self._missing
            if not any(value["pid"] == item["pid"] and value["ppid"] == item["parentPid"] for value in self.known.values())]
        if unresolved_spawns or self._unresolved_groups:
            self.errors.append("unresolved spawn/group ownership; cannot attest quiet")
        self.rejected.extend({"reason": "unowned ancestry", "child": row["child"]} for row in self._pending
            if row["child"] is not None)
        journal = self.root / "receipts/fixture-spawns.jsonl"
        if journal.exists() and not journal.read_bytes().endswith(b"\n"):
            self.errors.append("incomplete final spawn journal row")
        report = {"syntheticEvidence": True, "knownIdentities": list(self.known.values()),
            "groups": sorted({value["pgid"] for value in self.known.values()}), "signals": self.events, "remaining": live,
            "errors": self.errors, "rejected": self.rejected,
            "unresolvedSpawns": unresolved_spawns, "unresolvedGroups": self._unresolved_groups,
            "observerError": type(self._observer_error).__name__ if self._observer_error else None,
            "directExits": [{"pid": p.pid, "exitCode": p.returncode} for p in self.processes]}
        target = self.root / "process-settlement.json"
        with target.open("x", encoding="utf-8") as stream:
            os.chmod(target, 0o600)
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._report = report
        if live or self.errors:
            raise RuntimeError("owned test process settlement failed; evidence retained")
        return report

    def _live(self):
        self._reap()
        live = []
        for key, expected in tuple(self.known.items()):
            if key in self._terminal:
                continue
            try:
                actual = process_identity(expected["pid"])
                if _same_process(actual, expected):
                    live.append(actual)
                else:
                    self._terminal.add(key)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                self.errors.append("identity: " + str(error))
        return live

    def _safe_refresh(self):
        try:
            self._reap()
            self._refresh()
        except Exception as error:  # noqa: BLE001 -- malformed journal cannot prevent cleanup of known identities
            self.errors.append("refresh: " + str(error))


@contextmanager
def owned_processes(root):
    owner = OwnedTestProcesses(root)
    try:
        yield owner
    finally:
        owner.settle()
