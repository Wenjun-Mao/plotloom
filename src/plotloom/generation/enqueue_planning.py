"""Enqueue-time planning from canonical inputs and provider bounds."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel

from ..domain import (
    STAGE_ORDER,
    StageName,
)
from .planning_contracts import (
    DEFAULT_STAGE_BUDGETS,
    PLANNING_POLICY_VERSION,
    GenerationPlan,
    PlanningError,
    StageBudget,
    _json_value,
    content_hash,
)
from .prompts import canonical_json, sha256_text


def create_generation_plan(
    *,
    run_id: str,
    requested_stages: tuple[StageName, ...] | list[StageName],
    provider_profile_hash: str,
    story_graph_topology_hash: str | None = None,
    canonical_snapshot: BaseModel | Mapping[str, Any] | None = None,
    canonical_snapshot_hash: str | None = None,
    canonical_snapshot_bytes: int | None = None,
    instructions: str | None = None,
    canonical_inputs: Mapping[StageName, BaseModel | Mapping[str, Any]] | None = None,
    stage_budgets: Mapping[StageName, StageBudget] | None = None,
    provider_output_token_ceiling: int | None = None,
    max_concurrency: int = 1,
    context_window_tokens: int = 32_768,
    prompt_overhead_bytes: int = 16_384,
    planning_policy_version: str = PLANNING_POLICY_VERSION,
) -> GenerationPlan:
    """Freeze enqueue-time bounds without creating future entity selectors."""

    requested = tuple(requested_stages)
    _validate_requested_range(requested)
    if provider_output_token_ceiling is not None and (
        isinstance(provider_output_token_ceiling, bool)
        or provider_output_token_ceiling < 1
    ):
        raise PlanningError("provider_output_token_ceiling must be at least 1")
    snapshot_json: str | None = None
    if canonical_snapshot is not None:
        snapshot_json = canonical_json(_json_value(canonical_snapshot))
        computed_snapshot_hash = sha256_text(snapshot_json)
        computed_snapshot_bytes = len(snapshot_json.encode("utf-8"))
        if (
            canonical_snapshot_hash is not None
            and canonical_snapshot_hash != computed_snapshot_hash
        ):
            raise PlanningError(
                "canonical_snapshot_hash does not match canonical_snapshot"
            )
        if (
            canonical_snapshot_bytes is not None
            and canonical_snapshot_bytes != computed_snapshot_bytes
        ):
            raise PlanningError(
                "canonical_snapshot_bytes does not match canonical_snapshot"
            )
    if canonical_snapshot_hash is None:
        if snapshot_json is None:
            raise PlanningError(
                "canonical_snapshot or canonical_snapshot_hash is required when enqueueing"
            )
        canonical_snapshot_hash = sha256_text(snapshot_json)
    if canonical_snapshot_bytes is None:
        if snapshot_json is None:
            raise PlanningError(
                "canonical_snapshot_bytes is required when only a snapshot hash is supplied"
            )
        canonical_snapshot_bytes = len(snapshot_json.encode("utf-8"))
    if canonical_snapshot_bytes < 0:
        raise PlanningError("canonical_snapshot_bytes cannot be negative")
    instructions_json = instructions or ""
    instructions_hash = sha256_text(instructions_json)
    instructions_bytes = len(instructions_json.encode("utf-8"))
    run_request_hash = sha256_text(
        canonical_json(
            {
                "canonical_snapshot_hash": canonical_snapshot_hash,
                "instructions_hash": instructions_hash,
            }
        )
    )
    existing = canonical_inputs or {}
    allowed_inputs = set(STAGE_ORDER[: STAGE_ORDER.index(requested[0])])
    unexpected = set(existing) - allowed_inputs
    if unexpected:
        names = ", ".join(
            stage.value for stage in sorted(unexpected, key=STAGE_ORDER.index)
        )
        raise PlanningError(
            "run-level plans may freeze only canonical inputs that precede the "
            f"requested range; got {names}"
        )
    supplied_budgets = stage_budgets or {}
    unknown_budgets = set(supplied_budgets) - set(requested)
    if unknown_budgets:
        names = ", ".join(
            stage.value for stage in sorted(unknown_budgets, key=STAGE_ORDER.index)
        )
        raise PlanningError(f"budgets were supplied for unrequested stages: {names}")
    budgets: dict[StageName, StageBudget] = {}
    for stage in requested:
        requested_budget = supplied_budgets.get(stage, DEFAULT_STAGE_BUDGETS[stage])
        if provider_output_token_ceiling is not None:
            requested_budget = requested_budget.model_copy(
                update={
                    "max_output_tokens": min(
                        requested_budget.max_output_tokens,
                        provider_output_token_ceiling,
                    )
                }
            )
        budgets[stage] = requested_budget
        if requested_budget.max_output_tokens >= context_window_tokens:
            raise PlanningError(
                f"{stage.value} max_output_tokens must leave room for provider input",
                code="planning.output_budget_exceeds_context",
                stage=stage,
            )
    input_hashes = {
        stage: content_hash(value)
        for stage, value in sorted(
            existing.items(), key=lambda item: STAGE_ORDER.index(item[0])
        )
    }
    policy_hash = sha256_text(planning_policy_version)
    unsigned = {
        "run_id": run_id,
        "requested_stages": [stage.value for stage in requested],
        "planning_policy_version": planning_policy_version,
        "planning_policy_hash": policy_hash,
        "provider_profile_hash": provider_profile_hash,
        "canonical_snapshot_hash": canonical_snapshot_hash,
        "canonical_snapshot_bytes": canonical_snapshot_bytes,
        "instructions_hash": instructions_hash,
        "instructions_bytes": instructions_bytes,
        "run_request_hash": run_request_hash,
        "canonical_input_hashes": {
            stage.value: value for stage, value in input_hashes.items()
        },
        "stage_budgets": {
            stage.value: budget.model_dump(mode="json")
            for stage, budget in budgets.items()
        },
        "max_concurrency": max_concurrency,
        "context_window_tokens": context_window_tokens,
        "prompt_overhead_bytes": prompt_overhead_bytes,
    }
    unsigned["story_graph_topology_hash"] = story_graph_topology_hash
    return GenerationPlan(
        run_id=run_id,
        requested_stages=requested,
        planning_policy_version=planning_policy_version,
        planning_policy_hash=policy_hash,
        provider_profile_hash=provider_profile_hash,
        story_graph_topology_hash=story_graph_topology_hash,
        canonical_snapshot_hash=canonical_snapshot_hash,
        canonical_snapshot_bytes=canonical_snapshot_bytes,
        instructions_hash=instructions_hash,
        instructions_bytes=instructions_bytes,
        run_request_hash=run_request_hash,
        canonical_input_hashes=input_hashes,
        stage_budgets=budgets,
        max_concurrency=max_concurrency,
        context_window_tokens=context_window_tokens,
        prompt_overhead_bytes=prompt_overhead_bytes,
        plan_hash=sha256_text(canonical_json(unsigned)),
    )


def _validate_requested_range(requested: tuple[StageName, ...]) -> None:
    if not requested:
        raise PlanningError("generation plans require at least one requested stage")
    if len(requested) != len(set(requested)):
        raise PlanningError("requested stages must not contain duplicates")
    first = STAGE_ORDER.index(requested[0])
    expected = STAGE_ORDER[first : first + len(requested)]
    if requested != expected:
        raise PlanningError("requested stages must form a contiguous canonical range")
