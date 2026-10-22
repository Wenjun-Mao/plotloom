"""Confined creative package and stored request/pin adapters for a project handle."""

from ..creative_handoff_contracts import (
    CreativeHandoffRequest,
    CreativeStage,
)
from datetime import datetime
from typing import Any
from .format import _require_real_directory, _utc_folder_timestamp, ProjectStorageConfinementError, ProjectStorageCorruptionError


class ProjectCreativeHandoffs:
    def creative_handoff_exchange(self):
        """Return the confined project-owned manual creative exchange root."""

        from ..creative_handoff_exchange import CreativeHandoffExchange

        outputs = _require_real_directory(self.home / "outputs", label="project outputs root")
        return CreativeHandoffExchange(outputs / "creative-handoff")

    def creative_handoff_execution_pin(self, request: CreativeHandoffRequest) -> dict[str, str]:
        """Read the pin bound to this candidate's request in project storage."""

        return self.repository.creative_handoff_execution_pin(request)

    def terminal_creative_request(self, stage: CreativeStage, job_id: str) -> CreativeHandoffRequest:
        """Terminal reconciliation only; ordinary handoff guards remain unchanged."""
        return self.repository.creative_terminal.retained_request(self.manifest.project_id, stage, job_id)


    def branch_state(self):
        return self.repository.branches.state(self.manifest.project_id)

    def branch_candidate_request(self, job_id):
        return self.repository.branches.request(self.manifest.project_id, job_id)

    def branch_candidate_report(self, job_id):
        return self.repository.branches.candidate_report(self.manifest.project_id, job_id)

    def admit_branch_delivery(self, delivery):
        return self.repository.branches.admit(self.manifest.project_id, delivery)

    def prepare_branch_candidate(self):
        exchange = self.creative_handoff_exchange()
        request = self.repository.branches.prepare(self.manifest.project_id, exchange)
        return exchange.write_package(request, self.creative_handoff_execution_pin(request))

    def branch_draft(self, job_id):
        return self.repository.branches.draft(self.manifest.project_id, job_id)

    def cancel_branch_candidate(self, job_id):
        self.repository.branches.cancel(self.manifest.project_id, job_id)
        return self.branch_state()


    def return_to_accepted_outline(self, request):
        return self.repository.source_outline._mutations.return_to_accepted(self.manifest.project_id, request)

    def image_exchange_for(self, job: dict[str, Any]):
        """Return the one project-run-local handoff exchange for an image unit."""
        from ..image_job_exchange import ImageJobExchange
        from ..managed_media import DEFAULT_MANAGED_MEDIA_LIMITS

        job_id = str(job.get("id", ""))
        created_at = job.get("createdAt")
        if not job_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_-"
            for character in job_id
        ):
            raise ProjectStorageConfinementError(
                "image handoff identity is not path-safe"
            )
        try:
            timestamp = _utc_folder_timestamp(datetime.fromisoformat(str(created_at)))
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "image handoff has no valid creation timestamp"
            ) from error
        runs = _require_real_directory(self.home / "runs", label="project runs root")
        run_home = runs / f"{timestamp}__{job_id}"
        # Manual image/reference proposals are durable database records before
        # their external package exists.  The package owner, not a caller or
        # specialist, creates this one confined run home on first Copy.
        # Without it, normal API handoffs depended on a test-only directory
        # setup and could never reach the exchange's no-follow writer.
        run_home.mkdir(mode=0o700, exist_ok=True)
        _require_real_directory(run_home, label="project image handoff run")
        return ImageJobExchange(run_home, limits=DEFAULT_MANAGED_MEDIA_LIMITS)
