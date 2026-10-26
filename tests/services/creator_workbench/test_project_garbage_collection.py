"""Real SQLite/private-file collection through the native operator transport."""
import json
import shutil
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import codex_client
import pytest
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_test_support import _attempt, _insert_attempt_row
from host_bridge import QueueBridge, handler_for

from plotloom.codex_exec_contracts import transition_exec_attempt
from plotloom.codex_exec_gc_contracts import ProjectGarbageCollectionRequest
from tests.services.creator_workbench.test_codex_exec_capacity_retirement import (
    consent,
    revoked_unknown,
)


def deleted_project(supervisor, *, revoked=True):
    original = _attempt()
    current = transition_exec_attempt(original, state="queued")
    _insert_attempt_row(supervisor, original, current)
    home = supervisor.outputs_root / ("deleted__" + str(original.project_id))
    path = supervisor.private_root / "attempts" / str(original.attempt_id)
    path.mkdir(parents=True)
    (path / "private.log").write_text("private historical evidence")
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET project_home=? WHERE attempt_id=?", (str(home), str(original.attempt_id)))
        connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES (?,0)", (str(original.attempt_id),))
        connection.execute("INSERT INTO exec_process_exits VALUES (?,?)", (str(original.attempt_id), '{}'))
        connection.execute("INSERT INTO exec_recovery_evidence VALUES (?,?,?)", (str(original.attempt_id), '{}', '{}'))
        if revoked:
            connection.execute("INSERT INTO exec_project_revocations VALUES (?,?,?,1)", (str(original.project_id), str(home), "f"*64))
    return original, path, ProjectGarbageCollectionRequest(project_id=original.project_id)


def allow(supervisor, request):
    preview = supervisor.project_gc_preview(request)
    assert preview.eligible, preview.blockers
    return request.model_copy(update={"expected_preview_hash": preview.preview_hash})


def test_native_cli_owned_gc_erases_only_deleted_project_and_blocks_late_callbacks(supervisor, tmp_path, monkeypatch, capsys):
    original, path, request = deleted_project(supervisor)
    other, other_path, _ = deleted_project(supervisor, revoked=False)
    retained = dict(supervisor._row(other.attempt_id))
    bridge = QueueBridge(tmp_path / "codex", tmp_path / "settings", "private-token")
    monkeypatch.setattr(bridge, "exec_supervisor", lambda: supervisor)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge))
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    token = tmp_path / "token"; token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", f"http://127.0.0.1:{server.server_port}")
    for method in ("_drain_queue", "_start_worker", "_prove_group_absent"):
        monkeypatch.setattr(supervisor, method, lambda *_a: pytest.fail("GC and missing-row status must not dispatch or probe stale PIDs"))
    try:
        assert codex_client.main(["exec-project-gc-preview", "--packet-json", request.model_dump_json(by_alias=True)]) == 0
        preview = json.loads(capsys.readouterr().out)
        assert preview["attemptIds"] == [str(original.attempt_id)] and preview["privateFileCount"] == 1
        request.expected_preview_hash = preview["previewHash"]
        assert codex_client.main(["exec-project-gc", "--packet-json", request.model_dump_json(by_alias=True)]) == 0
        assert json.loads(capsys.readouterr().out)["applied"]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    assert not path.exists() and supervisor._row(original.attempt_id) is None
    assert dict(supervisor._row(other.attempt_id)) == retained and other_path.is_dir()
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT COUNT(*) FROM exec_project_revocations").fetchone()[0] == 1
        for table in ("exec_queue", "exec_process_exits", "exec_recovery_evidence", "exec_capacity_retirements"):
            assert not connection.execute(f"SELECT * FROM {table} WHERE attempt_id=?", (str(original.attempt_id),)).fetchall()
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    monkeypatch.setattr(supervisor, "_namespace_assert_attempt", lambda *_a, **_k: None)
    assert supervisor.status(original.attempt_id).state == "not_found"
    for action in (supervisor.admit, supervisor.cancel, supervisor.resume, supervisor._store):
        with pytest.raises(CodexExecSupervisorError):
            action(original)
    assert supervisor._row(original.attempt_id) is None
    # Empty explicit collection is idempotent after rereading the current target.
    assert supervisor.collect_deleted_project(allow(supervisor, request)).attempt_ids == []


@pytest.mark.parametrize("defect", ["unrevoked", "home", "symlink_home", "private_path", "private_symlink", "nested_fifo", "hardlink", "slot", "validator", "queue", "active", "different_preview", "no_preview"])
def test_collection_refuses_unsafe_or_changed_target(supervisor, tmp_path, defect):
    original, path, request = deleted_project(supervisor, revoked=defect != "unrevoked")
    if defect == "unrevoked":
        with pytest.raises(CodexExecSupervisorError, match="revocation"):
            supervisor.project_gc_preview(request)
        return
    request = allow(supervisor, request)
    with closing(supervisor._connect()) as connection:
        home = Path(connection.execute("SELECT project_home FROM exec_project_revocations").fetchone()[0])
        if defect == "home": home.mkdir()
        if defect == "symlink_home": home.symlink_to(tmp_path, target_is_directory=True)
        if defect == "private_path": connection.execute("UPDATE exec_attempts SET private_dir=? WHERE attempt_id=?", (str(tmp_path), str(original.attempt_id)))
        if defect == "private_symlink":
            shutil.rmtree(path); path.symlink_to(tmp_path, target_is_directory=True)
        if defect == "nested_fifo":
            import os
            os.mkfifo(path / "special")
        if defect == "hardlink":
            import os
            os.link(path / "private.log", path / "linked.log")
        if defect == "slot": connection.execute("INSERT INTO exec_slot VALUES (?, 'text')", (str(original.attempt_id),))
        if defect == "validator": connection.execute("INSERT INTO exec_validation_process VALUES (?, 'step', 'spawn_intent', NULL,NULL,NULL,1)", (str(original.attempt_id),))
        if defect == "queue": connection.execute("UPDATE exec_queue SET enabled=1")
        if defect == "active": connection.execute("UPDATE exec_attempts SET status_json=? WHERE attempt_id=?", (original.model_dump_json(by_alias=True), str(original.attempt_id)))
    if defect in {"slot", "validator", "queue", "active"}:
        preview = supervisor.project_gc_preview(request)
        assert not preview.eligible
        request.expected_preview_hash = preview.preview_hash
    if defect == "different_preview": (path / "private.log").write_text("changed")
    if defect == "no_preview": request.expected_preview_hash = None
    with pytest.raises(CodexExecSupervisorError): supervisor.collect_deleted_project(request)
    assert supervisor._row(original.attempt_id) is not None and path.exists()


def test_interrupted_filesystem_erasure_keeps_rows_and_retry_requires_new_preview(supervisor, monkeypatch):
    original, path, request = deleted_project(supervisor)
    request = allow(supervisor, request)
    from codex_exec_supervisor_gc import _erase_private_tree
    real_remove = _erase_private_tree
    def interrupted(target):
        (target / "private.log").unlink()
        raise OSError("injected interrupted erasure")
    monkeypatch.setattr("codex_exec_supervisor_gc._erase_private_tree", interrupted)
    with pytest.raises(OSError, match="interrupted"): supervisor.collect_deleted_project(request)
    assert supervisor._row(original.attempt_id) is not None and path.is_dir()
    monkeypatch.setattr("codex_exec_supervisor_gc._erase_private_tree", real_remove)
    with pytest.raises(CodexExecSupervisorError, match="preview changed"): supervisor.collect_deleted_project(request)
    assert supervisor.collect_deleted_project(allow(supervisor, request)).applied
    assert not path.exists() and supervisor._row(original.attempt_id) is None


def test_unknown_collection_uses_existing_immutable_retirement_without_new_pid_claim(supervisor, monkeypatch):
    original, unknown, retirement = revoked_unknown(supervisor, monkeypatch)
    gc = ProjectGarbageCollectionRequest(project_id=original.project_id)
    assert not supervisor.project_gc_preview(gc).eligible
    supervisor.retire_local_capacity(consent(supervisor, retirement))
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_a: pytest.fail("old PID reuse must not be reprobed"))
    assert supervisor._load(supervisor._row(original.attempt_id)).attempt == unknown
    assert supervisor.collect_deleted_project(allow(supervisor, gc)).applied
    assert supervisor._row(original.attempt_id) is None and supervisor._publication_revoked(original.project_id)


def test_child_symlinks_are_bound_inert_entries_and_never_touch_external_target(supervisor, tmp_path):
    original, path, request = deleted_project(supervisor)
    target = tmp_path / "external-sentinel"; target.mkdir()
    sentinel = target / "keep"; sentinel.write_text("keep external target unchanged")
    link = path / "apply_patch"; link.symlink_to(target, target_is_directory=True)
    dangling = path / "applypatch"; dangling.symlink_to(tmp_path / "absent-executable")
    preview = supervisor.project_gc_preview(request)
    assert preview.private_file_count == 1 and preview.private_symlink_count == 2
    request.expected_preview_hash = preview.preview_hash
    # Replacing link text/identity invalidates consent, even for another absent target.
    dangling.unlink(); dangling.symlink_to(tmp_path / "different-absent-executable")
    with pytest.raises(CodexExecSupervisorError, match="preview changed"):
        supervisor.collect_deleted_project(request)
    assert supervisor.collect_deleted_project(allow(supervisor, request)).applied
    assert sentinel.read_text() == "keep external target unchanged"
    assert target.is_dir() and not path.exists() and supervisor._row(original.attempt_id) is None


def test_new_foreign_fk_ownership_refuses_before_private_evidence_erasure(supervisor):
    original, path, request = deleted_project(supervisor)
    with closing(supervisor._connect()) as connection:
        connection.execute("CREATE TABLE future_owner(attempt_id TEXT REFERENCES exec_attempts(attempt_id))")
        connection.execute("INSERT INTO future_owner VALUES (?)", (str(original.attempt_id),))
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        supervisor.collect_deleted_project(allow(supervisor, request))
    assert supervisor._row(original.attempt_id) is not None
    assert (path / "private.log").read_text() == "private historical evidence"


def test_gc_bridge_auth_and_cli_lost_ack_never_retry(supervisor, tmp_path, monkeypatch, capsys):
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    _original, path, request = deleted_project(supervisor)
    bridge = QueueBridge(tmp_path / "codex", tmp_path / "settings", "private-token")
    monkeypatch.setattr(bridge, "exec_supervisor", lambda: pytest.fail("unauthenticated request reached supervisor"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge))
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with pytest.raises(HTTPError) as denied:
            urlopen(Request(f"http://127.0.0.1:{server.server_port}/exec-project-gc", data=request.model_dump_json().encode()), timeout=3)
        assert denied.value.code == 401 and path.is_dir()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    token = tmp_path / "token"; token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    calls = []
    def lost_ack(call, **_kwargs):
        calls.append(call)
        raise TimeoutError("ack lost after possible commit")
    monkeypatch.setattr(codex_client, "urlopen", lost_ack)
    assert codex_client.main(["exec-project-gc", "--packet-json", request.model_dump_json()]) == 1
    assert len(calls) == 1 and "private-token" not in capsys.readouterr().err


def test_renamed_current_project_is_never_collected(supervisor, tmp_path, monkeypatch):
    from tests.services.creator_workbench.test_project_abandonment import (
        unknown_project,
    )
    _original, _unknown, packet = unknown_project(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_a: True)
    preview = supervisor.abandonment_preview(packet)
    supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": preview.preview_hash}))
    Path(packet.project_home).rename(supervisor.outputs_root / "renamed-current-project")
    with pytest.raises(CodexExecSupervisorError, match="still present"):
        supervisor.project_gc_preview(ProjectGarbageCollectionRequest(project_id=packet.project_id))


def test_replaced_attempt_parent_link_refuses_without_touching_external_target(supervisor, tmp_path):
    original, path, request = deleted_project(supervisor)
    request = allow(supervisor, request)
    parent = path.parent
    retained = parent.with_name("saved-attempts")
    parent.rename(retained)
    target = tmp_path / "external-attempts"; target.mkdir()
    sentinel = target / str(original.attempt_id); sentinel.mkdir()
    (sentinel / "keep").write_text("untouched")
    parent.symlink_to(target, target_is_directory=True)
    with pytest.raises(CodexExecSupervisorError): supervisor.collect_deleted_project(request)
    assert (sentinel / "keep").read_text() == "untouched"
    assert (retained / path.name / "private.log").is_file()


def test_preview_read_ignores_only_access_time_and_retains_exact_evidence(supervisor):
    import os
    _original, path, request = deleted_project(supervisor)
    evidence = path / "private.log"
    initial = evidence.stat()
    os.utime(evidence, ns=(initial.st_atime_ns - 2_000_000_000, initial.st_mtime_ns))
    before = evidence.stat()
    assert supervisor.project_gc_preview(request).eligible
    after = evidence.stat()
    assert after.st_atime_ns > before.st_atime_ns
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_ctime_ns == before.st_ctime_ns
    assert evidence.read_text() == "private historical evidence"


def test_preview_refuses_subsecond_evidence_change_during_read(supervisor, monkeypatch):
    import os
    import codex_exec_supervisor_gc as owner
    _original, path, request = deleted_project(supervisor)
    evidence = path / "private.log"
    target = evidence.stat()
    real_fstat = os.fstat
    observations = 0

    def changed(descriptor):
        nonlocal observations
        result = real_fstat(descriptor)
        if result.st_ino == target.st_ino:
            observations += 1
            if observations == 2:
                os.utime(evidence, ns=(result.st_atime_ns, result.st_mtime_ns + 1))
                result = real_fstat(descriptor)
        return result

    monkeypatch.setattr(owner.os, "fstat", changed)
    with pytest.raises(CodexExecSupervisorError, match="changed during preview"):
        supervisor.project_gc_preview(request)
    assert evidence.is_file()
