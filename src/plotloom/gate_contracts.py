from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import Field

from plotloom.domain_base import CamelModel


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


class GateSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class GateEvidence(CamelModel):
    """One immutable, JSON-safe observation supporting a gate decision."""

    model_config = CamelModel.model_config | {"frozen": True}

    key: Annotated[str, Field(min_length=1)]
    value: str


class GateResult(CamelModel):
    """Versioned deterministic quality-gate result.

    Results deliberately record an entity path rather than a provider prompt or
    transient runner detail.  Tuples and frozen nested evidence prevent callers
    from mutating the recorded decision after evaluation.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    # ``gate_id`` names one concrete check target (for example
    # ``audio.timing.shot-7``); ``id`` is the stable persisted result identity.
    id: Annotated[str, Field(min_length=1)]
    gate_set_version: Annotated[str, Field(min_length=1)]
    gate_id: Annotated[str, Field(min_length=1)]
    evaluated_input_hash: Annotated[str, Field(min_length=1)]
    required: bool
    status: GateStatus
    severity: GateSeverity
    entity_path: tuple[str | int, ...] = ()
    evidence: tuple[GateEvidence, ...] = ()
    reason: str = ""

    @property
    def passed(self) -> bool:
        """Whether this individual result can count toward acceptance."""

        if self.status == GateStatus.PASS:
            return True
        if self.required:
            # Required gates must run and pass.  In particular SKIPPED is not
            # a success-shaped outcome, even if an evaluator lacks context.
            return False
        return self.status in {GateStatus.SKIPPED, GateStatus.NOT_APPLICABLE}


class GateEvaluation(CamelModel):
    """Immutable, ordered output of one versioned deterministic evaluator."""

    model_config = CamelModel.model_config | {"frozen": True}

    gate_set_version: Annotated[str, Field(min_length=1)]
    evaluated_input_hash: Annotated[str, Field(min_length=1)]
    results: tuple[GateResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)
