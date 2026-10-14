"""Typed failures returned by the private Mac Codex Exec supervisor."""


class CodexExecSupervisorError(ValueError):
    """A typed host request cannot be admitted or safely reconciled."""


class CodexExecValidationFailure(CodexExecSupervisorError):
    """Known failed trusted validation with a private hash for its captured evidence."""

    def __init__(self, message: str, evidence_hash: str):
        super().__init__(message)
        self.evidence_hash = evidence_hash


class CodexExecValidationOwnershipUnknown(CodexExecSupervisorError):
    """A validator process group outlived its exact leader and cannot be cleaned safely."""
