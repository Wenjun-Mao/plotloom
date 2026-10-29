"""Exact source inventory selects the one supported text-only bridge rebuild."""
from types import SimpleNamespace

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence
from ...exceptions import InvalidTransitionError
from ...production_presentation import (
    PresentationUpdate,
    ProductionPresentation,
    bind_presentation_spans,
    prepare_presentation,
)
from ...text_correction_contracts import logical_checkpoint
from ..schema import AutopilotRunRow, Base

RAW_OPERATIONS = {"source", "outline", "branches", "characters", "art", "script", "storyboard"}
BRIDGE_OPERATIONS = {"bridge.prepare", "bridge-intent", "bridge-presentation", "installation"}
CREATIVE_OPERATIONS = (RAW_OPERATIONS | BRIDGE_OPERATIONS) - {"source", "bridge.prepare", "installation"}
DEPENDENT_TABLES = (
    "v2_image_jobs", "v2_character_reference_proposals", "v2_character_reference_decisions",
    "v2_art_reference_proposals", "v2_art_reference_decisions", "v2_character_imported_appearances",
    "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_shot_presentations",
    "v2_autopilot_frames", "v2_autopilot_handoffs", "v2_video_jobs", "v2_video_batches",
    "v2_video_end_frame_decisions", "v2_same_person_reviews",
)


def _assert_no_dependent_material(session, project_id):
    for name in DEPENDENT_TABLES:
        table = Base.metadata.tables[name]
        if session.execute(select(table.c.project_id).where(table.c.project_id == project_id).limit(1)).first():
            raise InvalidTransitionError(f"frame-bound presentation has dependent material: {name}")
    runs = session.scalars(select(AutopilotRunRow).where(AutopilotRunRow.project_id == project_id)).all()
    if any(row.bundle is not None or row.handoff is not None for row in runs):
        raise InvalidTransitionError("frame-bound presentation has retained bundle or handoff authority")


def _logical_installation(session, run, checkpoints):
    """Keep exact physical rows while resolving validated correction/retry chains."""
    from .autopilot_bindings import assert_retained_checkpoint_provenance

    by_key = {row.operation_key: row for row in checkpoints}
    view = SimpleNamespace(checkpoints=[{"operationKey": row.operation_key,
        "state": row.state, "evidence": row.evidence} for row in checkpoints])
    selected, covered = {}, set()
    for key in RAW_OPERATIONS | BRIDGE_OPERATIONS:
        logical = logical_checkpoint(view, key) if key in CREATIVE_OPERATIONS else None
        row = by_key.get(logical["operationKey"] if logical else key)
        if row is None or row.state != "adopted":
            raise InvalidTransitionError("Continue requires a complete adopted logical text installation")
        if key in CREATIVE_OPERATIONS and row.evidence["owner"] != key:
            raise InvalidTransitionError("Continue logical checkpoint owner changed")
        selected[key] = row
        physical = [item for item in checkpoints if item.evidence["owner"] == key] if key in CREATIVE_OPERATIONS else [row]
        for item in physical:
            assert_retained_checkpoint_provenance(session.connection().connection.driver_connection,
                run.project_id, item.state, CheckpointEvidence.model_validate(item.evidence),
                run_id=run.id, operation_key=item.operation_key)
            covered.add(item.id)
    if (covered != {row.id for row in checkpoints}
            or {row.id for row in selected.values()} != {row.id for row in checkpoints if row.state == "adopted"}):
        raise InvalidTransitionError("Continue refuses extra or superseded logical installation checkpoints")
    return selected


def select_inherited_checkpoints(owner, session, run, checkpoints):
    adopted = [row for row in checkpoints if row.state == "adopted"]
    by_key = {row.operation_key: row for row in adopted}
    if "installation" not in by_key:
        return adopted
    installed, proposal, inputs, script, storyboard, mapping = owner.continuation_source_context(session, run.project_id)
    if by_key["installation"].evidence["result"].get("admissionId") != installed.admission_id:
        raise InvalidTransitionError("Continue installation checkpoint differs from current admission")
    expected = prepare_presentation(inputs=inputs, script=script, storyboard=storyboard, mapping=mapping)
    package = proposal.proposal["presentation"]
    try:
        retained = ProductionPresentation.model_validate(package)
        bind_presentation_spans(retained, [PresentationUpdate(id=source.id, spans=source.spans) for source in retained.sources])
    except ValueError as error:
        raise InvalidTransitionError("Continue presentation inventory or spans are malformed") from error
    if not retained.reviewed and retained.machine_adoption is None:
        raise InvalidTransitionError("Continue presentation lacks its retained adoption authority")
    if (package["frozenEvidence"] != expected.frozen_evidence or package["sourceHash"] != expected.source_hash
            or len(package["sources"]) != len(expected.sources)):
        raise InvalidTransitionError("Continue presentation source inventory is incomplete or changed")
    fields = set()
    for actual, source in zip(package["sources"], expected.sources, strict=True):
        wanted = source.model_dump(mode="json", by_alias=True)
        if source.kind == "composition":
            coordinates = source.coordinates
            episode = next(item for item in storyboard["episodes"] if item["ep"] == coordinates["episode"])
            cut = episode["segments"][coordinates["segmentIndex"] - 1]["cuts"][coordinates["cutIndex"] - 1]
            field = actual.get("coordinates", {}).get("field")
            if field not in {"frame", "composition"} or not isinstance(cut.get(field), str) or not cut[field].strip():
                raise InvalidTransitionError("Continue presentation has an unsupported composition source")
            fields.add(field)
            wanted["coordinates"] = coordinates | {"field": field}
            wanted["sourceText"] = cut[field]
        if {key: value for key, value in actual.items() if key != "spans"} != {
                key: value for key, value in wanted.items() if key != "spans"}:
            raise InvalidTransitionError("Continue presentation source identity, text or coordinates changed")
    if fields == {"composition"}:
        from .image_art_references import reusable_image_checkpoints
        return reusable_image_checkpoints(session, adopted)
    if fields != {"frame"}:
        raise InvalidTransitionError("Continue refuses mixed presentation sources or incomplete text installation")
    _assert_no_dependent_material(session, run.project_id)
    logical = _logical_installation(session, run, checkpoints)
    return [logical[key] for key in sorted(RAW_OPERATIONS)]
