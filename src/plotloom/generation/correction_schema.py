"""Deterministic correction schema assembly and exact result hashing."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .correction_contract import CORRECTION_RESPONSE_SCHEMA_VERSION
from .correction_schema_continuity import ContinuityCorrectionSchema
from .correction_schema_contracts import CorrectionResponseSchema
from .correction_schema_cue_timing import CueTimingCorrectionSchema
from .correction_schema_graph import GraphCorrectionSchema
from .prompts import canonical_json, sha256_text
from .repair_facts import (
    SemanticRepairFact,
)


def compile_correction_response_schema(
    base_schema: Mapping[str, Any],
    facts: Sequence[SemanticRepairFact],
) -> CorrectionResponseSchema:
    """Return a deep-copied schema narrowed by typed repair authority.

    Unsupported fact types deliberately leave the schema unchanged. They may
    still be executable through their versioned prompt directive and the
    canonical validator. Exact facts are independently checked after response
    validation, so this schema is a constrained-decoding aid rather than the
    trust boundary. A supported fact with incomplete or contradictory authority
    fails closed instead of silently falling back to prose.
    """

    schema = deepcopy(dict(base_schema))
    graph = GraphCorrectionSchema()
    continuity = ContinuityCorrectionSchema()
    cue_timing = CueTimingCorrectionSchema()
    for fact in facts:
        if graph.collect(fact):
            continue
        if continuity.collect(fact):
            continue
        cue_timing.collect(fact)
    graph.apply(schema)
    continuity.apply(schema)
    cue_timing.apply(schema)
    applied_codes = (
        graph.applied_codes | continuity.applied_codes | cue_timing.applied_codes
    )

    return CorrectionResponseSchema(
        version=CORRECTION_RESPONSE_SCHEMA_VERSION,
        schema=schema,
        schema_hash=sha256_text(canonical_json(schema)),
        applied_fact_codes=tuple(sorted(applied_codes)),
    )
