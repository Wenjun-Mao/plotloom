"""Terminal settlement and private receipt publication for Codex attempts."""
from __future__ import annotations

from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorTerminalMixin:
    def _build_manifest_json(self, attempt, profile, package_request, job_root, terminal, receipt,
                             session, image_facts, image_call, image_event, reference_hashes):
        if attempt.domain == "text":
            from plotloom.codex_exec_delivery import publish_creative_completion
            from plotloom.creative_handoff_contracts import (
                creative_handoff_request_from_package,
            )
            from plotloom.creative_handoff_exchange import canonical_json
            request = creative_handoff_request_from_package(package_request)
            manifest = publish_creative_completion(
                request=request,
                execution_pin=package_request["executionPin"],
                code_revision=attempt.plotloom_code_revision,
                job_root=job_root,
                attempt=terminal,
                profile=profile,
                receipt=receipt,
                publish_marker=False,
            )
            return canonical_json(manifest.model_dump(mode="json", by_alias=True)).decode("utf-8")
        from plotloom.codex_exec_delivery import publish_image_completion
        manifest = publish_image_completion(
            request=package_request,
            execution_pin=package_request["specialistPreflight"],
            job_root=job_root,
            attempt=terminal,
            profile=profile,
            receipt=receipt,
            session=session,
            call=image_call,
            event=image_event,
            reference_hashes=reference_hashes,
            publish_marker=False,
        )
        from plotloom.image_job_package import canonical_json
        return canonical_json(manifest.model_dump(mode="json", by_alias=True, exclude_none=True)).decode("utf-8")

    def _finish_failure(
        self, attempt, exit_code, session_id, session, stdout_path, stderr_path,
        *, remote_state=None, max_output_bytes=500_000_000, extra_evidence_hash=None, content_rejection=None,
    ):
        from plotloom.codex_exec_contracts import transition_exec_attempt
        current = self._load(self._row(attempt.attempt_id)).attempt
        remote = remote_state or (
            "completed" if session and any(event.status == "completed" for event in session.image_events)
            else "failed" if session and any(event.status == "failed" for event in session.image_events)
            else "not_applicable"
        )
        if attempt.domain == "text" and session and (
            session.image_calls or session.image_events or session.reference_views
        ):
            # A text job cannot settle native ImageGen proof. Preserve its exact
            # session identity and keep host capacity fenced for reconciliation.
            self._mark_unknown(current or attempt, session_id=session_id)
            return
        if current is None or current.process_id is None:
            self._mark_unknown(current or attempt)
            return
        remote_output_hash = None
        if attempt.domain == "image" and remote == "completed":
            try:
                if (session is None or session_id != session.session_id
                        or len(session.image_calls) != 1 or len(session.image_events) != 1):
                    raise CodexExecSupervisorError("completed ImageGen output lacks one exact session event")
                event = session.image_events[0]
                if event.status != "completed" or event.saved_path is None:
                    raise CodexExecSupervisorError("completed ImageGen event has no exact output path")
                from plotloom.codex_exec_runtime import read_generated_image
                _content, remote_output_hash = read_generated_image(
                    Path(event.saved_path),
                    codex_home=self.codex_home,
                    session_id=session.session_id,
                    max_bytes=max_output_bytes,
                )
            except (OSError, ValueError, CodexExecSupervisorError):
                # The remote service reported success, but the host cannot
                # verify the exact bytes. Keep the budget and slot unresolved.
                self._mark_unknown(current)
                return
        evidence = self._evidence_hash(stdout_path, stderr_path,
            session.transcript_sha256 if session else "unavailable", exit_code)
        if extra_evidence_hash is not None:
            from hashlib import sha256
            evidence = sha256(f"{evidence}:{extra_evidence_hash}".encode("ascii")).hexdigest()
        changes = {
            "state": "failed",
            "session_id": session_id,
            "process_exit_code": exit_code,
            "terminal_result": "failure",
            "remote_tool_state": remote if attempt.domain == "image" else "not_applicable",
            "evidence_hash": evidence,
            "output_hash": None,
            "remote_output_hash": remote_output_hash,
            "content_rejection": content_rejection,
            "image_budget_state": (
                "consumed" if attempt.domain == "image" and remote == "completed"
                else "released" if attempt.domain == "image" else "none"
            ),
        }
        self._store(transition_exec_attempt(current, **changes))

    def _finish_not_started(self, attempt, *, worker_identity=None):
        from plotloom.codex_exec_contracts import CodexExecAttempt

        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        return self._finish_not_started_if_unspawned(
            attempt, worker_identity=worker_identity
        )
