"""Typed failures returned by the private Mac Codex Exec supervisor."""


class CodexExecSupervisorError(ValueError):
    """A typed host request cannot be admitted or safely reconciled."""
