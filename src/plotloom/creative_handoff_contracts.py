"""Candidate-only contracts for the manual Shuohao creative handoff.

F0 deliberately does not define a second canonical authoring model.  The
specialist returns a stage-shaped proposal; the existing project/review owner
must decide whether, and at which current revision, to install it.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value


CREATIVE_STAGES = ("outline", "characters", "art", "script", "storyboard")
CreativeStage = Literal["outline", "characters", "art", "script", "storyboard"]
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
    model: str | None = Field(default=None, max_length=128)
    reasoning_effort: str | None = Field(default=None, max_length=32)


class CreativeDeliveryManifest(CamelModel):
    schema_version: Literal[1] = 1
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
