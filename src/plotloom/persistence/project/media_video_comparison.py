"""Admission for the single versioned H3 v1 vocal-control comparison."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy.orm import Session

from ...exceptions import InvalidTransitionError
from ...video_backends.minimax_h3.prompt import (
    COMPARISON_COMPILER_VERSION,
    compile_v1_vocal_control,
)
from ...video_provider import VideoProductionContract
from ..schema import VideoJobRow
from .media_video_currentness import VideoJobCurrentness


def freeze_v1_vocal_control_comparison(
    session: Session,
    *,
    project_id: str,
    baseline_job_id: str,
    snapshot: dict[str, Any],
    production_contract: VideoProductionContract | None,
    currentness: VideoJobCurrentness,
) -> None:
    """Refuse any changed input before freezing the one soundscape treatment."""

    baseline_job = session.get(VideoJobRow, baseline_job_id)
    if (
        baseline_job is None or baseline_job.project_id != project_id
        or baseline_job.state != "ingested"
        or baseline_job.snapshot.get("compilerVersion") != "plotloom.h3-i2va.v1"
        or production_contract is None
        or production_contract.adapter_id != "minimax_h3_gateway"
        or not currentness.video_job_current_in_session(session, baseline_job)
    ):
        raise InvalidTransitionError("v1 vocal comparison needs a current ingested H3 baseline")
    expected = dict(snapshot)
    expected["compilerVersion"] = "plotloom.h3-i2va.v1"
    if expected != baseline_job.snapshot:
        raise InvalidTransitionError("v1 vocal comparison changed source or provider inputs")
    try:
        _, treatment_prompt, baseline_prompt_hash = compile_v1_vocal_control(baseline_job.snapshot)
    except ValueError as exc:
        raise InvalidTransitionError(str(exc)) from exc
    snapshot["compilerVersion"] = COMPARISON_COMPILER_VERSION
    snapshot["compiledPrompt"] = treatment_prompt
    snapshot["promptComparison"] = {
        "baselineJobId": baseline_job.id,
        "baselinePromptSha256": baseline_prompt_hash,
        "treatmentPromptSha256": sha256(treatment_prompt.encode("utf-8")).hexdigest(),
        "condition": "v1_s1_only_vocal_utterance",
    }
