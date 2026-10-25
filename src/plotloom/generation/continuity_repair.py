"""Derive and revalidate source-owned continuity sequence repairs."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import (
    ValidationError,
)

from ..domain import (
    StageName,
    StoryBibleV2,
)
from .continuity_repair_contracts import (
    ContinuityBoundaryRepair,
    ContinuityEntityStateAssignment,
    ContinuityFactAssignment,
    ContinuityRepairAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    ContinuityStateEndpoint,
)
from .contracts import ValidationIssue
from .fragment_semantics import (
    FragmentSemanticContextError,
    continuity_sequence_repair_boundaries,
    continuity_state_from_context,
)
from .repair_facts import SemanticRepairFact
from .scene_response_contracts import (
    BeatContent,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
)
from .storyboard_response_contracts import (
    ShotContent,
    StoryboardFragmentOutput,
)


def continuity_sequence_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
    scoped_context: Mapping[str, Any] | None = None,
) -> tuple[ContinuitySequenceRepairFact, ...]:
    """Compile exact left-to-right continuity repairs for one fragment response.

    This compiler deliberately accepts only schema-valid fragments and a
    valid Story Bible.  It never repairs a one-sided declaration, notes, or a
    malformed state; those cases lack an exact, safe ownership authority.
    """

    if bible is None:
        return ()
    if stage == StageName.SCENE_BEATS:
        relevant = tuple(
            issue
            for issue in issues
            if issue.code == "semantic.continuity_beat_sequence_mismatch"
        )
        if not relevant:
            return ()
        try:
            output = SceneBeatsFragmentOutput.model_validate(
                value, by_alias=True, by_name=False
            )
        except ValidationError:
            return ()
        scene_ids = [scene.local_scene_id for scene in output.scenes]
        beat_ids = [beat.local_beat_id for beat in output.beats]
        if len(scene_ids) != len(set(scene_ids)) or len(beat_ids) != len(set(beat_ids)):
            return ()
        facts: list[ContinuitySequenceRepairFact] = []
        for issue in relevant:
            path = issue.path
            if (
                len(path) != 2
                or path[0] != "scenes"
                or not isinstance(path[1], int)
                or isinstance(path[1], bool)
                or path[1] < 0
                or path[1] >= len(output.scenes)
            ):
                continue
            scene = output.scenes[path[1]]
            ordered = sorted(
                (
                    beat
                    for beat in output.beats
                    if beat.scene_local_id == scene.local_scene_id
                ),
                key=lambda beat: beat.order,
            )
            if (
                not ordered
                or any(
                    beat.scene_local_id not in set(scene_ids) for beat in output.beats
                )
                or [beat.order for beat in ordered] != list(range(1, len(ordered) + 1))
            ):
                continue
            differences = continuity_sequence_repair_boundaries(
                scene.entry_state,
                ordered,
                scene.exit_state,
                bible=bible,
            )
            if not differences:
                continue
            boundaries: list[ContinuityBoundaryRepair] = []
            for difference in differences:
                source, target = _scene_beats_continuity_boundary_endpoints(
                    scene,
                    ordered,
                    difference.boundary_index,
                )
                assignments = tuple(
                    _continuity_assignment_from_candidate(candidate)
                    for candidate in difference.assignments
                )
                boundaries.append(
                    ContinuityBoundaryRepair(
                        source=source,
                        target=target,
                        assignments=assignments,
                    )
                )
            facts.append(
                ContinuitySequenceRepairFact(
                    code=issue.code,
                    path=path,
                    sequence_kind="beat",
                    owner=ContinuityStateEndpoint(
                        kind="scene",
                        id=scene.local_scene_id,
                        id_scope="response_local",
                        state="entry",
                    ),
                    ordered_item_ids=tuple(beat.local_beat_id for beat in ordered),
                    boundaries=tuple(boundaries),
                )
            )
        return tuple(facts)

    if stage != StageName.STORYBOARD:
        return ()
    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.continuity_shot_sequence_mismatch"
        and issue.path == ("shots",)
    )
    if not relevant or scoped_context is None:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(
            value, by_alias=True, by_name=False
        )
        scene = scoped_context.get("dramatic_scene")
        if not isinstance(scene, Mapping):
            return ()
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            return ()
        scene_entry = continuity_state_from_context(scene, "entryState")
        scene_exit = continuity_state_from_context(scene, "exitState")
    except (ValidationError, FragmentSemanticContextError):
        return ()
    shot_ids = [shot.local_shot_id for shot in output.shots]
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if (
        len(shot_ids) != len(set(shot_ids))
        or not ordered
        or [shot.order for shot in ordered] != list(range(1, len(ordered) + 1))
    ):
        return ()
    differences = continuity_sequence_repair_boundaries(
        scene_entry,
        ordered,
        scene_exit,
        bible=bible,
        final_boundary_source="sequence_exit",
    )
    if not differences:
        return ()
    boundaries = []
    for difference in differences:
        source, target = _storyboard_continuity_boundary_endpoints(
            scene_id,
            ordered,
            difference.boundary_index,
        )
        boundaries.append(
            ContinuityBoundaryRepair(
                source=source,
                target=target,
                assignments=tuple(
                    _continuity_assignment_from_candidate(candidate)
                    for candidate in difference.assignments
                ),
            )
        )
    return tuple(
        ContinuitySequenceRepairFact(
            code=issue.code,
            path=issue.path,
            sequence_kind="shot",
            owner=ContinuityStateEndpoint(
                kind="scene",
                id=scene_id,
                id_scope="canonical_context",
                state="entry",
            ),
            ordered_item_ids=tuple(shot.local_shot_id for shot in ordered),
            boundaries=tuple(boundaries),
        )
        for issue in relevant
    )


def _continuity_assignment_from_candidate(candidate: Any) -> ContinuityRepairAssignment:
    if candidate.kind == "fact":
        assert candidate.fact_key is not None
        return ContinuityFactAssignment(
            kind="fact",
            key=candidate.fact_key,
            expected_value=candidate.expected_value,
        )
    if candidate.kind == "entity_state":
        assert candidate.entity_type is not None and candidate.entity_id is not None
        return ContinuityEntityStateAssignment(
            kind="entity_state",
            entity_type=candidate.entity_type,
            entity_id=candidate.entity_id,
            expected_state=candidate.expected_value,
        )
    assert candidate.scalar_field is not None
    return ContinuityScalarAssignment(
        kind="scalar",
        field={
            "screen_direction": "screenDirection",
            "lighting": "lighting",
            "sound": "sound",
        }[candidate.scalar_field],
        expected_value=candidate.expected_value,
    )


def _scene_beats_continuity_boundary_endpoints(
    scene: DramaticSceneContent,
    ordered: list[BeatContent],
    boundary_index: int,
) -> tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]:
    scene_entry = ContinuityStateEndpoint(
        kind="scene", id=scene.local_scene_id, id_scope="response_local", state="entry"
    )
    scene_exit = ContinuityStateEndpoint(
        kind="scene", id=scene.local_scene_id, id_scope="response_local", state="exit"
    )
    if boundary_index == 0:
        return scene_entry, ContinuityStateEndpoint(
            kind="beat",
            id=ordered[0].local_beat_id,
            id_scope="response_local",
            state="entry",
        )
    if boundary_index == len(ordered):
        return ContinuityStateEndpoint(
            kind="beat",
            id=ordered[-1].local_beat_id,
            id_scope="response_local",
            state="exit",
        ), scene_exit
    return ContinuityStateEndpoint(
        kind="beat",
        id=ordered[boundary_index - 1].local_beat_id,
        id_scope="response_local",
        state="exit",
    ), ContinuityStateEndpoint(
        kind="beat",
        id=ordered[boundary_index].local_beat_id,
        id_scope="response_local",
        state="entry",
    )


def _storyboard_continuity_boundary_endpoints(
    scene_id: str,
    ordered: list[ShotContent],
    boundary_index: int,
) -> tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]:
    scene_entry = ContinuityStateEndpoint(
        kind="scene", id=scene_id, id_scope="canonical_context", state="entry"
    )
    scene_exit = ContinuityStateEndpoint(
        kind="scene", id=scene_id, id_scope="canonical_context", state="exit"
    )
    if boundary_index == 0:
        return scene_entry, ContinuityStateEndpoint(
            kind="shot",
            id=ordered[0].local_shot_id,
            id_scope="response_local",
            state="entry",
        )
    if boundary_index == len(ordered):
        return scene_exit, ContinuityStateEndpoint(
            kind="shot",
            id=ordered[-1].local_shot_id,
            id_scope="response_local",
            state="exit",
        )
    return ContinuityStateEndpoint(
        kind="shot",
        id=ordered[boundary_index - 1].local_shot_id,
        id_scope="response_local",
        state="exit",
    ), ContinuityStateEndpoint(
        kind="shot",
        id=ordered[boundary_index].local_shot_id,
        id_scope="response_local",
        state="entry",
    )


def assert_continuity_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
    scoped_context: Mapping[str, Any] | None = None,
) -> None:
    """Bind executable continuity authority back to the rejected response.

    Internal endpoint adjacency is necessary but insufficient: a persisted
    fact could otherwise name a different owner or reorder response-local
    items while remaining self-consistent.  Recompiling the one exact fact
    from the source value and frozen context proves that its owner, IDs,
    sequence order, boundaries, and assignments all came from the response
    that was actually rejected.
    """

    if not isinstance(fact, ContinuitySequenceRepairFact):
        return
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = continuity_sequence_repair_facts(
        source_value,
        (source_issue,),
        stage=stage,
        bible=bible,
        scoped_context=scoped_context,
    )
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError(
            "continuity repair fact does not match the rejected response and frozen context"
        )
