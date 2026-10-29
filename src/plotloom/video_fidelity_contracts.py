"""Typed assistant fidelity evidence, separate from generation authorization."""
from typing import Literal

from pydantic import Field, model_validator

from .delegated_qa_contracts import AgentQaAttribution
from .domain_base import CamelModel

HASH = r"^[a-f0-9]{64}$"
CHECK_DIMENSIONS = ("actions", "identities", "positions", "sound_roles", "negation",
    "completeness", "exact_text", "creative_discretion")


class FidelityFinding(CamelModel):
    path: str = Field(min_length=1, max_length=200)
    code: Literal["omission", "changed_meaning", "negation", "identity", "position", "sound_role",
        "extra_speech", "visible_text", "invented_decision", "unsupported", "other"]
    message: str = Field(min_length=1, max_length=2000)


class FidelityTarget(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    source_hash: str = Field(pattern=HASH)
    candidate_hash: str = Field(pattern=HASH)
    compiled_prompt_sha256: str = Field(pattern=HASH)
    verdict: Literal["pass", "reject"]
    checked_paths: list[str] = Field(max_length=100)
    checked_dimensions: list[str] = Field(min_length=8, max_length=8)
    findings: list[FidelityFinding] = Field(max_length=100)

    @model_validator(mode="after")
    def consistent_verdict(self):
        if len(set(self.checked_dimensions)) != 8 or set(self.checked_dimensions) != set(CHECK_DIMENSIONS):
            raise ValueError("fidelity check must explicitly cover every semantic dimension")
        if (self.verdict == "pass") != (not self.findings):
            raise ValueError("fidelity rejection needs findings; a pass cannot retain findings")
        return self


class FidelityResult(CamelModel):
    version: Literal["video-directions.fidelity.v1"] = "video-directions.fidelity.v1"
    targets: list[FidelityTarget] = Field(max_length=256)


class FidelityReference(CamelModel):
    version: Literal["assistant-fidelity.v1"] = "assistant-fidelity.v1"
    batch_id: str = Field(min_length=36, max_length=36)
    attempt_id: str = Field(min_length=36, max_length=36)
    result_hash: str = Field(pattern=HASH)


class IntentAuthorization(CamelModel):
    version: Literal["production-intent.v2"] = "production-intent.v2"
    brief_hash: str = Field(pattern=HASH)


class DirectionReviewBasis(CamelModel):
    version: Literal["production-intent.v2"] = "production-intent.v2"
    batch_id: str = Field(min_length=36, max_length=36)
    manifest_hash: str = Field(pattern=HASH)
    shot_id: str = Field(min_length=1, max_length=100)
    attribution: AgentQaAttribution | None = Field(default=None, exclude_if=lambda value: value is None)
