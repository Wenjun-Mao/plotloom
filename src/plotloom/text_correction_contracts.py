"""Typed candidate rejection and immutable, single-correction lineage."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from plotloom.domain_base import CamelModel

HASH = r"^[a-f0-9]{64}$"
CONTENT_DIAGNOSTIC_COUNT = 32
CONTENT_DIAGNOSTIC_LENGTH = 1000
CORRECTION_CONTRACT = "plotloom.text-correction.v4"
SCRIPT_CORRECTION_CONTRACTS = frozenset({"plotloom.text-correction.v3", CORRECTION_CONTRACT})
MANUAL_CORRECTION_CONTRACTS = frozenset({"plotloom.text-correction.v2", *SCRIPT_CORRECTION_CONTRACTS})
MANUAL_CORRECTION_STAGES = frozenset({"outline", "branches", "characters", "art", "script", "storyboard",
                                      "bridge-intent", "bridge-presentation"})


def content_correction_capability(binding, stage):
    if binding is None:
        return False
    if stage == "script":
        return binding.text_correction_contract in SCRIPT_CORRECTION_CONTRACTS
    if stage == "storyboard":
        return binding.text_correction_contract == CORRECTION_CONTRACT
    if stage in {"branches", "bridge-intent", "bridge-presentation"}:
        return binding.text_correction_contract == CORRECTION_CONTRACT
    return stage in MANUAL_CORRECTION_STAGES and (
        binding.text_correction_contract in MANUAL_CORRECTION_CONTRACTS or binding.text_correction_limit == 1)


def automatic_correction_limit(policy, stage):
    limit = policy.text_correction_limit or 0
    if stage in {"script", "storyboard", "branches", "bridge-intent", "bridge-presentation"}:
        if not content_correction_capability(policy.executor_binding, stage):
            return 0
        return min(1, limit)
    return limit


class TextContentIssue(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    code: Literal["candidate_content_invalid", "art_prop_scale", "content_language_mismatch"]
    field_paths: tuple[str, ...] = Field(max_length=128)
    repair_facts: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def source_owned_vocabulary(self):
        if self.code == "candidate_content_invalid":
            if self.repair_facts or self.field_paths != ("$",):
                raise ValueError("generic content feedback cannot contain untrusted prose")
        elif self.code == "content_language_mismatch":
            import re
            if (not self.field_paths or len(set(self.field_paths)) != len(self.field_paths)
                    or any(re.fullmatch(r"\$\.[A-Za-z][A-Za-z0-9_]*(?:(?:\[[0-9]+\])|(?:\.[A-Za-z][A-Za-z0-9_]*))*", path) is None
                           for path in self.field_paths)
                    or set(self.repair_facts) != {"contentLocale"}
                    or self.repair_facts["contentLocale"] not in {"zh-CN", "en-US"}):
                raise ValueError("language correction requires trusted exact paths and supported locale only")
        else:
            import re
            if (not self.field_paths or any(re.fullmatch(r"props\[[0-9]+\]\.(scale|image\.(prompt|sheet))", p) is None for p in self.field_paths)
                    or set(self.repair_facts) != {"requiredPhrase"}
                    or self.repair_facts["requiredPhrase"] not in {"handheld scale", "tabletop scale", "furniture scale"}):
                raise ValueError("art scale feedback must use source-owned paths and vocabulary")
        return self


class LanguageRejectionProof(CamelModel):
    check_job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    check_attempt_id: UUID
    check_receipt_hash: str = Field(pattern=HASH)
    binding_hash: str = Field(pattern=HASH)
    result_hash: str = Field(pattern=HASH)


class TextContentRejection(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    contract: Literal["plotloom.text-content-rejection.v1"] = "plotloom.text-content-rejection.v1"
    source_attempt_id: UUID
    run_id: UUID
    stage: Literal["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"]
    job_id: str
    candidate_hash: str = Field(pattern=HASH)
    validation_evidence_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    plan_hash: str = Field(pattern=HASH)
    profile_hash: str = Field(pattern=HASH)
    source_revision: str
    language_check: LanguageRejectionProof | None = Field(default=None, exclude_if=lambda value: value is None)
    issues: tuple[TextContentIssue, ...] = Field(min_length=1, max_length=128)
    display_diagnostics: tuple[Annotated[str, Field(max_length=CONTENT_DIAGNOSTIC_LENGTH)], ...] = Field(default=(), max_length=CONTENT_DIAGNOSTIC_COUNT, exclude_if=lambda value: not value)

    @property
    def rejection_hash(self):
        return sha256(json.dumps(self.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

    def assert_attempt(self, attempt):
        states, terminal = ({"completed", "settled"}, "success") if self.language_check else ({"failed", "settled"}, "failure")
        if (attempt.domain != "text" or attempt.state not in states
                or attempt.terminal_result != terminal or attempt.process_exit_code != 0
                or attempt.session_id is None or attempt.process_id is None
                or any(getattr(self, own) != getattr(attempt, other) for own, other in (
                    ("source_attempt_id", "attempt_id"), ("run_id", "run_id"), ("job_id", "job_id"),
                    ("request_hash", "request_hash"), ("package_hash", "package_hash"),
                    ("plan_hash", "validation_plan_hash"), ("profile_hash", "profile_hash"),
                    ("source_revision", "plotloom_code_revision")))):
            raise ValueError("content rejection differs from its exact completed CLI failure")
        if self.language_check is not None and (self.language_check.check_attempt_id == attempt.attempt_id
                or any(issue.code != "content_language_mismatch" for issue in self.issues)):
            raise ValueError("semantic rejection requires a distinct checking attempt and constrained language issues")


class TextRetryGrant(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    command_id: UUID
    expected_run_id: UUID
    expected_revision: int = Field(strict=True, ge=1)
    failed_attempt_id: UUID
    rejection_hash: str = Field(pattern=HASH)
    directions: str = Field(default="", max_length=4000)


class TextCorrection(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    ordinal: int = Field(default=1, strict=True, ge=1)
    manual_grant: TextRetryGrant | None = Field(default=None, exclude_if=lambda value: value is None)
    rejection: TextContentRejection
    prior_candidate_json: str = Field(min_length=2, max_length=500_000)

    @model_validator(mode="after")
    def exact_prior_bytes(self):
        if (len(self.prior_candidate_json.encode("utf-8")) > 500_000
                or sha256(self.prior_candidate_json.encode("utf-8")).hexdigest() != self.rejection.candidate_hash
                or not isinstance(json.loads(self.prior_candidate_json), dict)):
            raise ValueError("correction prior candidate differs from rejected exact bytes")
        if self.manual_grant is not None and self.rejection.stage not in MANUAL_CORRECTION_STAGES:
            raise ValueError("stage has no manual extra-correction authority")
        if self.manual_grant is not None and (
                self.manual_grant.expected_run_id != self.rejection.run_id
                or self.manual_grant.failed_attempt_id != self.rejection.source_attempt_id
                or self.manual_grant.rejection_hash != self.rejection.rejection_hash):
            raise ValueError("manual retry grant differs from its exact failed attempt")
        return self


def correction_key(stage, ordinal=1):
    return f"{stage}:correction:{ordinal}"


def logical_checkpoint(view, stage):
    """Resolve the latest immutable physical attempt of one logical stage."""
    from .autopilot_execution_retry import retry_root, retry_ordinal
    candidates = [c for c in view.checkpoints if retry_root(c["operationKey"]) == stage
        or retry_root(c["operationKey"]).startswith(f"{stage}:correction:")]
    for candidate in candidates:
        if retry_root(candidate["operationKey"]) == stage:
            continue
        ordinal = candidate["evidence"]["result"].get("correctionOrdinal")
        if type(ordinal) is not int or ordinal < 1 or retry_root(candidate["operationKey"]) != correction_key(stage, ordinal):
            raise ValueError("malformed correction checkpoint identity")
    return max(candidates, key=lambda c: (c["evidence"]["result"].get("correctionOrdinal", 0), retry_ordinal(c)), default=None)
