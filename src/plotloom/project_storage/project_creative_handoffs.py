"""Confined creative package and stored request/pin adapters for a project handle."""

from ..creative_handoff_contracts import (
    CreativeHandoffRequest,
    CreativeStage,
)
from .format import _require_real_directory


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
