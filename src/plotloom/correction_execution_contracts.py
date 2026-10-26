"""Application correction failure categories and immutable contract fields."""

from __future__ import annotations


class CorrectionPromptBudgetError(ValueError):
    """A correction packet cannot fit the work unit's frozen byte budget."""

    code = "contract.correction_input_budget_exceeded"


class CorrectionSourceContractError(ValueError):
    """A rejected attempt cannot be corrected under changed executable rules."""

    code = "contract.correction_source_changed"


class GraphEntityStateEffectCorrectionError(CorrectionSourceContractError):
    """Persist the graph-specific fail-closed correction disposition."""

    code = "contract.graph_entity_state_effect_correction_forbidden"


_CORRECTION_VARIANT_CONTRACT_FIELDS = frozenset(
    {
        "prompt_id",
        "prompt_version",
        "prompt_spec_hash",
        "variables_hash",
        "rendered_hash",
        "correction_ordinal",
        "correction_strategy",
        "correction_directive_set_hash",
        "correction_evidence_projection_hash",
        "correction_issue_selection_hash",
        "correction_response_schema_hash",
    }
)
