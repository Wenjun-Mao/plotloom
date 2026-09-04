from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from plotloom.domain import (
    CharacterV2,
    ContinuityStateV2,
    RequiredEntityState,
    StageName,
    StoryBibleV2,
)
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.fragment_semantics import continuity_sequence_repair_boundaries
from plotloom.generation.work_units import (
    BeatContent,
    ContinuityBoundaryRepair,
    ContinuityFactAssignment,
    ContinuitySequenceRepairFact,
    ContinuityStateEndpoint,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
    assert_continuity_repair_fact_matches_source,
    parse_semantic_repair_fact,
    semantic_repair_facts,
    serialize_semantic_repair_fact,
)


def _bible(*, hero: bool = True) -> StoryBibleV2:
    characters = []
    if hero:
        characters.append(
            CharacterV2(
                id="hero",
                name="Hero",
                description="A test character.",
                visual_anchors=[],
                sound_anchors=[],
                allowed_states=["alert", "calm"],
                continuity_rules=[],
                role="lead",
                goal="test",
                traits=[],
                voice_anchors=[],
            )
        )
    return StoryBibleV2(
        logline="Test logline.",
        premise="Test premise.",
        genre="",
        tone="",
        audience="",
        narrative_promise="",
        visual_language="",
        themes=[],
        world_rules=[],
        known_facts=[],
        open_questions=[],
        source_notes=[],
        characters=characters,
        locations=[],
        props=[],
    )


def _state(
    *,
    facts: dict | None = None,
    hero_state: str | None = None,
    screen_direction: str | None = None,
    lighting: str | None = None,
    sound: str | None = None,
    notes: list[str] | None = None,
) -> ContinuityStateV2:
    entities = [] if hero_state is None else [
        {"entityType": "character", "entityId": "hero", "state": hero_state}
    ]
    return ContinuityStateV2(
        facts=facts or {},
        entity_states=entities,
        screen_direction=screen_direction,
        lighting=lighting,
        sound=sound,
        notes=notes or [],
    )


def _beat(
    identifier: str,
    order: int,
    entry: ContinuityStateV2,
    exit: ContinuityStateV2,
) -> BeatContent:
    return BeatContent(
        local_beat_id=identifier,
        scene_local_id="scene-local",
        order=order,
        description="beat",
        purpose="test",
        visible_event="",
        immediate_result="",
        dramatic_change="",
        entry_state=entry,
        exit_state=exit,
        continuity_anchors=[],
        continuity_delta={},
    )


def _shot(
    identifier: str,
    order: int,
    entry: ContinuityStateV2,
    exit: ContinuityStateV2,
) -> ShotContent:
    return ShotContent(
        local_shot_id=identifier,
        order=order,
        title="shot",
        shot_size="medium",
        duration_units=1,
        camera_angle="",
        camera_movement="",
        composition="",
        visual_intent="",
        motion_intent="",
        action="",
        transition="",
        cue_ids=[],
        audio_plan={"events": []},
        character_ids=[],
        location_id=None,
        prop_ids=[],
        required_entity_states=[],
        entry_state=entry,
        exit_state=exit,
    )


def _scene_beats_payload(beats: list[BeatContent], entry: ContinuityStateV2, exit: ContinuityStateV2) -> dict:
    return SceneBeatsFragmentOutput(
        scenes=[
            DramaticSceneContent(
                local_scene_id="scene-local",
                order=1,
                title="scene",
                objective="test",
                location_id=None,
                character_ids=[],
                entry_state=entry,
                exit_state=exit,
            )
        ],
        beats=beats,
        dialogue_cues=[],
    ).model_dump(mode="json", by_alias=True)


def test_scene_continuity_fact_scans_every_boundary_and_round_trips() -> None:
    scene_entry = _state(
        facts={"nested": {"values": [1, None]}, "singleSource": "leave"},
        hero_state="alert",
        screen_direction="left",
        notes=["source note"],
    )
    beat_one_entry = _state(
        facts={"nested": {"values": [2, None]}, "targetOnly": True},
        hero_state="calm",
        screen_direction="right",
        notes=["target note"],
    )
    beat_one_exit = _state(facts={"torch": "lit"}, lighting="warm")
    beat_two_entry = _state(facts={"torch": "dark", "singleTarget": "leave"}, lighting="cold")
    beat_two_exit = _state(facts={"ending": None}, sound="wind")
    scene_exit = _state(facts={"ending": False}, sound="rain")
    payload = _scene_beats_payload(
        [
            _beat("beat-two", 2, beat_two_entry, beat_two_exit),
            _beat("beat-one", 1, beat_one_entry, beat_one_exit),
        ],
        scene_entry,
        scene_exit,
    )
    issues = (
        ValidationIssue(
            code="semantic.continuity_beat_sequence_mismatch",
            message="fixture",
            path=("scenes", 0),
        ),
    )

    facts = semantic_repair_facts(
        payload, issues, stage=StageName.SCENE_BEATS, bible=_bible()
    )

    assert len(facts) == 1
    fact = facts[0]
    assert isinstance(fact, ContinuitySequenceRepairFact)
    assert fact.path == ("scenes", 0)
    assert fact.ordered_item_ids == ("beat-one", "beat-two")
    assert [
        (boundary.source.kind, boundary.source.id, boundary.source.state,
         boundary.target.kind, boundary.target.id, boundary.target.state)
        for boundary in fact.boundaries
    ] == [
        ("scene", "scene-local", "entry", "beat", "beat-one", "entry"),
        ("beat", "beat-one", "exit", "beat", "beat-two", "entry"),
        ("beat", "beat-two", "exit", "scene", "scene-local", "exit"),
    ]
    assert [assignment.model_dump(mode="json", by_alias=True) for assignment in fact.boundaries[0].assignments] == [
        {"kind": "fact", "key": "nested", "expectedValue": {"values": [1, None]}},
        {
            "kind": "entity_state",
            "entityType": "character",
            "entityId": "hero",
            "expectedState": "alert",
        },
        {"kind": "scalar", "field": "screenDirection", "expectedValue": "left"},
    ]
    assert [assignment.model_dump(mode="json", by_alias=True) for assignment in fact.boundaries[1].assignments] == [
        {"kind": "fact", "key": "torch", "expectedValue": "lit"},
        {"kind": "scalar", "field": "lighting", "expectedValue": "warm"},
    ]
    assert [assignment.model_dump(mode="json", by_alias=True) for assignment in fact.boundaries[2].assignments] == [
        {"kind": "fact", "key": "ending", "expectedValue": None},
        {"kind": "scalar", "field": "sound", "expectedValue": "wind"},
    ]
    assert parse_semantic_repair_fact(serialize_semantic_repair_fact(fact)) == fact
    assert_continuity_repair_fact_matches_source(
        fact,
        payload,
        stage=StageName.SCENE_BEATS,
        bible=_bible(),
    )


def test_continuity_compiler_fails_closed_for_invalid_or_duplicate_states() -> None:
    invalid = _state(facts={"bad": float("nan")})
    valid = _state(facts={"bad": "safe"})
    assert continuity_sequence_repair_boundaries(
        invalid, [SimpleNamespace(entry_state=valid, exit_state=valid)], valid, bible=_bible()
    ) is None

    duplicate = ContinuityStateV2.model_construct(
        facts={},
        entity_states=[
            RequiredEntityState(entity_type="character", entity_id="hero", state="alert"),
            RequiredEntityState(entity_type="character", entity_id="hero", state="calm"),
        ],
        screen_direction=None,
        lighting=None,
        sound=None,
        notes=[],
    )
    assert continuity_sequence_repair_boundaries(
        duplicate, [SimpleNamespace(entry_state=valid, exit_state=valid)], valid, bible=_bible()
    ) is None

    payload = _scene_beats_payload(
        [_beat("beat-one", 1, _state(hero_state="calm"), _state())],
        _state(hero_state="alert"),
        _state(),
    )
    issues = (
        ValidationIssue(
            code="semantic.continuity_beat_sequence_mismatch",
            message="fixture",
            path=("scenes", 0),
        ),
    )
    assert semantic_repair_facts(
        payload, issues, stage=StageName.SCENE_BEATS, bible=_bible(hero=False)
    ) == ()


def test_storyboard_uses_frozen_scene_context_for_both_outer_boundaries() -> None:
    canonical_entry = _state(facts={"arrival": {"side": None}}, screen_direction="left")
    first_entry = _state(facts={"arrival": {"side": "right"}}, screen_direction="right")
    first_exit = _state(facts={"torch": "lit"})
    second_entry = _state(facts={"torch": "dark"})
    second_exit = _state(facts={"departure": "wrong"}, sound="rain")
    canonical_exit = _state(facts={"departure": "north"}, sound="wind")
    payload = StoryboardFragmentOutput(
        shots=[
            _shot("shot-two", 2, second_entry, second_exit),
            _shot("shot-one", 1, first_entry, first_exit),
        ],
        primary_shot_local_id_by_beat={"beat-a": "shot-one"},
    ).model_dump(mode="json", by_alias=True)
    issues = (
        ValidationIssue(
            code="semantic.continuity_shot_sequence_mismatch",
            message="fixture",
            path=("shots",),
        ),
    )

    facts = semantic_repair_facts(
        payload,
        issues,
        stage=StageName.STORYBOARD,
        bible=_bible(),
        scoped_context={
            "dramatic_scene": {
                "id": "scene-canonical",
                "entryState": canonical_entry.model_dump(mode="json", by_alias=True),
                "exitState": canonical_exit.model_dump(mode="json", by_alias=True),
            }
        },
    )

    assert len(facts) == 1
    fact = facts[0]
    assert isinstance(fact, ContinuitySequenceRepairFact)
    assert fact.path == ("shots",)
    assert fact.ordered_item_ids == ("shot-one", "shot-two")
    assert [
        (boundary.source.id, boundary.source.id_scope, boundary.source.state,
         boundary.target.id, boundary.target.id_scope, boundary.target.state)
        for boundary in fact.boundaries
    ] == [
        ("scene-canonical", "canonical_context", "entry", "shot-one", "response_local", "entry"),
        ("shot-one", "response_local", "exit", "shot-two", "response_local", "entry"),
        ("scene-canonical", "canonical_context", "exit", "shot-two", "response_local", "exit"),
    ]
    assert [assignment.expected_value for assignment in fact.boundaries[-1].assignments] == ["north", "wind"]


def test_persisted_continuity_fact_rejects_non_adjacent_or_foreign_boundary() -> None:
    owner = ContinuityStateEndpoint(
        kind="scene",
        id="scene-local",
        id_scope="response_local",
        state="entry",
    )
    foreign_boundary = ContinuityBoundaryRepair(
        source=ContinuityStateEndpoint(
            kind="beat",
            id="beat-foreign",
            id_scope="response_local",
            state="entry",
        ),
        target=ContinuityStateEndpoint(
            kind="beat",
            id="beat-foreign",
            id_scope="response_local",
            state="exit",
        ),
        assignments=(
            ContinuityFactAssignment(kind="fact", key="x", expected_value="forced"),
        ),
    )

    with pytest.raises(ValidationError, match="not adjacent"):
        ContinuitySequenceRepairFact(
            code="semantic.continuity_beat_sequence_mismatch",
            path=("scenes", 0),
            sequence_kind="beat",
            owner=owner,
            ordered_item_ids=("beat-one",),
            boundaries=(foreign_boundary,),
        )


@pytest.mark.parametrize("tamper_mode", ["owner", "order"])
def test_persisted_continuity_fact_must_bind_to_rejected_response(
    tamper_mode: str,
) -> None:
    scene_entry = _state(facts={"place": "bridge"}, sound="quiet")
    first_entry = _state(facts={"place": "engine"}, sound="alarm")
    first_exit = _state(facts={"power": "on"})
    second_entry = _state(facts={"power": "off"})
    second_exit = _state()
    scene_exit = _state()
    payload = _scene_beats_payload(
        [
            _beat("beat-one", 1, first_entry, first_exit),
            _beat("beat-two", 2, second_entry, second_exit),
        ],
        scene_entry,
        scene_exit,
    )
    issue = ValidationIssue(
        code="semantic.continuity_beat_sequence_mismatch",
        message="fixture",
        path=("scenes", 0),
    )
    [original] = semantic_repair_facts(
        payload,
        (issue,),
        stage=StageName.SCENE_BEATS,
        bible=_bible(),
    )
    assert isinstance(original, ContinuitySequenceRepairFact)

    if tamper_mode == "owner":
        serialized = serialize_semantic_repair_fact(original)
        serialized["owner"]["id"] = "unbound-scene"
        for boundary in serialized["boundaries"]:
            for endpoint_name in ("source", "target"):
                endpoint = boundary[endpoint_name]
                if endpoint["kind"] == "scene":
                    endpoint["id"] = "unbound-scene"
        tampered = parse_semantic_repair_fact(serialized)
    else:
        tampered = ContinuitySequenceRepairFact(
            code="semantic.continuity_beat_sequence_mismatch",
            path=("scenes", 0),
            sequence_kind="beat",
            owner=original.owner,
            ordered_item_ids=("beat-two", "beat-one"),
            boundaries=(
                ContinuityBoundaryRepair(
                    source=ContinuityStateEndpoint(
                        kind="beat",
                        id="beat-two",
                        id_scope="response_local",
                        state="exit",
                    ),
                    target=ContinuityStateEndpoint(
                        kind="beat",
                        id="beat-one",
                        id_scope="response_local",
                        state="entry",
                    ),
                    assignments=(
                        ContinuityFactAssignment(
                            kind="fact",
                            key="power",
                            expected_value="off",
                        ),
                    ),
                ),
            ),
        )

    with pytest.raises(ValueError, match="does not match the rejected response"):
        assert_continuity_repair_fact_matches_source(
            tampered,
            payload,
            stage=StageName.SCENE_BEATS,
            bible=_bible(),
        )
