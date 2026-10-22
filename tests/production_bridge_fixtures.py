"""Reusable source-shaped setup for production bridge tests."""

from __future__ import annotations

from plotloom.production_bridge_contracts import (
    ProductionBridgeIntentUpdateRequest,
    ProductionBridgeProposal,
)
from plotloom.project_storage.project_handle import ProjectStore
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage


def _source_shaped_review_board(
    seconds: float = 3, episodes=(1, 2, 3)
) -> dict[str, object]:
    """Pass the pinned upstream validator; no review-validation bypass is used."""

    def segment(
        ep: int, segment_index: int, beat_ranges: list[list[int]]
    ) -> dict[str, object]:
        cuts = [
            {
                "seconds": seconds,
                "beats": beat_range,
                "size": "medium",
                "camera": "Static Shot",
                "characters": [],
                "props": [],
                "frame": "medium shot of an empty beacon room at dawn, cinematic film still, cool gray palette, 16:9",
            }
            for beat_range in beat_ranges
        ]
        starts = [index * seconds for index in range(len(cuts))]
        align = (
            "; ".join(
                f"Picture {index} (from Shot {index}) aligns with the {start:.2f}-second mark of the target video"
                for index, start in enumerate(starts, 1)
            )
            + "."
        )
        shots = "\n".join(
            f"[Shot {index}] Cinematic, live-action, cool gray palette. The empty beacon room of <Picture {index}> holds while the camera uses a static shot."
            if index == 1
            else f"[Shot {index}] At 00:{starts[index - 1]:06.3f}, the camera cuts to <Picture {index}> and holds a static shot in the empty beacon room."
            for index in range(1, len(cuts) + 1)
        )
        return {
            "id": f"E{ep:02}-{segment_index:02}",
            "sceneIndex": 1,
            "cuts": cuts,
            "h3Prompt": f"How the reference pictures align with the target video — {align}\n\nintegrated_multimodal_description:\n{shots}\n\noverall_soundscape: Quiet wind around an empty beacon room.\n\nnon_diegetic_music: N/A",
        }

    return {
        "source": "Tide Light",
        "params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15},
        "episodes": [
            {
                "ep": ep,
                "segments": [
                    segment(ep, 1, [[1, 1], [2, 2], [3, 3], [4, 4]]),
                    segment(ep, 2, [[5, 5], [6, 6], [7, 7], [8, 8], [9, 10]]),
                ],
            }
            for ep in episodes
        ],
    }


def _review_fixture_presentation(store, proposal):
    from plotloom.production_presentation import ProductionPresentationUpdateRequest

    package = proposal.presentation
    assert package is not None
    return store.update_production_bridge_presentation(
        ProductionPresentationUpdateRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
            source_hash=package.source_hash,
            reviewed_complete=True,
            entries=[
                {
                    "id": source.id,
                    "spans": [
                        {
                            "start": 0,
                            "end": len(source.source_text),
                            "role": "dialogue"
                            if source.kind == "dialogue"
                            else "physical",
                            "rendering": ""
                            if source.kind == "dialogue"
                            else source.source_text,
                        }
                    ],
                }
                for source in package.sources
            ],
        )
    ).proposal


def _prepare_installable_bridge(
    store: ProjectStore, seconds: float = 3, structure_factory=None
) -> ProductionBridgeProposal:
    _accepted_f4_script(store, structure_factory)
    candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
    ready = store.admit_storyboard_review_delivery(
        _deliver_stage(
            store,
            request,
            "storyboard.json",
            _source_shaped_review_board(
                seconds, [item.episode for item in candidate.binding.section_bindings]
            ),
            "bridge-fixture",
        )
    )
    store.accept_storyboard_review_candidate(
        StoryboardReviewAcceptRequest(
            job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding
        )
    )
    proposal = store.prepare_production_bridge(
        store.production_bridge_state().preparation.request
    ).proposal
    assert proposal and not proposal.installable
    assert proposal.intent_package.review_state == "pending"
    assert proposal.intent_package.suggestion_origin == "none"
    assert all(not entry.text for entry in proposal.intent_package.entries)
    assert all(
        entry.source_excerpt and entry.suggested_text is None
        for entry in proposal.intent_package.entries
    )
    proposal = _review_fixture_presentation(store, proposal)
    authored = [
        {"id": entry.id, "text": f"作者明确的戏剧目的：{entry.id}"}
        for entry in proposal.intent_package.entries
    ]
    ready = store.update_production_bridge_intent_package(
        ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash,
            entries=authored,
        )
    ).proposal
    assert ready and ready.installable, ready.conflicts if ready else None
    return ready
