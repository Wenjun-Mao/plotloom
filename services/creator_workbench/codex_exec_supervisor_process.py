"""Process execution and private evidence handling for the Mac supervisor."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_terminal import CodexExecSupervisorTerminalMixin

from plotloom.codex_exec_auth import (
    AUTHENTICATION_STORE,
)
from plotloom.codex_exec_auth import (
    credential_free_environment as _credential_free_environment,
)


class CodexExecSupervisorProcessMixin(CodexExecSupervisorTerminalMixin):
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
            self._workers.pop(str(attempt.attempt_id), None)

    def _execute(self, attempt, profile, package_request, job_root, private_dir, source_resources=None):
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            CodexExecImageEvidence,
            CodexExecOutputEvidence,
            CodexExecReceipt,
            image_arguments_hash,
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
        for path in (stdout_path, stderr_path):
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.close(descriptor)
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
            ),
            "--config", f'permissions.{profile.permission_profile}.network.enabled=false',
        ]
        from plotloom.codex_exec_profile import DISABLED_CLI_FEATURES
        command.extend(flag for feature in DISABLED_CLI_FEATURES for flag in ("--disable", feature))
        # The pinned CLI ignores tools.view_image; its stable `view_image`
        # feature flag is the supported exact-version disable path.
        command.extend(("--config", 'web_search="disabled"'))
        if attempt.domain == "text":
            command.extend(("--disable", "image_generation"))
        else:
            command.extend(("--enable", "image_generation"))
        command.extend(("--ignore-user-config", "-"))
        environment = self._cli_environment(
            private_dir, source_root=self.source_root, domain=attempt.domain, source_resources=source_resources
        )
        process = None
        try:
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                with self._guard:
                    with closing(self._connect()) as connection:
                        connection.execute("BEGIN IMMEDIATE")
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

                        # The durable SQLite write lock spans the final cancel
                        # check, Popen and process-identity commit. A bridge in
                        # another process must observe either no child or its
                        # exact running identity; it cannot settle a child as
                        # not-started in this interval.
                        try:
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
            if attempt.domain == "text" and (session.image_calls or session.image_events):
                self._mark_unknown(current, session_id=stream.session_id)
                return
            if exit_code != 0 or stream.terminal_event != "turn.completed" or stream.diagnostics:
                self._finish_failure(
                    current, exit_code, stream.session_id, session, stdout_path, stderr_path,
                    max_output_bytes=profile.max_output_bytes,
                )
                return
            if attempt.domain == "text":
                outputs = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
                image_facts = ()
                remote_state = "not_applicable"
            else:
                if attempt.reserved_image_outputs != 1 or len(session.image_calls) != 1 or len(session.image_events) != 1:
                    raise CodexExecRuntimeError("serial image attempt did not produce exactly one ImageGen event")
                image_call, image_event = session.image_calls[0], session.image_events[0]
                if image_event.status != "completed" or image_event.saved_path is None:
                    self._finish_failure(
                        current, exit_code, stream.session_id, session, stdout_path, stderr_path,
                        remote_state="failed", max_output_bytes=profile.max_output_bytes,
                    )
                    return
                reference_hashes = self._match_image_references(job_root, package_request, image_call.reference_paths)
                from plotloom.codex_exec_runtime import read_generated_image
                content, image_hash = read_generated_image(
                    Path(image_event.saved_path),
                    codex_home=self._codex_home(environment),
                    session_id=stream.session_id,
                    max_bytes=profile.max_output_bytes,
                )
                self._copy_image_to_delivery(job_root, Path(image_event.saved_path).name, content)
                image_path = f"delivery/outputs/{Path(image_event.saved_path).name}"
                arguments_hash = image_arguments_hash(
                    prompt_hash=sha256(image_call.prompt.encode("utf-8")).hexdigest(),
                    reference_hashes=reference_hashes,
                    transparent_background=image_call.transparent_background,
                    num_last_images_to_include=image_call.num_last_images_to_include,
                )
                image_facts = (CodexExecImageEvidence(
                    attemptId=attempt.attempt_id,
                    sessionId=stream.session_id,
                    callId=image_call.call_id,
                    eventId=image_event.event_id,
                    eventType="image_gen.generation",
                    eventStatus="completed",
                    argumentsHash=arguments_hash,
                    promptHash=sha256(image_call.prompt.encode("utf-8")).hexdigest(),
                    referenceHashes=reference_hashes,
                    transparentBackground=image_call.transparent_background,
                    numLastImagesToInclude=image_call.num_last_images_to_include,
                    outputHash=image_hash,
                    outputRelativePath=image_path,
                ),)
                outputs = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
                remote_state = "completed"
            output_evidence = tuple(CodexExecOutputEvidence(
                outputHash=item.sha256,
                outputRelativePath=f"delivery/{item.relative_path}",
                sizeBytes=item.size_bytes,
            ) for item in outputs)
            if not output_evidence:
                raise CodexExecRuntimeError("Codex Exec produced no delivery files")
            output_hash = output_manifest_hash(output_evidence)
            evidence_hash = self._evidence_hash(stdout_path, stderr_path, session.transcript_sha256, exit_code)
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
                processId=current.process_id,
                processGroupId=current.process_group_id,
                processBirthIdentity=current.process_birth_identity,
                processExitCode=exit_code,
                expectedImageOutputs=attempt.reserved_image_outputs,
                evidenceHash=evidence_hash,
                outputHash=output_hash,
                outputs=output_evidence,
                imageEvidence=image_facts,
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

    def _cli_environment(self, private_dir, *, source_root, domain, source_resources=None):
        """Keep inherited API tokens and bridge credentials out of the worker process."""
        environment = _credential_free_environment()
        (private_dir / "tmp").mkdir(mode=0o700, exist_ok=True)
        (private_dir / "uv-cache").mkdir(mode=0o700, exist_ok=True)
        environment["TMPDIR"] = str(private_dir / "tmp")
        environment["CODEX_HOME"] = str(self.codex_home)
        environment["UV_CACHE_DIR"] = str(private_dir / "uv-cache")
        for name in (
            "PLOTLOOM_SOURCE_ROOT", "PLOTLOOM_UV", "PLOTLOOM_NODE", "PLOTLOOM_PYTHON",
            "PYTHONPATH", "NODE_PATH", "NODE_OPTIONS", "PYTHONHOME",
            "PYTHONUSERBASE", "PYTHONSTARTUP", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE",
            "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT",
        ):
            environment.pop(name, None)
        if domain == "text":
            environment["PLOTLOOM_SOURCE_ROOT"] = str(source_root)
            environment["PYTHONPATH"] = str(source_root / "src")
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONNOUSERSITE"] = "1"
            environment["UV_PROJECT_ENVIRONMENT"] = str(source_root / ".venv")
            tool_paths = dict(source_resources.tools) if source_resources is not None else {}
            if "uv" in tool_paths:
                environment["PLOTLOOM_UV"] = str(tool_paths["uv"])
            if "node" in tool_paths:
                environment["PLOTLOOM_NODE"] = str(tool_paths["node"])
            if "python" in tool_paths:
                environment["PLOTLOOM_PYTHON"] = str(tool_paths["python"])
        return environment

    @staticmethod
    def _permission_filesystem_config(
        profile, job_root, delivery, private_dir, codex_home, source_read_paths=()
    ):
        values = {
            ":root": "deny",
            ":minimal": "read",
            ":tmpdir": "write",
            ":slash_tmp": "deny",
            str(codex_home): "deny",
            str(job_root / "package"): "read",
            str(delivery): "write",
            str(private_dir / "tmp"): "write",
            str(private_dir / "uv-cache"): "write",
        }
        values.update({str(path): "read" for path in source_read_paths})
        encoded = ",".join(f'{json.dumps(key)}={json.dumps(value)}' for key, value in values.items())
        return f"permissions.{profile.permission_profile}.filesystem={{{encoded}}}"

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

    @staticmethod
    def _match_image_references(job_root, package_request, reference_paths):
        references = package_request.get("references")
        if not isinstance(references, list):
            raise CodexExecSupervisorError("Codex Exec image request has no typed frozen reference inventory")
        by_path = {}
        package = job_root / "package"
        for item in references:
            if not isinstance(item, dict) or set(item) != {"role", "filename", "sha256"}:
                raise CodexExecSupervisorError("Codex Exec image reference has an unsupported package shape")
            relative = Path(item["filename"])
            if relative.is_absolute() or ".." in relative.parts or not item["filename"].startswith("references/"):
                raise CodexExecSupervisorError("Codex Exec image reference is outside its frozen package")
            by_path[str((package / relative).resolve(strict=True))] = item["sha256"]
        hashes = []
        for value in reference_paths:
            path = Path(value)
            if not path.is_absolute():
                raise CodexExecSupervisorError("ImageGen reference arguments must be exact absolute package paths")
            resolved = str(path.resolve(strict=True))
            if resolved not in by_path:
                raise CodexExecSupervisorError("ImageGen reference argument is not a frozen package attachment")
            hashes.append(by_path[resolved])
        if len(hashes) != len(set(hashes)) or set(hashes) != {item["sha256"] for item in references}:
            raise CodexExecSupervisorError("ImageGen references differ from the exact frozen package bytes")
        return tuple(hashes)

    @staticmethod
    def _copy_image_to_delivery(job_root, filename, content):
        from pathlib import PurePosixPath
        if PurePosixPath(filename).name != filename or not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raise CodexExecSupervisorError("ImageGen returned an unsupported output basename")
        delivery = job_root / "delivery"
        if delivery.is_symlink() or not delivery.is_dir():
            raise CodexExecSupervisorError("Codex Exec delivery directory is unsafe")
        if any(delivery.iterdir()):
            raise CodexExecSupervisorError("image delivery was modified before its trusted host copy")
        outputs = delivery / "outputs"
        outputs.mkdir(mode=0o700)
        output_fd = os.open(outputs, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=output_fd)
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            os.fsync(output_fd)
        finally:
            os.close(output_fd)
