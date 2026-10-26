"""Compile bounded correction requests from verified immutable source evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from plotloom.generation.correction_schema import compile_correction_response_schema
from plotloom.generation.correction_schema_contracts import (
    CorrectionResponseSchemaError,
)
from plotloom.generation.planning_contracts import GenerationWorkUnit

from plotloom.run_contracts import GenerationAttempt, GenerationAttemptKind, GenerationRun
from plotloom.stage_contracts import StageName, StagePayload
from .generation.contracts import (
    ExtractionPolicy,
)
from .generation.correction_directives import (
    CorrectionDirectivePlanError,
    GraphEntityStateEffectCorrectionPlanError,
    compile_correction_instruction_plan,
)
from .generation.prompts import PromptRenderer
from .generation.work_unit_contracts import (
    CompiledWorkUnitRequest,
)

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from .correction_execution_contracts import (
    CorrectionPromptBudgetError,
    CorrectionSourceContractError,
    GraphEntityStateEffectCorrectionError,
)
from .correction_source import verify_correction_source


def compile_correction_request(
    repository: "GenerationRunRepository",
    renderer: PromptRenderer,
    *,
    run: GenerationRun,
    work_unit: GenerationWorkUnit,
    work_unit_id: str,
    base_compiled: CompiledWorkUnitRequest,
    source_attempt: GenerationAttempt,
    dependencies: Mapping[StageName, StagePayload],
    extraction_policy: ExtractionPolicy,
) -> CompiledWorkUnitRequest:
    """Render one compact correction packet from durable final evidence.

    The closed response schema carries the immutable topology/selector
    structure.  The correction packet deliberately omits the broader
    creative context: the previous final answer supplies its prose while
    the schema, frozen contract, and stable code/path pairs supply the only
    correction authority.  Free-form validator messages remain in the
    audit artifact.
    """

    evidence = verify_correction_source(
        repository,
        run=run,
        work_unit=work_unit,
        work_unit_id=work_unit_id,
        base_compiled=base_compiled,
        source_attempt=source_attempt,
        dependencies=dependencies,
        extraction_policy=extraction_policy,
    )
    previous_final_content = evidence.previous_final_content
    source_contract = evidence.source_contract
    validated_issues = evidence.validated_issues
    parsed_repair_facts = evidence.parsed_repair_facts
    try:
        instruction_plan = compile_correction_instruction_plan(
            validated_issues,
            parsed_repair_facts,
        )
        executable_repair_facts = tuple(
            parsed_repair_facts[index]
            for index in instruction_plan.executable_fact_indexes
        )
        correction_schema = compile_correction_response_schema(
            base_compiled.response_schema,
            executable_repair_facts,
        )
    except GraphEntityStateEffectCorrectionPlanError as error:
        raise GraphEntityStateEffectCorrectionError(str(error)) from error
    except (CorrectionDirectivePlanError, CorrectionResponseSchemaError) as error:
        raise CorrectionSourceContractError(str(error)) from error
    issues = [
        {
            "code": validated_issues[index].code,
            "path": list(validated_issues[index].path),
        }
        for index in instruction_plan.executable_issue_indexes
    ]
    correction_ordinal = source_attempt.attempt_number
    correction_strategy = (
        "repair_previous_final"
        if correction_ordinal == 1
        else "reconstruct_from_schema"
    )
    rendered = renderer.render(
        "work_unit_correction",
        {
            "original_contract": base_compiled.contract.snapshot_dump(),
            "response_schema": correction_schema.schema,
            "previous_final_content": previous_final_content,
            "validation_issues": issues,
            "repair_evidence_projection": instruction_plan.prompt_evidence,
            "correction_directives": [
                directive.model_dump(mode="json")
                for directive in instruction_plan.directives
            ],
            "correction_ordinal": correction_ordinal,
            "correction_strategy": correction_strategy,
        },
    )
    if source_attempt.attempt_kind == GenerationAttemptKind.CORRECTION:
        current_prompt_identity = {
            "prompt_id": rendered.trace.prompt_id,
            "prompt_version": rendered.trace.prompt_version,
            "prompt_spec_hash": rendered.trace.spec_hash,
        }
        if any(
            source_contract.get(key) != value
            for key, value in current_prompt_identity.items()
        ):
            raise CorrectionSourceContractError(
                "correction prompt contract changed after the source rejection"
            )
    input_bytes = sum(
        len(message.content.encode("utf-8")) for message in rendered.messages
    )
    if input_bytes > work_unit.budget.max_input_bytes:
        raise CorrectionPromptBudgetError(
            "correction prompt is "
            f"{input_bytes} bytes, exceeding the frozen max_input_bytes "
            f"budget of {work_unit.budget.max_input_bytes}"
        )
    contract = type(base_compiled.contract).model_validate(
        {
            **base_compiled.contract.snapshot_dump(),
            "prompt_id": rendered.trace.prompt_id,
            "prompt_version": rendered.trace.prompt_version,
            "prompt_spec_hash": rendered.trace.spec_hash,
            "variables_hash": rendered.trace.input_hash,
            "rendered_hash": rendered.trace.rendered_hash,
            "correction_ordinal": correction_ordinal,
            "correction_strategy": correction_strategy,
            "correction_directive_set_hash": instruction_plan.directive_set_hash,
            "correction_evidence_projection_hash": (
                instruction_plan.evidence_projection_hash
            ),
            "correction_issue_selection_hash": (instruction_plan.issue_selection_hash),
            "correction_response_schema_hash": correction_schema.schema_hash,
        }
    )
    return CompiledWorkUnitRequest(
        rendered=rendered,
        validator=base_compiled.validator,
        contract=contract,
        response_schema=correction_schema.schema,
        audit_issue_selection=instruction_plan.audit_issue_selection,
        correction_repair_facts=executable_repair_facts,
    )
