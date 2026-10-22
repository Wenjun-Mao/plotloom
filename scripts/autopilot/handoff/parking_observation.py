"""Passive cleanup facts: safe parked jobs never imply successful completion."""
from dataclasses import dataclass

from admission_observation import identity
from plotloom.codex_exec_contracts import CodexExecHostStatus


@dataclass(frozen=True)
class CleanupFacts:
    rows: tuple
    project_attempts: tuple
    project_states: dict
    queue: dict
    held: int
    validators: int
    group_observations: dict
    material_qualified: bool
    human_handoff: bool = False


@dataclass(frozen=True)
class CleanupResult:
    outcome: str
    zero_live_work: bool
    all_work_quiescent: bool
    complete_success: bool
    parked_attempts: tuple = ()


def classify_cleanup(facts):
    """Use only supplied observations; never suspend, retire, resume or poll work.

    material_qualified is the EXISTING full-arm verification result, including
    inventory/bundle/receipt/early-reuse guards. This function cannot replace it.
    Group values are explicit absent/present/unproved observations, not guesses.
    """
    unresolved = CleanupResult("unresolved", False, False, False)
    if any(type(value) is not int or value < 0 for value in (facts.held, facts.validators)):
        return unresolved
    if facts.held or facts.validators or facts.human_handoff:
        return unresolved
    rows = {str(row.current.attempt_id): row for row in facts.rows}
    projects = {str(attempt.attempt_id): attempt for attempt in facts.project_attempts}
    if len(rows) != len(facts.rows) or len(projects) != len(facts.project_attempts) or set(rows) != set(projects):
        return unresolved
    if any(state not in {"paused", "awaiting_review"} for state in facts.project_states.values()):
        return unresolved
    parked, groups = [], set()
    for key, row in rows.items():
        attempt = row.current
        project = projects[key]
        if (identity(row.original) != identity(attempt) or identity(projects[key]) != identity(attempt)
                or str(attempt.project_id) not in facts.project_states):
            return unresolved
        if project.state in {"outcome_unknown", "cancel_requested", "failed"}:
            return unresolved
        worker = (row.worker_pid, row.worker_group_id, row.worker_birth_identity)
        if any(item is not None for item in worker) and any(item is None for item in worker):
            return unresolved
        if row.worker_pid is not None and row.worker_pid != row.worker_group_id:
            return unresolved
        groups.update(group for group in (row.worker_group_id, attempt.process_group_id) if group is not None)
        if attempt.state == "queued":
            if (row.dispatch_enabled is not False or facts.queue.get(key) is not False
                    or any(item is not None for item in (*worker, attempt.process_id,
                        attempt.process_group_id, attempt.process_birth_identity, attempt.session_id,
                        attempt.process_exit_code, attempt.terminal_result, attempt.remote_tool_state,
                        attempt.evidence_hash, attempt.output_hash, attempt.remote_output_hash, row.receipt))):
                return unresolved
            if (project.state not in {"spawn_intent", "queued"}
                    or project.image_budget_state != attempt.image_budget_state
                    or any(item is not None for item in (project.evidence_hash, project.output_hash,
                        project.remote_output_hash, project.terminal_result, project.remote_tool_state))):
                return unresolved
            parked.append(key)
        elif attempt.state == "completed" and attempt.terminal_result == "success":
            # Resource absence cannot erase an unresolved/stale project outcome
            # or pretend the project's reserved budget was already settled.
            if project.model_dump(mode="python") != attempt.model_dump(mode="python"):
                return unresolved
            try:
                CodexExecHostStatus(state="completed", attempt=attempt, receipt=row.receipt)
            except (TypeError, ValueError):
                return unresolved
        else:
            return unresolved
    if set(facts.queue) != set(parked):
        return unresolved
    if any(facts.group_observations.get(group) != "absent" for group in groups):
        return unresolved
    # Any additional supplied present/unproved group also forbids absence claims.
    if any(value != "absent" for value in facts.group_observations.values()):
        return unresolved
    if parked:
        if any(state != "paused" for state in facts.project_states.values()):
            return unresolved
        return CleanupResult("safe_parked", True, False, False, tuple(sorted(parked)))
    if not rows:
        return CleanupResult("empty_unqualified", True, True, False)
    if facts.material_qualified:
        return CleanupResult("complete_success", True, True, True)
    return CleanupResult("material_incomplete", True, True, False)
