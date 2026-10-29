"""Standalone check advancement by the existing project controller process lease."""
import logging

from sqlalchemy import select

from .content_language_persistence import check_rows, verified_check
from .content_language_service import ContentLanguageService
from .exceptions import InvalidTransitionError
from .generation_retry_policy import repeatable_failure
from .persistence.schema import AutopilotRunRow

logger = logging.getLogger(__name__)


def standalone_check_jobs(store):
    """Read current already-authorized checks; run-bound jobs keep their owner."""
    with store.repository._read() as session:
        run_ids = set(session.scalars(select(AutopilotRunRow.id).where(
            AutopilotRunRow.project_id == store.manifest.project_id)))
        jobs, seen = [], set()
        for row in check_rows(session, store.manifest.project_id):
            request, data, attempt, _profile, _receipt, result = verified_check(row)
            binding = (request.source["candidateJobId"], request.source["bindingHash"])
            if binding in seen:
                continue
            seen.add(binding)
            # Only the prospective frozen retry grant delegates continuation.
            # Retained requests without it never acquire new runtime authority.
            if ("retryPolicy" not in data or str(attempt.run_id) in run_ids
                    or result is not None or data.get("executionCancelled")):
                continue
            if attempt.state in {"completed", "settled", "cancel_requested"}:
                continue
            if attempt.state in {"failed", "outcome_unknown"}:
                policy = data["retryPolicy"]
                if not repeatable_failure(attempt) or (data.get("localExecutionStopped")
                        and policy["automaticRetriesUsed"] >= policy["automaticRetryLimit"]):
                    continue
            jobs.append(row.job_id)
        return jobs


def advance_standalone_checks(store, registry):
    """Use native rows and admission CAS; no queue, thread or observation dispatch."""
    service = ContentLanguageService(registry)
    for job_id in standalone_check_jobs(store):
        try:
            service.advance(store, job_id)
        except (InvalidTransitionError, ValueError) as error:
            # Source, permissions and configuration gates remain authoritative.
            # Never persist arbitrary exception text or manufacture a new grant.
            logger.warning("Standalone language check held: %s", type(error).__name__)
