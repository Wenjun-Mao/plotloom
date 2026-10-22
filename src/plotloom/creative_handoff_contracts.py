"""Candidate-only contracts for the manual Shuohao creative handoff.

F0 deliberately does not define a second canonical authoring model.  The
specialist returns a stage-shaped proposal; the existing project/review owner
must decide whether, and at which current revision, to install it.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value
from .text_correction_contracts import TextCorrection


CREATIVE_STAGES = ("outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation", "video-directions")
CreativeStage = Literal["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation", "video-directions"]
CREATIVE_CANDIDATE_FILENAMES = {
    "branches": "branches.json",
    "outline": "outline.json",
    "characters": "cast.json",
    "art": "art.json",
    "script": "script.json",
    "storyboard": "storyboard.json",
    "bridge-intent": "intent.json",
    "bridge-presentation": "presentation.json",
    "video-directions": "directions.json",
}
SHA256_PATTERN = r"^[a-f0-9]{64}$"
JOB_ID_PATTERN = r"^ch_[a-z0-9]{20,64}$"
DELIVERY_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"


class CreativeHandoffError(ValueError):
    """A stable, non-secret error at the manual creative boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CreativeHandoffRequest(CamelModel):
    """A frozen, self-contained request for exactly one creative stage."""

    schema_version: Literal[1] = 1
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    project_id: str = Field(min_length=1, max_length=128)
    section_id: str = Field(min_length=1, max_length=128)
    stage: CreativeStage
    expected_stage_revision: int = Field(ge=0)
    source: dict[str, Any]
    input_artifacts: dict[str, Any] = Field(default_factory=dict)
    creative_brief: str = Field(min_length=1, max_length=20_000)
    text_correction: TextCorrection | None = Field(default=None, exclude_if=lambda value: value is None)
    content_validation_contract: Literal["plotloom.typed-content-result.v1"] | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("source")
    @classmethod
    def source_is_an_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("source must be a nonempty object")
        return value

    @field_validator("input_artifacts")
    @classmethod
    def inputs_have_plain_names(cls, value: dict[str, Any]) -> dict[str, Any]:
        for name, artifact in value.items():
            if not name.endswith(".json") or "/" in name or "\\" in name or name.startswith("."):
                raise ValueError("inputArtifacts keys must be plain .json filenames")
            if not isinstance(artifact, dict):
                raise ValueError("inputArtifacts values must be JSON objects")
        return value

    @field_validator("creative_brief")
    @classmethod
    def brief_is_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("creativeBrief must not be blank")
        return value

    def assert_secret_free(self) -> None:
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise CreativeHandoffError("request_secret", "creative handoff requests must not contain credentials")


def creative_handoff_request_from_package(package_payload: Mapping[str, Any]) -> CreativeHandoffRequest:
    """Project a frozen package onto the exact creative request contract.

    Package metadata is validated by its package owner. This shared projection
    keeps request validation and completion publication aligned as that
    metadata evolves, while the request model itself continues to reject extras.
    """
    if not isinstance(package_payload, Mapping):
        raise TypeError("creative handoff package payload must be an object")
    request_fields = {
        field.alias or name
        for name, field in CreativeHandoffRequest.model_fields.items()
    }
    return CreativeHandoffRequest.model_validate({
        key: value for key, value in package_payload.items() if key in request_fields
    })


class CreativeOutput(CamelModel):
    filename: str = Field(min_length=1, max_length=180)
    sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("filename")
    @classmethod
    def filename_is_confined(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value or value.startswith("."):
            raise ValueError("filename must be a plain filename")
        return value


class CreativeExecutorProvenance(CamelModel):
    code_revision: str = Field(min_length=7, max_length=64, pattern=r"^[a-f0-9]+$")
    skill_version: str = Field(min_length=1, max_length=80)
    skill_hash: str = Field(pattern=SHA256_PATTERN)
    upstream_revision: str = Field(min_length=7, max_length=64, pattern=r"^[a-f0-9]+$")
    upstream_skill_hash: str = Field(pattern=SHA256_PATTERN)
    model: str | None = Field(default=None, max_length=128)
    reasoning_effort: str | None = Field(default=None, max_length=32)


class CreativeDeliveryManifest(CamelModel):
    schema_version: Literal[1, 2, 3] = 1
    executor_backend: Literal["codex_exec"] | None = Field(default=None, exclude_if=lambda value: value is None)
    executor_attempt_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    codex_session_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    executor_profile_hash: str | None = Field(default=None, pattern=SHA256_PATTERN, exclude_if=lambda value: value is None)
    validation_plan_hash: str | None = Field(default=None, pattern=SHA256_PATTERN, exclude_if=lambda value: value is None)
    validation_evidence_hash: str | None = Field(default=None, pattern=SHA256_PATTERN, exclude_if=lambda value: value is None)
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    request_hash: str = Field(pattern=SHA256_PATTERN)
    delivery_id: str = Field(pattern=DELIVERY_ID_PATTERN)
    stage: CreativeStage
    candidate: CreativeOutput
    report: CreativeOutput
    executor_provenance: CreativeExecutorProvenance
    limitations: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def filenames_are_distinct(self) -> "CreativeDeliveryManifest":
        if self.candidate.filename == self.report.filename:
            raise ValueError("candidate and report filenames must differ")
        executor_fields = (self.executor_backend, self.executor_attempt_id, self.codex_session_id, self.executor_profile_hash)
        if self.schema_version == 1 and any(value is not None for value in executor_fields):
            raise ValueError("specialist-chat creative manifests cannot claim Codex Exec identity")
        if self.schema_version == 2 and (
            self.executor_backend != "codex_exec" or self.executor_attempt_id is None
            or self.codex_session_id is None or self.executor_profile_hash is None
        ):
            raise ValueError("Codex Exec creative manifests require their exact attempt, session and profile")
        validation_fields = (self.validation_plan_hash, self.validation_evidence_hash)
        if self.schema_version in {1, 2} and any(value is not None for value in validation_fields):
            raise ValueError("older creative manifests cannot claim trusted text validation proof")
        if self.schema_version == 3 and (
            self.executor_backend != "codex_exec" or self.executor_attempt_id is None
            or self.codex_session_id is None or self.executor_profile_hash is None
            or any(value is None for value in validation_fields)
        ):
            raise ValueError("validated Codex Exec manifests require exact attempt, profile and validation proof")
        return self

    @field_validator("limitations")
    @classmethod
    def limitations_are_bounded(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 2_000 for item in value):
            raise ValueError("limitations must be nonblank and at most 2,000 characters")
        return value

    def assert_secret_free(self) -> None:
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise CreativeHandoffError("delivery_manifest_secret", "completion manifest must not contain credentials")


def is_creative_job_id(value: str) -> bool:
    return re.fullmatch(JOB_ID_PATTERN, value) is not None
