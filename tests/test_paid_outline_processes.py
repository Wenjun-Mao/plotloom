"""Lifecycle guards for fixture-owned processes; no product/provider execution."""
import json
import os
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from tests import paid_outline_processes as lifecycle
from tests.paid_outline_process_guard import exclusive

SUPPORT = str(Path(__file__).resolve().parents[1])


def test_owned_process_identity_is_independent_of_display_width(monkeypatch):
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.read()", "owned-long-command-" * 40],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        with monkeypatch.context() as columns:
            columns.setenv("COLUMNS", "40")
            narrow = lifecycle.process_identity(process.pid)
            columns.setenv("COLUMNS", "4096")
            wide = lifecycle.process_identity(process.pid)
        assert narrow == wide
        assert narrow["pgid"] == process.pid
    finally:
        process.communicate(timeout=5)
    assert process.returncode == 0


def program(root, ending):
    return [sys.executable, "-B", "-c", (
        "import subprocess,sys,time; "
        f"sys.path.insert(0,{SUPPORT!r}); "
        "from tests.paid_outline_processes import install_spawn_journal; "
        f"install_spawn_journal({str(root)!r}); "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'],start_new_session=True,"
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        + ending)]


def root_for(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "receipts").mkdir(mode=0o700)
    return tmp_path


@pytest.mark.parametrize("ending,timeout,error", [
    ("time.sleep(90)", 1.5, subprocess.TimeoutExpired),
    ("time.sleep(.3); sys.exit(3)", 10, subprocess.CalledProcessError),
])
def test_failure_settles_direct_and_detached_descendant(tmp_path, ending, timeout, error):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    with pytest.raises(error):
        owner.run(program(root, ending), timeout=timeout, capture_output=True, check=True)
    report = owner.settle()
    assert report["remaining"] == [] and report["errors"] == []
    assert len(report["knownIdentities"]) >= 2 and report["signals"]
    assert all(lifecycle.process_identity(row["pid"]) is None for row in report["knownIdentities"])
    assert json.loads((root / "process-settlement.json").read_bytes()) == report
    assert owner.settle() == report


def test_keyboard_interrupt_settles_owned_descendants(tmp_path, monkeypatch):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    real_popen = lifecycle._POPEN
    def interrupted(command, **kwargs):
        process = real_popen(command, **kwargs)
        if command[0] == sys.executable:
            original = process.communicate
            def communicate(**arguments):
                try:
                    original(timeout=1.5)
                except subprocess.TimeoutExpired:
                    raise KeyboardInterrupt
                raise AssertionError("fixture unexpectedly exited")
            process.communicate = communicate
        return process
    monkeypatch.setattr(lifecycle, "_POPEN", interrupted)
    with pytest.raises(KeyboardInterrupt):
        owner.run(program(root, "time.sleep(90)"), capture_output=True)
    assert owner.settle()["remaining"] == []


def test_unowned_journal_pid_is_never_a_signal_target(tmp_path):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    # This real caller identity is deliberately outside the owner's spawn tree.
    caller = lifecycle.process_identity(os.getpid())
    journal = root / "receipts/fixture-spawns.jsonl"
    journal.write_text(json.dumps({"parent": caller, "child": caller}) + "\n")
    journal.chmod(0o600)
    report = owner.settle()
    assert report["signals"] == [] and report["knownIdentities"] == []
    assert report["rejected"] and lifecycle.process_identity(os.getpid()) == caller


def test_changed_birth_identity_cannot_be_signalled(tmp_path):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    owner._stop.set()
    owner._observer.join(timeout=3)
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"], start_new_session=True)
    try:
        identity = lifecycle.process_identity(process.pid)
        obsolete = identity | {"birth": "obsolete process birth"}
        owner._remember(obsolete)
        # No group scan is permitted to rebind this deliberate stale identity.
        owner.groups.clear()
        report = owner.settle()
        assert report["signals"] == [] and report["remaining"] == []
        assert process.poll() is None
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=5)


def test_reused_numeric_group_never_adopts_or_signals_mocked_unrelated_pid(tmp_path, monkeypatch):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    owner._stop.set()
    owner._observer.join(timeout=3)
    old = {"pid": 90001, "ppid": 90000, "pgid": 90001,
        "birth": "old birth", "commandSha256": "a" * 64}
    owner._remember(old)
    reused = old | {"birth": "new unrelated birth", "commandSha256": "b" * 64}
    monkeypatch.setattr(lifecycle, "process_identity", lambda pid: reused)
    monkeypatch.setattr(lifecycle, "_probe", lambda command: (0, "90001\n"))
    def forbidden_signal(*arguments):
        raise AssertionError("numeric group reuse must never authorize a signal")
    monkeypatch.setattr(lifecycle.os, "kill", forbidden_signal)
    with pytest.raises(RuntimeError, match="settlement failed"):
        owner.settle()
    report = json.loads((root / "process-settlement.json").read_bytes())
    assert report["knownIdentities"] == [old] and report["signals"] == []
    assert report["unresolvedGroups"] == {"90001": [90001]}
    assert report["errors"] and report["remaining"] == []


def test_missed_fast_leader_is_reconciled_from_owned_descendant_journal(tmp_path):
    root = root_for(tmp_path)
    child_code = (
        "import subprocess,sys; "
        f"sys.path.insert(0,{SUPPORT!r}); "
        "from tests.paid_outline_processes import install_spawn_journal; "
        f"install_spawn_journal({str(root)!r}); "
        "subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'],start_new_session=True)"
    )
    parent_code = (
        "import subprocess,sys,time; "
        f"sys.path.insert(0,{SUPPORT!r}); "
        "import tests.paid_outline_processes as lifecycle; "
        "real=lifecycle.process_identity; parent=__import__('os').getpid(); "
        "lifecycle.process_identity=lambda pid: real(pid) if pid==parent else None; "
        f"lifecycle.install_spawn_journal({str(root)!r}); "
        f"leader=subprocess.Popen([sys.executable,'-B','-c',{child_code!r}],start_new_session=True); "
        "leader.wait(); time.sleep(90)"
    )
    owner = lifecycle.OwnedTestProcesses(root)
    with pytest.raises(subprocess.TimeoutExpired):
        owner.run([sys.executable, "-B", "-c", parent_code], timeout=1.5, capture_output=True)
    report = owner.settle()
    assert report["remaining"] == [] and report["unresolvedSpawns"] == [] and report["errors"] == []
    assert len(report["knownIdentities"]) >= 3
    rows = [json.loads(line) for line in (root / "receipts/fixture-spawns.jsonl").read_text().splitlines()]
    assert any(row["child"] is None and row["newSession"] is True for row in rows)


def test_unreconciled_missing_spawn_cannot_claim_quiet(tmp_path):
    root = root_for(tmp_path)
    owner = lifecycle.OwnedTestProcesses(root)
    owner._missing.append({"pid": 90002, "parentPid": 90001})
    with pytest.raises(RuntimeError, match="settlement failed"):
        owner.settle()
    report = json.loads((root / "process-settlement.json").read_bytes())
    assert report["signals"] == [] and report["unresolvedSpawns"] == [{"pid": 90002, "parentPid": 90001}]
    assert report["errors"]


@pytest.mark.parametrize("code", [0, 5])
def test_quick_non_journaling_command_has_captured_identity_and_real_exit(tmp_path, code):
    root = tmp_path
    root.chmod(0o700)
    assert not (root / "receipts").exists()
    with lifecycle.owned_processes(root) as owner:
        result = owner.run([sys.executable, "-c", f"raise SystemExit({code})"], capture_output=True)
        assert result.returncode == code
    report = owner.settle()
    assert report["errors"] == [] and report["remaining"] == [] and report["unresolvedSpawns"] == []
    assert len(report["knownIdentities"]) >= 2 and report["signals"] == []


@pytest.mark.parametrize("kind", ["file", "public-directory"])
def test_context_refuses_unsafe_existing_receipt_namespace(tmp_path, kind):
    tmp_path.chmod(0o700)
    receipt = tmp_path / "receipts"
    if kind == "file":
        receipt.write_bytes(b"foreign file")
    else:
        receipt.mkdir(mode=0o755)
    with pytest.raises((ValueError, FileExistsError)):
        lifecycle.OwnedTestProcesses(tmp_path)


def test_guard_record_name_is_published_only_after_complete_json(tmp_path, monkeypatch):
    from tests import paid_outline_process_guard as guard

    entered, release = Event(), Event()
    target, value = tmp_path / "ready.json", {"complete": "owned process identity"}
    real_dump = guard.json.dump
    def blocked_dump(*args, **kwargs):
        entered.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test writer was never released")
        return real_dump(*args, **kwargs)
    monkeypatch.setattr(guard.json, "dump", blocked_dump)
    with ThreadPoolExecutor(max_workers=1) as writer:
        future = writer.submit(exclusive, target, value)
        try:
            assert entered.wait(timeout=2)
            assert not target.exists()
        finally:
            release.set()
        future.result(timeout=5)
    assert json.loads(target.read_bytes()) == value
    assert target.stat().st_nlink == 1 and target.stat().st_mode & 0o777 == 0o600
    assert not target.with_name(target.name + ".pending").exists()
