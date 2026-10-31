"""One source/settings/topology owner for frozen outline requests."""
from uuid import uuid4

from .creative_handoff_contracts import CreativeHandoffRequest
from .exceptions import InvalidTransitionError
from .language_policy import (
    LANGUAGE_CONTRACT_FILENAME,
    language_contract,
    language_instructions,
)
from .outline_echoes import ECHO_CONTRACT_FILENAME, outline_echo_contract
from .outline_report_metadata import (
    OUTLINE_REPORT_SCHEMA_FILENAME,
    outline_report_metadata_schema,
)
from .outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from .outline_structure_authority import (
    outline_structure_inputs,
    outline_structure_instructions,
)


def outline_request(store, *, job_id=None):
    state = store.source_outline_state()
    if state.source is None:
        raise InvalidTransitionError("save an accepted source before preparing an outline candidate")
    return CreativeHandoffRequest(job_id=job_id or f"ch_{uuid4().hex}", project_id=store.manifest.project_id,
        section_id="story", stage="outline",
        content_validation_contract="plotloom.typed-content-result.v1",
        expected_stage_revision=state.accepted_outline.revision if state.accepted_outline else 0,
        source=state.source.material.model_dump(mode="json", by_alias=True),
        input_artifacts={ECHO_CONTRACT_FILENAME: outline_echo_contract(), OUTLINE_SETTINGS_FILENAME: outline_settings(store.project().require_brief()),
            LANGUAGE_CONTRACT_FILENAME: language_contract(store.project().require_brief().language),
            OUTLINE_REPORT_SCHEMA_FILENAME: outline_report_metadata_schema(),
            **outline_structure_inputs(store.manifest.project_id, store.project().require_brief(), state.source.material)},
        creative_brief=(
            "Read inputs/outline-report-metadata-schema.json: it constrains report metadata and forbids the unsupported top-level routePlan field while permitting upstream creative fields. Top-level lang must match the frozen project report locale, exactly zh/en. Do not copy a content locale such as zh-CN into lang. "
            + outline_structure_instructions(state.source.material)
            + "Create one reviewable upstream outline.json candidate from the accepted author source. Preserve the adaptation intent and any supplied attribution or rights metadata without inventing missing claims. Do not claim approval, rights clearance, or edit project canon. "
            "Read inputs/outline-settings.json for the author's saved language, genre, visual style, aspect ratio, route-duration target and production scope; do not ask the author to retype them. Source owns the title and story facts; the settings artifact is not another story source. A blank adaptationIntent on an original synopsis means no additional creative direction, not permission to invent one. Report conflicts between explicit source direction and saved settings instead of silently overriding either. The duration is a route target, not guaranteed generated footage; shot-count advice/limits retain their stated policy."
            + f" Optional copied settings, sourceMetadata and {'sourceStructure' if state.source.material.authored_structure else 'storyTopology'} may be omitted. If included, copy the registered machine values exactly from their frozen inputs, including all topology keys and values; never translate IDs, enums, locale, aspect ratio, hashes or preset-selection identities. sourceMetadata contains only exact original metadata. Omit routePlan entirely. Keep authored story, viewer-choice and ending explanations in existing Outline fields. Frozen topology guides those explanations; Branches owns the installed graph. A correction must remove an unnecessary echo or restore its exact input value, never translate machine values to satisfy prose language checking. "
            + language_instructions(store.project().require_brief().language)))
