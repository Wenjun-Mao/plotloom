"""Fake provider and isolated bridge-intent setup for tests."""

from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
from threading import Event
from typing import Any

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse
from plotloom.generation.exceptions import (
    ProviderOutcomeUnknownError,
    ProviderRequestNotSentError,
)
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.provider_profiles import (
    StageMaxOutputTokens,
    TextProviderProfileSnapshotV3,
)
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
from tests.production_bridge_fixtures import (
    _review_fixture_presentation,
    _source_shaped_review_board,
)


def _profile(auth_mode: str = "none") -> dict[str, Any]:
    return TextProviderProfileSnapshotV3(
        profile_id="fake",
        profile_version=1,
        text_provider="deterministic-fake",
        text_base_url="http://localhost:18888",
        text_model="fake-intent",
        text_auth_mode=auth_mode,
        text_context_window_tokens=32768,
        text_max_output_tokens=8192,
        text_attempt_timeout_seconds=5,
        stage_max_output_tokens=StageMaxOutputTokens(
            story_bible=4096,
            story_graph=4096,
            scene_beats=4096,
            storyboard=4096,
        ),
    ).model_dump(mode="json", by_alias=True)


def _pending_project(tmp_path: Path) -> tuple[ProjectFolderStorage, str, int, str]:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
        ready = store.admit_storyboard_review_delivery(
            _deliver_stage(
                store,
                request,
                "storyboard.json",
                _source_shaped_review_board(),
                "bridge-intent-fixture",
            )
        )
        store.accept_storyboard_review_candidate(
            StoryboardReviewAcceptRequest(
                job_id=candidate.job_id,
                expected_review_revision=0,
                binding=ready.binding,
            )
        )
        proposal = store.prepare_production_bridge(
            store.production_bridge_state().preparation.request
        ).proposal
        assert proposal and not proposal.installable
        proposal = _review_fixture_presentation(store, proposal)
        return (
            storage,
            store.manifest.project_id,
            proposal.revision,
            proposal.content_hash,
        )


class FakeAdapter:
    name = "deterministic-fake"
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(
        self, mode: str = "success", *, held: bool = False, expect_secret: bool = False
    ) -> None:
        self.mode = mode
        self.expect_secret = expect_secret
        self.started = Event()
        self.release = Event()
        if not held:
            self.release.set()
        self.calls = 0

    def generate(self, request: Any, secret: Any) -> ProviderResponse:
        self.calls += 1
        self.started.set()
        assert self.release.wait(8)
        assert (secret is not None) == self.expect_secret
        if self.mode == "unknown":
            raise ProviderOutcomeUnknownError("transport lost after dispatch")
        if self.mode == "not_sent":
            raise ProviderRequestNotSentError("request rejected before transport")
        ids = request.response_schema["properties"]["entries"]["items"]["properties"][
            "id"
        ]["enum"]
        entries = [
            {"id": target, "suggestedText": f"角色在此推动冲突并改变局势：{target}"}
            for target in ids
        ]
        if self.mode == "duplicate":
            entries[-1]["id"] = entries[0]["id"]
        raw = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({"entries": entries}, ensure_ascii=False),
                    }
                }
            ]
        }
        return ProviderResponse(
            provider=self.name, model=request.model, raw=raw, request_id="fake-request"
        )


class FakeResolver:
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter

    def resolve(self, _snapshot: Any) -> tuple[FakeAdapter, str]:
        return self.adapter, "fake-intent"


def _wait_for_job(
    service: ProductionBridgeIntentService, adapter: FakeAdapter, job_id: str
) -> None:
    assert adapter.started.wait(8)
    future = service._active.get(job_id)
    adapter.release.set()
    if future is not None:
        future.result(timeout=15)
