"""Fake provider IO with real frozen Node validation and rendering.

This does not emulate the Mac sandbox. It compares its full production command,
then runs the real Node tail in the existing owned validator process group.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from tests.paid_outline_processes import install_spawn_journal, journal_spawn


def sandbox(case, executable, arguments):
    allocation = json.loads((case / "bundle/paid-allocation.json").read_bytes())
    namespace = allocation["namespace"]
    source = Path(namespace["sourceRoot"]["path"])
    sys.path.insert(0, str(source / "src"))
    sys.path.insert(0, str(source / "services/creator_workbench"))
    from plotloom import codex_exec_profile
    codex_exec_profile.NODE_OPENSSL_CONFIG = case / "provider-free-host/openssl.cnf"
    from codex_exec_supervisor_environment import CodexExecSupervisorEnvironmentMixin
    from codex_exec_supervisor_validation import CodexExecSupervisorValidationMixin

    from plotloom.codex_exec_profile import CodexExecProfile
    from plotloom.codex_exec_resources import codex_exec_source_resources
    from plotloom.codex_exec_validation import (
        expand_validation_argv,
        validation_plan_from_package,
    )
    from tests.paid_outline_cli_runtime import observe_sandbox_imports
    observe_sandbox_imports(case, source, __file__)

    profile = CodexExecProfile.model_validate(namespace["profile"])
    attempt = namespace["attempt"]
    job = Path(allocation["projectHome"]["path"]) / "outputs/creative-handoff/jobs" / attempt["jobId"]
    private = Path(namespace["privateRoot"]["path"]) / "attempts" / attempt["attemptId"]
    validation = private / "validation"
    package = json.loads((job / "package/request.json").read_bytes())
    plan = validation_plan_from_package(package)
    resources = codex_exec_source_resources(source, package)
    owner = SimpleNamespace(executable=executable, codex_home=case / "auth-home",
        _permission_filesystem_config=CodexExecSupervisorEnvironmentMixin._permission_filesystem_config)
    allowed = []
    for step in plan.steps:
        if step.program != "node":
            raise ValueError("Outline fixture only permits the frozen Node stage")
        tail = expand_validation_argv(step, source_root=source,
            submodule_root=source / "third_party/shuohao-skills", job_root=job,
            candidate_filename=plan.candidate_filename, tool_paths=dict(resources.tools))
        full = CodexExecSupervisorValidationMixin._sandbox_validation_command(
            owner, profile, job, private, validation, tail, resources)
        allowed.append((full, tail))
    matches = [tail for full, tail in allowed if full == [str(executable), *arguments]]
    if len(matches) != 1 or Path.cwd() != validation:
        raise ValueError("fixture refused non-frozen sandbox argv or working directory")
    # Keep this wrapper's birth/command identity stable for the real host owner.
    # Node inherits its private process group and the actual report streams.
    child = subprocess.Popen(matches[0])
    return child.wait()


def main(executable, arguments, version):
    from datetime import UTC, datetime
    from uuid import uuid4

    case = executable.parent
    journal_spawn(case, os.getpid(), parent_pid=os.getppid())
    install_spawn_journal(case)
    if arguments == ["--version"]:
        print(version)
        return 0
    if arguments[-2:] == ["login", "status"]:
        return 0
    if arguments and arguments[0] == "sandbox":
        return sandbox(case, executable, arguments)
    sys.stdin.read()
    request = json.loads(Path("../package/request.json").read_text())
    candidate = json.loads((case / "provider-output.json").read_bytes())
    candidate["source"] = request["source"]["title"]
    Path("outline.json").write_text(json.dumps(candidate, ensure_ascii=False))
    session, now = uuid4(), datetime.now(UTC)
    day = now.date()
    root = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"rollout-{now.strftime('%Y-%m-%dT%H-%M-%S')}-{session}.jsonl").write_text(
        json.dumps({"type": "session_meta", "payload": {"id": str(session)}, "ordinal": 0}) + "\n")
    for event in ({"type": "thread.started", "thread_id": str(session)},
            {"type": "turn.started"}, {"type": "turn.completed"}):
        print(json.dumps(event), flush=True)
    return 0
