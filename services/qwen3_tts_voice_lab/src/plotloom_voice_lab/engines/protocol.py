"""Bounded private child-process messages; never exposed as shell arguments."""

from __future__ import annotations

from typing import Literal
from pydantic import Field, model_validator
from ..contracts import StrictModel, DeliveryControl


Phase = Literal["loading_model", "interpreting", "synthesizing"]


class ExecutionEvidence(StrictModel):
    mode: Literal["none", "text", "manual"]
    rawVector: list[float] | None = None
    effectiveVector: list[float] | None = None
    classifierSeconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def valid_vectors(self):
        for vector in (self.rawVector, self.effectiveVector):
            if vector is not None:
                DeliveryControl(mode="manual", vector=vector)
        if (self.mode == "text" and (self.rawVector is None or self.effectiveVector != self.rawVector)) or (self.mode == "manual" and self.effectiveVector is None):
            raise ValueError("execution.invalid_vector")
        if self.mode == "none" and (self.rawVector is not None or self.effectiveVector is not None):
            raise ValueError("execution.unexpected_vector")
        return self


class RunnerRequest(StrictModel):
    schemaVersion: Literal[1] = 1
    snapshot: dict
    runtime: dict
    text: str = Field(min_length=1, max_length=200)
    direction: str = Field(default="", max_length=2301)
    seed: int = Field(ge=0, le=2**32 - 1)
    reference: str | None = None
    referenceText: str = Field(default="", max_length=160)
    delivery: DeliveryControl = Field(default_factory=DeliveryControl)
    output: str
    events: str


class RunnerEvent(StrictModel):
    kind: Literal["phase", "delivery", "complete", "failure"]
    phase: Phase | None = None
    evidence: ExecutionEvidence | None = None
    errorCode: Literal["model.unavailable", "model.integrity_failed", "audio.invalid", "generation.failed", "generation.oom"] | None = None
    peakTorchGiB: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def required_fields(self):
        if (self.kind == "phase" and self.phase is None) or (self.kind == "delivery" and self.evidence is None) or (self.kind == "failure" and self.errorCode is None):
            raise ValueError("runner.invalid_event")
        return self
