"""Typed candidate rejection and immutable, single-correction lineage."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .domain import CamelModel

HASH = r"^[a-f0-9]{64}$"


class TextContentIssue(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    code: Literal["candidate_content_invalid", "art_prop_scale"]
    field_paths: tuple[str, ...] = Field(max_length=128)
    repair_facts: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def source_owned_vocabulary(self):
        if self.code == "candidate_content_invalid":
            if self.repair_facts or self.field_paths != ("$",):
                raise ValueError("generic content feedback cannot contain untrusted prose")
        else:
            import re
            if (not self.field_paths or any(re.fullmatch(r"props\[[0-9]+\]\.(scale|image\.(prompt|sheet))", p) is None for p in self.field_paths)
                    or set(self.repair_facts) != {"requiredPhrase"}
                    or self.repair_facts["requiredPhrase"] not in {"handheld scale", "tabletop scale", "furniture scale"}):
                raise ValueError("art scale feedback must use source-owned paths and vocabulary")
        return self


class TextContentRejection(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    contract: Literal["plotloom.text-content-rejection.v1"] = "plotloom.text-content-rejection.v1"
    source_attempt_id: UUID
    run_id: UUID
    stage: Literal["outline", "characters", "art"]
    job_id: str
    candidate_hash: str = Field(pattern=HASH)
    validation_evidence_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    plan_hash: str = Field(pattern=HASH)
    profile_hash: str = Field(pattern=HASH)
    source_revision: str
    issues: tuple[TextContentIssue, ...] = Field(min_length=1, max_length=128)

    @property
    def rejection_hash(self):
        return sha256(json.dumps(self.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

    def assert_attempt(self, attempt):
        if (attempt.domain != "text" or attempt.state not in {"failed", "settled"}
                or attempt.terminal_result != "failure" or attempt.process_exit_code != 0
                or attempt.session_id is None or attempt.process_id is None
                or any(getattr(self, own) != getattr(attempt, other) for own, other in (
                    ("source_attempt_id", "attempt_id"), ("run_id", "run_id"), ("job_id", "job_id"),
                    ("request_hash", "request_hash"), ("package_hash", "package_hash"),
                    ("plan_hash", "validation_plan_hash"), ("profile_hash", "profile_hash"),
                    ("source_revision", "plotloom_code_revision")))):
            raise ValueError("content rejection differs from its exact completed CLI failure")


class TextCorrection(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    ordinal: int = Field(default=1, strict=True, ge=1, le=1)
    rejection: TextContentRejection
    prior_candidate_json: str = Field(min_length=2, max_length=500_000)

    @model_validator(mode="after")
    def exact_prior_bytes(self):
        if (sha256(self.prior_candidate_json.encode("utf-8")).hexdigest() != self.rejection.candidate_hash
                or not isinstance(json.loads(self.prior_candidate_json), dict)):
            raise ValueError("correction prior candidate differs from rejected exact bytes")
        return self


def correction_key(stage):
    return f"{stage}:correction:1"


def logical_checkpoint(view, stage):
    """One stage resolves to its sole immutable correction when present."""
    return next((c for c in view.checkpoints if c["operationKey"] == correction_key(stage)),
        next((c for c in view.checkpoints if c["operationKey"] == stage), None))
