"""Production rebuild preconditions, identity, and request-shape guards."""

from contextlib import closing
from copy import deepcopy

import pytest
from sqlalchemy import select

from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.production_rebuild_fixtures import _accept, _heads, _review, _store


@pytest.mark.parametrize(
    "job_state",
    ["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"],
)
def test_direct_video_job_blocks_preparation_and_acceptance_without_clearing_it(
    tmp_path, job_state
):
    from plotloom.domain import utc_now
    from plotloom.persistence.schema import VideoJobRow

    _, store = _store(tmp_path)
    with closing(store):
        proposal = _prepare_installable_bridge(store)
        request = store.production_bridge_state().preparation.request
        with store.repository._lifecycle_write() as session:
            session.add(
                VideoJobRow(
                    id="held-video",
                    project_id=store.manifest.project_id,
                    idempotency_key="held",
                    request_hash="a" * 64,
                    snapshot={},
                    snapshot_hash="b" * 64,
                    requested_seconds=5,
                    state=job_state,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        before = _heads(store)
        with pytest.raises(InvalidTransitionError, match="unresolved"):
            store.prepare_production_bridge(request)
        assert store.production_bridge_state().preparation.status == "unavailable"
        with pytest.raises(InvalidTransitionError, match="unresolved"):
            _accept(store, proposal)
        assert _heads(store) == before
        with store.repository._read() as session:
            assert session.get(VideoJobRow, "held-video").state == job_state


def test_latest_only_timing_refuses_removed_and_reused_ids_and_retains_installation_during_prepare(
    tmp_path,
):
    from plotloom.persistence.project.media_video_source import VideoSourceTiming
    from plotloom.persistence.schema import ProductionBridgeRevisionRow

    _, store = _store(tmp_path)
    with closing(store):
        original = _accept(store, _prepare_installable_bridge(store))
        bridge = store.repository.production_bridge
        timing = VideoSourceTiming(bridge._access, bridge)
        cut = original.installation.cuts[0]
        shot_id = cut["shotId"]
        with store.repository._read() as session:
            first = timing.binding_in_session(
                session, store.manifest.project_id, shot_id, 3000
            )
        fresh = store.prepare_production_bridge(original.preparation.request)
        with store.repository._read() as session:
            assert (
                timing.binding_in_session(
                    session, store.manifest.project_id, shot_id, 3000
                )
                == first
            )
        reviewed = _review(store, fresh.proposal)
        _accept(store, reviewed)
        with store.repository._read() as session:
            reused = timing.binding_in_session(
                session, store.manifest.project_id, shot_id, 3000
            )
            assert reused["admissionId"] != first["admissionId"]
            assert not timing.binding_is_current(
                session, store.manifest.project_id, shot_id, 3000, first
            )
        # Remove membership from the latest installed fixture, retaining the
        # historical admission and canonical shot; no historical/canonical
        # timing recovery is permitted even for the identical shot ID.
        with store.repository._lifecycle_write() as session:
            row = session.scalar(
                select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == store.manifest.project_id,
                    ProductionBridgeRevisionRow.revision == reviewed.revision,
                )
            )
            payload = deepcopy(row.proposal)
            payload["cuts"] = [
                item for item in payload["cuts"] if item["shotId"] != shot_id
            ]
            row.proposal = payload
        with (
            store.repository._read() as session,
            pytest.raises(InvalidTransitionError, match="not a member"),
        ):
            timing.binding_in_session(session, store.manifest.project_id, shot_id, 3000)


def test_projection_refuses_ambiguous_converging_typed_entry_states(
    tmp_path, monkeypatch
):
    from plotloom.canonical_schema import StoryGraphV2
    from plotloom.edge_entry_states import EdgeEntryStateContractError

    _, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        bridge = store.repository.production_bridge
        with store.repository._read() as session:
            inputs, board, script, cast_art = bridge._context(
                session, store.manifest.project_id
            )
            data = bridge._canonical._load_stage_payload(
                session, store.manifest.project_id, StageName.STORY_GRAPH
            ).model_dump(mode="json", by_alias=True)
            edges = [edge for edge in data["edges"] if edge["sourceNodeId"] == "choose"]
            for edge, state in zip(edges, ("dawn", "night")):
                edge["targetNodeId"] = "ending-a"
                edge["entityStateEffects"] = [
                    {"entityType": "location", "entityId": "S01", "state": state}
                ]
            monkeypatch.setattr(
                bridge._canonical,
                "_load_stage_payload",
                lambda *_: StoryGraphV2.model_validate(data),
            )
            with pytest.raises(EdgeEntryStateContractError, match="conflicting"):
                bridge._build(
                    session,
                    store.manifest.project_id,
                    inputs=inputs,
                    storyboard=board,
                    script=script,
                    cast_and_art=cast_art,
                )


def test_prepare_api_requires_exact_typed_body_and_stale_body_performs_no_writes(
    tmp_path,
):
    from fastapi.testclient import TestClient

    from plotloom.api import create_project_folder_authoring_app

    storage, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        project_id = store.manifest.project_id
        request = store.production_bridge_state().preparation.request.model_dump(
            mode="json", by_alias=True
        )
    client = TestClient(create_project_folder_authoring_app(storage))
    url = f"/api/v2/projects/{project_id}/production-bridge/proposals"
    assert client.post(url).status_code == 422
    assert client.post(url, json={}).status_code == 422
    valid = client.post(url, json=request)
    assert valid.status_code == 200, valid.text
    before = client.get(url.removesuffix("/proposals")).json()
    stale = client.post(url, json=request)
    assert stale.status_code == 409, stale.text
    assert client.get(url.removesuffix("/proposals")).json() == before
