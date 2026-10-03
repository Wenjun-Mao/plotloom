"""Non-publishing acknowledgement of a cancelled, pre-generation image block.

This deliberately does not alter the frozen successful-delivery projection.
The declaration binds a stopped worker to its request; explicit operator review
is a separate attestation, not an inferred queue-message/runtime identity.
"""
from __future__ import annotations

import json
import os
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, ValidationError, field_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value
from .image_job_contracts import ImageExecutorProvenance, ImageJobError, SHA256_PATTERN
from .image_job_exchange import EXECUTOR_PIN_FILENAME, ImageJobExchange

TERMINAL_FILENAME = "terminal.json"


class ImageBlockedOutcome(CamelModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=CamelModel.model_config["alias_generator"])
    schema_version: Literal[1]
    job_id: str = Field(pattern=r"^ij_[a-z0-9]{20,64}$")
    request_hash: str = Field(pattern=SHA256_PATTERN)
    task_id: UUID
    outcome: Literal["blocked"]
    phase: Literal["before_generation"]
    generation_started: Literal[False]
    active_tools: Literal[False]
    outputs_produced: Literal[False]
    reason: str = Field(min_length=1, max_length=2_000)
    executor_provenance: ImageExecutorProvenance

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blocked reason must not be blank")
        return value

    @field_validator("generation_started", "active_tools", "outputs_produced", mode="before")
    @classmethod
    def exact_false(cls, value):
        if value is not False:
            raise ValueError("pre-generation declarations must be boolean false")
        return value


class ImageTerminalReview(CamelModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=CamelModel.model_config["alias_generator"])
    marker_hash: str = Field(pattern=SHA256_PATTERN)
    task_id: UUID
    terminal_turn_id: UUID
    terminal_revision: int = Field(ge=1)
    observed_idle: Literal[True]
    reviewed_blocked_verdict: Literal[True]
    reviewer: str = Field(min_length=1, max_length=160)

    @field_validator("reviewer")
    @classmethod
    def nonblank_reviewer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewer must not be blank")
        return value

    @field_validator("observed_idle", "reviewed_blocked_verdict", mode="before")
    @classmethod
    def exact_true(cls, value):
        if value is not True:
            raise ValueError("operator attestations must be boolean true")
        return value


def read_blocked_outcome(exchange: ImageJobExchange, context: dict) -> dict:
    """Read only a confined final marker with the original, successful pin.

    Existing descriptor-relative primitives own no-follow confinement; reuse
    them without growing the already large successful-delivery adapter.
    """
    job_id, request_hash = context["id"], context["requestHash"]
    preflight = context["request"].get("specialistPreflight", {})
    if context["state"] != "cancelled" or preflight.get("version") != "p1.5-pin.v1":
        raise ImageJobError("image_terminal_ineligible", "只可核对已取消且成功建立执行 pin 的生成前阻塞任务。")
    descriptor = exchange._open_directory(exchange._root(), ("jobs", job_id, "delivery"))
    try:
        names = exchange._directory_names(descriptor)
        if TERMINAL_FILENAME not in names:
            raise ImageJobError("image_terminal_missing", "尚无请求绑定的 terminal.json；保留预约。")
        if names not in ({TERMINAL_FILENAME, EXECUTOR_PIN_FILENAME}, {TERMINAL_FILENAME, EXECUTOR_PIN_FILENAME, "outputs"}):
            raise ImageJobError("image_terminal_conflict", "终止声明与交付或其他文件冲突；保留预约。")
        if "outputs" in names:
            outputs = exchange._open_child_directory(descriptor, "outputs")
            try:
                if exchange._directory_names(outputs):
                    raise ImageJobError("image_terminal_conflict", "已存在输出或暂存文件，不能声明生成前阻塞。")
            finally:
                os.close(outputs)
        raw = exchange._read_regular_at(descriptor, TERMINAL_FILENAME, max_bytes=20_000)
        try:
            payload = json.loads(raw)
            marker = ImageBlockedOutcome.model_validate(payload)
        except (ValueError, TypeError, ValidationError) as error:
            raise ImageJobError("image_terminal_invalid", "终止声明格式无效；保留预约。") from error
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ImageJobError("image_terminal_secret", "终止声明含不允许的敏感设置；保留预约。")
        if marker.job_id != job_id or marker.request_hash != request_hash:
            raise ImageJobError("image_terminal_identity", "终止声明不属于此冻结请求；保留预约。")
        pin = exchange._validated_executor_pin(descriptor, job_id=job_id, request_hash=request_hash, expected_skill_version=preflight.get("skillVersion"))
        provenance = marker.executor_provenance.model_dump(mode="json", by_alias=True, exclude_none=True)
        if provenance != {key: pin[key] for key in ("codeRevision", "skillVersion", "skillHash")}:
            raise ImageJobError("image_terminal_pin", "终止声明来源与原始 executor pin 不一致；保留预约。")
        return {"marker": marker.model_dump(mode="json", by_alias=True), "markerHash": sha256(raw).hexdigest()}
    finally:
        os.close(descriptor)


def review_record(project_id: str, target: str, outcome: dict, review: ImageTerminalReview) -> dict:
    marker = outcome["marker"]
    if review.marker_hash != outcome["markerHash"] or str(review.task_id) != marker["taskId"]:
        raise ImageJobError("image_terminal_review_changed", "声明或助手身份已改变；请重新审阅，保留预约。")
    value = {"projectId": project_id, "target": target, "requestHash": marker["requestHash"],
             "markerHash": outcome["markerHash"], "marker": marker,
             "operatorReview": review.model_dump(mode="json", by_alias=True)}
    if contains_secret_setting(value) or contains_secret_value(value):
        raise ImageJobError("image_terminal_secret", "审核记录含不允许的敏感设置；保留预约。")
    return value
