"""Shared fixtures and builders for creator-workbench Codex Exec tests."""
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from plotloom.codex_exec_contracts import CodexExecAttempt
from plotloom.codex_exec_runtime import package_tree_hash
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import request_hash
from plotloom.project_storage import ProjectFolderStorage
from plotloom.codex_exec_profile import SUPPORTED_CLI_VERSION, build_codex_exec_profile


def _attempt(state="spawn_intent"):
    return CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ch_" + "a" * 24,
        operationKey="outline",
        domain="text",
        requestHash="a" * 64,
        packageHash="b" * 64,
        profileHash="c" * 64,
        reservedImageOutputs=0,
        state=state,
        **({"processId": 43210, "processGroupId": 43210, "processBirthIdentity": "fixture-process"}
           if state == "running" else {}),
    )


def _insert_attempt_row(supervisor, attempt, status_attempt):
    with closing(supervisor._connect()) as connection:
        connection.execute(
            "INSERT INTO exec_attempts "
            "(attempt_id,project_id,job_id,attempt_json,status_json,receipt_json,manifest_json,"
            "project_home,job_root,private_dir,worker_pid,worker_group_id,worker_birth_identity,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(attempt.attempt_id), str(attempt.project_id), attempt.job_id,
                attempt.model_dump_json(by_alias=True), status_attempt.model_dump_json(by_alias=True),
                None, None, "", "", str(supervisor.private_root / "attempts" / str(attempt.attempt_id)),
                None, None, None, time.time(),
            ),
        )


def _write_fake_cli(supervisor, body):
    executable = Path(supervisor.executable)
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if sys.argv[1:] == ['--version']:\n"
        f"    print({SUPPORTED_CLI_VERSION!r})\n"
        "    raise SystemExit(0)\n"
        "if sys.argv[-2:] == ['login', 'status']:\n"
        "    raise SystemExit(int(__import__('os').environ.get('PLOTLOOM_TEST_LOGIN_STATUS', '0')))\n"
        + body
    )
    executable.chmod(0o700)
    return build_codex_exec_profile(executable, source_root=supervisor.source_root)


def _prepared_text_job(supervisor, tmp_path, *, fake_cli_source=None):
    body = fake_cli_source or "import sys, time\nsys.stdin.read()\ntime.sleep(30)\n"
    profile = _write_fake_cli(supervisor, body)
    storage = ProjectFolderStorage(
        outputs_root=supervisor.outputs_root,
        application_data_root=tmp_path / "application",
    )
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
        request = CreativeHandoffRequest(
            jobId="ch_" + "a" * 20,
            projectId=str(project_id),
            sectionId="section-opening",
            stage="outline",
            expectedStageRevision=0,
            source={"kind": "synopsis", "title": "The Ferryman", "text": "A ferryman faces one irreversible choice."},
            inputArtifacts={},
            creativeBrief="Create a one-episode outline candidate without claiming approval.",
        )
        exchange = store.creative_handoff_exchange()
        execution_pin = exchange.current_execution_pin(request.stage)
        paths = exchange.write_package(request, execution_pin, executor_backend="codex_exec")
    package = Path(paths["packagePath"])
    job_root = package.parent
    package_hash = package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes)
    attempt = CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=project_id,
        jobId=request.job_id,
        operationKey=request.stage,
        domain="text",
        requestHash=request_hash(request),
        packageHash=package_hash,
        profileHash=profile.profile_hash,
        reservedImageOutputs=0,
        state="spawn_intent",
    )
    return exchange, request, execution_pin, job_root, attempt, profile
