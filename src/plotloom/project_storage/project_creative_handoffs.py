"""Confined creative package and stored request/pin adapters for a project handle."""

from ..creative_handoff_contracts import (
    CreativeHandoffError,
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

    def recover_creative_handoff_execution_pin(
        self, request: CreativeHandoffRequest, *, trusted_revision: str
    ) -> dict[str, str]:
        """Explicitly recover a pre-pin handoff from an operator-selected commit.

        This leaves package and delivery files untouched.  It first proves the
        project still owns this request and that the existing package/delivery
        match the selected historic pin, then records that pin in SQLite.
        """

        current = {
            "outline": self.outline_candidate_request,
            "characters": self.cast_candidate_request,
            "art": self.art_candidate_request,
            "script": self.script_candidate_request,
            "storyboard": self.storyboard_review_candidate_request,
        }[request.stage](request.job_id)
        if current != request:
            raise CreativeHandoffError(
                "request_identity_mismatch",
                "creative handoff request is no longer project-owned",
            )
        exchange = self.creative_handoff_exchange()
        revision, pin = exchange.execution_pin_at_revision(request, trusted_revision)
        exchange.verified_package_paths(request, pin)
        delivery = exchange.read_delivery(request, pin)
        if delivery is not None:
            claimed_revision = delivery.manifest.executor_provenance.code_revision
            if not revision.startswith(claimed_revision):
                raise CreativeHandoffError(
                    "delivery_execution_mismatch",
                    "delivery claims a different code revision than the operator-selected recovery revision",
                )
        self.repository.recover_creative_handoff_execution_pin(
            request, pin, trusted_revision=revision
        )
        return pin

    def terminal_creative_request(self, stage: CreativeStage, job_id: str) -> CreativeHandoffRequest:
        """Terminal reconciliation only; ordinary handoff guards remain unchanged."""
        return self.repository.creative_terminal.retained_request(self.manifest.project_id, stage, job_id)
