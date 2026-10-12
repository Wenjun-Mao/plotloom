"""One source/settings/topology owner for frozen outline requests."""
from uuid import uuid4

from .creative_handoff_contracts import CreativeHandoffRequest
from .exceptions import InvalidTransitionError
from .outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from .source_structures import planned_structure


def outline_request(store, *, job_id=None):
    state = store.source_outline_state()
    if state.source is None:
        raise InvalidTransitionError("save an accepted source before preparing an outline candidate")
    return CreativeHandoffRequest(job_id=job_id or f"ch_{uuid4().hex}", project_id=store.manifest.project_id,
        section_id="story", stage="outline",
        expected_stage_revision=state.accepted_outline.revision if state.accepted_outline else 0,
        source=state.source.material.model_dump(mode="json", by_alias=True),
        input_artifacts={OUTLINE_SETTINGS_FILENAME: outline_settings(store.project().brief),
            "story-topology.json": planned_structure(store.manifest.project_id, store.project().brief).model_dump(mode="json", by_alias=True)},
        creative_brief=(
            "Read inputs/story-topology.json: trusted code planned the feasible Brief structure. Author prose around every viewer choice, distinct ending and reconvergence without altering topology or treating episodes as route nodes. "
            "Create one reviewable upstream outline.json candidate from the accepted author source. Preserve the adaptation intent and any supplied attribution or rights metadata without inventing missing claims. Do not claim approval, rights clearance, or edit project canon. "
            "Read inputs/outline-settings.json for the author's saved language, genre, visual style, aspect ratio, route-duration target and production scope; do not ask the author to retype them. Source owns the title and story facts; the settings artifact is not another story source. A blank adaptationIntent on an original synopsis means no additional creative direction, not permission to invent one. Report conflicts between explicit source direction and saved settings instead of silently overriding either. The duration is a route target, not guaranteed generated footage; shot-count advice/limits retain their stated policy."))
