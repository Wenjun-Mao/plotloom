"""Process execution and private evidence handling for the Mac supervisor."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from contextlib import ExitStack, closing
from pathlib import Path

from codex_exec_supervisor_environment import CodexExecSupervisorEnvironmentMixin
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_image import CodexExecSupervisorImageMixin
from codex_exec_supervisor_terminal import CodexExecSupervisorTerminalMixin
from codex_exec_supervisor_validation import CodexExecSupervisorValidationMixin

from plotloom.codex_exec_auth import (
    AUTHENTICATION_STORE,
)


class CodexExecSupervisorProcessMixin(
    CodexExecSupervisorEnvironmentMixin,
    CodexExecSupervisorValidationMixin,
    CodexExecSupervisorTerminalMixin,
    CodexExecSupervisorImageMixin,
):
    def _run(self, attempt, profile, package_request, job_root, private_dir, source_resources=None):
        from plotloom.codex_exec_contracts import transition_exec_attempt
        try:
            self._execute(attempt, profile, package_request, job_root, private_dir, source_resources)
        except BaseException:
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is not None and current.state not in {"completed", "failed", "settled", "outcome_unknown"}:
                try:
                    unknown = transition_exec_attempt(current, state="outcome_unknown")
                    self._store(unknown)
                except Exception:
                    pass
        finally:
            # The launching parent reaps this helper. This process owns only
            # its durable attempt finalization and one FIFO continuation.
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is not None and current.state in {"completed", "failed", "settled"}:
                self._drain_queue()

    def _execute(self, attempt, profile, package_request, job_root, private_dir, source_resources=None):
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            CodexExecOutputEvidence,
            CodexExecReceipt,
            output_manifest_hash,
            transition_exec_attempt,
        )
        from plotloom.codex_exec_files import scan_regular_tree
        from plotloom.codex_exec_prompts import assignment_prompt
        from plotloom.codex_exec_runtime import (
            CodexExecRuntimeError,
            assert_file_changes_confined,
            locate_exact_session,
            package_tree_hash,
            read_exec_events,
        )
        from plotloom.codex_exec_telemetry import read_cli_session

        if source_resources is None:
            if attempt.domain == "text":
                from plotloom.codex_exec_resources import codex_exec_source_resources
                source_resources = codex_exec_source_resources(self.source_root, package_request)

        try:
            exact_profile = self.profile()
        except Exception:
            exact_profile = None
        if exact_profile is None or exact_profile.profile_hash != profile.profile_hash:
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is not None and current.state in {"spawn_intent", "cancel_requested"}:
                self._finish_not_started(
                    current,
                    worker_identity=self._registered_worker_identity(attempt.attempt_id),
                )
            return

        if not self.codex_exec_readiness().ready:
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is not None and current.state in {"spawn_intent", "cancel_requested"}:
                self._finish_not_started(
                    current,
                    worker_identity=self._registered_worker_identity(attempt.attempt_id),
                )
            return

        stdout_path = private_dir / "stdout.jsonl"
        stderr_path = private_dir / "stderr.log"
        delivery = job_root / "delivery"
        prompt = assignment_prompt(
            job_id=attempt.job_id,
            package_path=job_root / "package",
            delivery_path=delivery,
            domain=attempt.domain,
        )
        command = [
            str(self.executable), "exec", "--json", "--cd", str(delivery),
            "--model", profile.model,
            "--config", f'model_reasoning_effort="{profile.reasoning_effort}"',
            "--config", f'cli_auth_credentials_store="{AUTHENTICATION_STORE}"',
            "--config", f'default_permissions="{profile.permission_profile}"',
            "--config", f'permissions.{profile.permission_profile}.extends=":workspace"',
            "--config", self._permission_filesystem_config(
                profile, job_root, delivery, private_dir, self.codex_home,
                source_resources.read_paths if source_resources is not None else (),
                domain=attempt.domain,
            ),
            "--config", f'permissions.{profile.permission_profile}.network.enabled=false',
        ]
        from plotloom.codex_exec_profile import DISABLED_CLI_FEATURES, cli_feature_flags
        command.extend(flag for feature in DISABLED_CLI_FEATURES for flag in ("--disable", feature))
        command.extend(cli_feature_flags(attempt.domain))
        command.extend(("--config", 'web_search="disabled"'))
        command.extend(("--ignore-user-config", "-"))
        environment = self._cli_environment(
            private_dir, source_root=self.source_root, domain=attempt.domain,
            source_resources=source_resources, profile=profile,
        )
        process = None
        try:
            with ExitStack() as streams:
                with self._guard:
                    with closing(self._connect()) as connection:
                        connection.execute("BEGIN IMMEDIATE")
                        self._namespace_assert_connection(connection)
                        row = connection.execute(
                            "SELECT * FROM exec_attempts WHERE attempt_id=?",
                            (str(attempt.attempt_id),),
                        ).fetchone()
                        if row is None:
                            connection.rollback()
                            raise CodexExecSupervisorError("Codex Exec reservation disappeared before spawn")
                        original = CodexExecAttempt.model_validate_json(row["attempt_json"])
                        if self._identity(original) != self._identity(attempt):
                            connection.rollback()
                            raise CodexExecSupervisorError("Codex Exec worker changed immutable attempt identity")
                        latest = CodexExecAttempt.model_validate_json(row["status_json"])
                        worker_identity = (
                            row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"]
                        )
                        actual_worker = (os.getpid(), *self._process_identity(os.getpid()))
                        if worker_identity != actual_worker:
                            connection.rollback()
                            raise CodexExecSupervisorError("Codex Exec spawn is outside its registered attempt worker")
                        if latest.state == "cancel_requested":
                            self._settle_not_started_in_transaction(
                                connection, row, latest, worker_identity=worker_identity
                            )
                            connection.commit()
                            return
                        if latest.state != "spawn_intent":
                            connection.rollback()
                            return
                        grant = connection.execute("SELECT domain FROM exec_slot WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
                        authorization = connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
                        if grant is None or grant["domain"] != latest.domain or authorization is None:
                            connection.rollback()
                            raise CodexExecSupervisorError("Codex Exec spawn has no exact capacity and queue authorization")
                        if self._park_before_spawn_in_transaction(
                            connection, row, latest, worker_identity=worker_identity,
                        ):
                            connection.commit()
                            return

                        # Create native evidence only after the worker's final
                        # authorization fence. A proven parked job can later
                        # resume without replacing earlier execution evidence.
                        for path in (stdout_path, stderr_path):
                            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
                            os.close(descriptor)
                        stdout = streams.enter_context(stdout_path.open("wb"))
                        stderr = streams.enter_context(stderr_path.open("wb"))

                        # The durable SQLite write lock spans the final cancel
                        # check, Popen and process-identity commit. A bridge in
                        # another process must observe either no child or its
                        # exact running identity; it cannot settle a child as
                        # not-started in this interval.
                        try:
                            self._namespace_assert_attempt(attempt, check_profile=True)
                            if not self._qualification_new_work(connection, attempt):
                                # This worker owns proof that native Popen has
                                # not occurred. Park only through the existing
                                # exact pre-spawn owner, never time-only release.
                                connection.execute("UPDATE exec_queue SET enabled=0 WHERE attempt_id=?",
                                    (str(attempt.attempt_id),))
                                self._park_before_spawn_in_transaction(connection, row, latest,
                                    worker_identity=worker_identity)
                                connection.commit()
                                return
                            process = subprocess.Popen(
                                command,
                                cwd=delivery,
                                env=environment,
                                stdin=subprocess.PIPE,
                                stdout=stdout,
                                stderr=stderr,
                                start_new_session=True,
                            )
                            group_id, birth_identity = self._process_identity(process.pid)
                            if group_id != process.pid:
                                raise CodexExecSupervisorError(
                                    "Codex Exec process group does not match its leader"
                                )
                            running = transition_exec_attempt(
                                latest,
                                state="running",
                                process_id=process.pid,
                                process_group_id=group_id,
                                process_birth_identity=birth_identity,
                            )
                            self._persist_status_in_transaction(connection, running)
                            connection.execute("DELETE FROM exec_queue WHERE attempt_id=?", (str(attempt.attempt_id),))
                            connection.commit()
                        except BaseException:
                            if process is None:
                                connection.rollback()
                                raise
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait(timeout=2)
                            except (OSError, subprocess.SubprocessError):
                                pass
                            changes = {"state": "outcome_unknown"}
                            if ("group_id" in locals() and group_id == process.pid
                                    and "birth_identity" in locals()):
                                changes.update(
                                    process_id=process.pid,
                                    process_group_id=group_id,
                                    process_birth_identity=birth_identity,
                                )
                            unknown = transition_exec_attempt(latest, **changes)
                            self._persist_status_in_transaction(connection, unknown)
                            connection.commit()
                            raise
                if process is None:
                    return
                prompt_write_failed = False
                try:
                    process.stdin.write(prompt.encode("utf-8"))
                    process.stdin.close()
                except BrokenPipeError:
                    prompt_write_failed = True
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                deadline = time.monotonic() + profile.max_runtime_seconds
                over_limit = False
                termination_started = None
                while process.poll() is None:
                    now = time.monotonic()
                    latest = self._load(self._row(attempt.attempt_id)).attempt
                    if latest is not None and latest.state == "cancel_requested" and termination_started is None:
                        termination_started = now
                        os.killpg(process.pid, signal.SIGTERM)
                    try:
                        if stdout_path.stat().st_size + stderr_path.stat().st_size > profile.max_output_bytes:
                            over_limit = True
                            if termination_started is None:
                                termination_started = now
                                os.killpg(process.pid, signal.SIGTERM)
                    except FileNotFoundError:
                        over_limit = True
                        if termination_started is None:
                            termination_started = now
                            os.killpg(process.pid, signal.SIGTERM)
                    if now > deadline and termination_started is None:
                        termination_started = now
                        os.killpg(process.pid, signal.SIGTERM)
                    elif termination_started is not None and now - termination_started > 3:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    if process.poll() is None:
                        time.sleep(0.2)
                exit_code = process.wait()
                if not self._wait_for_process_group_exit(group_id):
                    current = self._load(self._row(attempt.attempt_id)).attempt
                    if current is not None and current.state not in {"completed", "failed", "settled", "outcome_unknown"}:
                        self._mark_unknown(current)
                    return
                if prompt_write_failed:
                    # The CLI started but the frozen assignment was not fully
                    # delivered. Its remote side effects cannot be inferred.
                    current = self._load(self._row(attempt.attempt_id)).attempt
                    self._mark_unknown(current or attempt)
                    return
                if over_limit:
                    raise CodexExecRuntimeError("Codex Exec private output exceeded its qualified byte limit")
        except OSError as error:
            current = self._load(self._row(attempt.attempt_id)).attempt
            if process is None and current is not None and current.state in {"spawn_intent", "cancel_requested"}:
                self._finish_not_started(
                    current,
                    worker_identity=self._registered_worker_identity(attempt.attempt_id),
                )
                return
            if process is not None:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                self._mark_unknown(current or attempt)
                return
            raise error

        current = self._load(self._row(attempt.attempt_id)).attempt
        if (current is None or current.process_id != process.pid
                or current.process_group_id != group_id
                or current.process_birth_identity != birth_identity):
            self._mark_unknown(current or attempt)
            return
        try:
            if package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash:
                raise CodexExecRuntimeError("Codex Exec frozen package changed during the process")
            stream = read_exec_events(stdout_path, max_event_bytes=profile.max_event_bytes, max_total_bytes=profile.max_output_bytes)
            assert_file_changes_confined(stream, job_root / "delivery")
            session_path = locate_exact_session(self._codex_home(environment), stream.session_id)
            session = read_cli_session(
                session_path,
                stream.session_id,
                max_event_bytes=profile.max_event_bytes,
                max_total_bytes=profile.max_output_bytes,
            )
            if attempt.domain == "text" and (session.image_calls or session.image_events or session.reference_views):
                self._mark_unknown(current, session_id=stream.session_id)
                return
            if exit_code != 0 or stream.terminal_event != "turn.completed" or stream.diagnostics:
                self._finish_failure(
                    current, exit_code, stream.session_id, session, stdout_path, stderr_path,
                    max_output_bytes=profile.max_output_bytes,
                )
                return
            if attempt.domain == "text":
                from codex_exec_supervisor_errors import CodexExecValidationFailure
                if attempt.validation_plan_hash is not None:
                    current = self._store(transition_exec_attempt(
                        current, state="validating", session_id=stream.session_id,
                    ))
                try:
                    text_validation = self._validate_text_delivery(
                        attempt, profile, package_request, job_root, private_dir, source_resources,
                    )
                except CodexExecValidationFailure as error:
                    self._finish_failure(
                        current, exit_code, stream.session_id, session, stdout_path, stderr_path,
                        max_output_bytes=profile.max_output_bytes,
                        extra_evidence_hash=error.evidence_hash,
                    )
                    return
                outputs = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
                image_facts = ()
                remote_state = "not_applicable"
            else:
                text_validation = None
                completion = self._complete_image_attempt(
                    attempt, profile, package_request, job_root, environment, stream, session,
                    current, exit_code, stdout_path, stderr_path,
                )
                if completion is None:
                    return
                outputs = completion.outputs
                image_facts = completion.image_facts
                remote_state = completion.remote_state
                reference_views = completion.reference_views
                image_call = completion.image_call
                image_event = completion.image_event
                reference_hashes = completion.reference_hashes
            output_evidence = tuple(CodexExecOutputEvidence(
                outputHash=item.sha256,
                outputRelativePath=f"delivery/{item.relative_path}",
                sizeBytes=item.size_bytes,
            ) for item in outputs)
            if not output_evidence:
                raise CodexExecRuntimeError("Codex Exec produced no delivery files")
            output_hash = output_manifest_hash(output_evidence)
            evidence_hash = self._evidence_hash(stdout_path, stderr_path, session.transcript_sha256, exit_code)
            if text_validation is not None:
                from hashlib import sha256
                evidence_hash = sha256(
                    f"{evidence_hash}:{text_validation.evidence_hash}".encode("ascii")
                ).hexdigest()
            completed = transition_exec_attempt(
                current,
                state="completed",
                session_id=stream.session_id,
                process_exit_code=exit_code,
                terminal_result="success",
                remote_tool_state=remote_state,
                evidence_hash=evidence_hash,
                output_hash=output_hash,
                remote_output_hash=image_facts[0].output_hash if image_facts else None,
                image_budget_state="consumed" if attempt.domain == "image" else "none",
            )
            receipt = CodexExecReceipt(
                attemptId=attempt.attempt_id,
                sessionId=stream.session_id,
                profileHash=profile.profile_hash,
                requestHash=attempt.request_hash,
                packageHash=attempt.package_hash,
                plotloomCodeRevision=attempt.plotloom_code_revision,
                processId=current.process_id,
                processGroupId=current.process_group_id,
                processBirthIdentity=current.process_birth_identity,
                processExitCode=exit_code,
                expectedImageOutputs=attempt.reserved_image_outputs,
                evidenceHash=evidence_hash,
                outputHash=output_hash,
                outputs=output_evidence,
                imageEvidence=image_facts,
                referenceViews=reference_views if attempt.domain == "image" else (),
                validationPlanHash=attempt.validation_plan_hash,
                textValidation=text_validation,
                remoteOutputHash=completed.remote_output_hash,
                remoteToolState=remote_state,
            )
            from plotloom.codex_exec_contracts import assert_receipt_matches_attempt
            assert_receipt_matches_attempt(completed, receipt)
            manifest_json = self._build_manifest_json(
                attempt, profile, package_request, job_root, completed, receipt,
                session, image_facts, image_call if attempt.domain == "image" else None,
                image_event if attempt.domain == "image" else None,
                reference_hashes if attempt.domain == "image" else (),
            )
            self._store(completed, receipt=receipt, manifest_json=manifest_json)
            self._ensure_manifest(self._row(attempt.attempt_id), completed)
        except BaseException:
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is not None and current.state not in {"completed", "failed", "settled", "outcome_unknown"}:
                self._mark_unknown(current)
            raise

    def _codex_home(self, environment):
        root = Path(environment.get("CODEX_HOME", "")).expanduser().resolve(strict=True)
        if root != self.codex_home:
            raise CodexExecSupervisorError("Codex session evidence escaped its authenticated host home")
        return root

    @staticmethod
    def _evidence_hash(stdout_path, stderr_path, transcript_hash, exit_code):
        from hashlib import sha256
        digest = sha256()
        for path in (stdout_path, stderr_path):
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        digest.update(transcript_hash.encode("ascii"))
        digest.update(str(exit_code).encode("ascii"))
        return digest.hexdigest()

    @classmethod
    def _wait_for_process_group_exit(cls, process_group_id, *, grace_seconds=3.0):
        """Require every process in the owned group to exit before trusting bytes."""
        deadline = time.monotonic() + grace_seconds
        while cls._process_group_exists(process_group_id):
            if time.monotonic() >= deadline:
                # The leader is gone, so the group number can no longer be
                # tied safely to its original birth identity. Do not signal a
                # possibly reused group ID; retain the attempt as unknown.
                return False
            time.sleep(0.1)
        return True

    @staticmethod
    def _process_group_exists(process_group_id):
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return False
        except OSError:
            # Permission errors do not prove that the process group is gone.
            return True
        return True
