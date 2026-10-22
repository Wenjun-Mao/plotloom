"""Dependency-effect rebinding and transactional validation contracts."""

from contextlib import closing
from copy import deepcopy

import pytest
from sqlalchemy import select

from plotloom.domain import StageName
from plotloom.persistence.schema.project_source_outline import SourceGraphIdentityRow
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from tests.production_rebuild_fixtures import (
    _accept,
    _effects_store,
    _heads,
    _review,
)


@pytest.mark.parametrize("late_failure", [False, True])
def test_dependency_only_rebind_preserves_f2_f5_receipts_and_rolls_back_atomically(
    tmp_path, monkeypatch, late_failure
):
    store, proposal = _effects_store(tmp_path)
    with closing(store):
        original_installation = _accept(store, proposal).installation
        prepared = store.prepare_production_bridge(
            store.production_bridge_state().preparation.request
        )
        proposal = _review(store, prepared.proposal)
        before_reviews = [
            reader().model_dump(mode="json")
            for reader in (
                store.cast_state,
                store.art_state,
                store.script_state,
                store.storyboard_review_state,
            )
        ]
        before_heads = _heads(store)
        with store.repository._read() as session:
            identities_before = len(
                session.scalars(select(SourceGraphIdentityRow)).all()
            )
        if late_failure:
            canonical = store.repository.production_bridge._canonical
            install = canonical._install_stage_in_session

            def reject_board(*args, **kwargs):
                if args[2] == StageName.STORYBOARD:
                    raise RuntimeError("dependency bundle late failure")
                return install(*args, **kwargs)

            monkeypatch.setattr(canonical, "_install_stage_in_session", reject_board)
            with pytest.raises(RuntimeError, match="late failure"):
                _accept(store, proposal)
            assert _heads(store) == before_heads
            assert store.production_bridge_state().installation == original_installation
        else:
            accepted = _accept(store, proposal)
            assert accepted.installation.status == "current"
            assert accepted.installation.installed_stage_revisions["story_graph"] == 3
            assert store.cast_state().accepted_cast.binding.graph_revision == 1
        assert [
            reader().model_dump(mode="json")
            for reader in (
                store.cast_state,
                store.art_state,
                store.script_state,
                store.storyboard_review_state,
            )
        ] == before_reviews
        with store.repository._read() as session:
            assert len(
                session.scalars(select(SourceGraphIdentityRow)).all()
            ) == identities_before + (0 if late_failure else 1)


def test_incompatible_proposed_bible_effects_refuse_without_any_bundle_writes(tmp_path):
    store, proposal = _effects_store(tmp_path)
    with closing(store):
        # Inject a source-owned proposed Bible change as a new exact proposal
        # fixture; acceptance must revalidate entity effects transactionally.
        from plotloom.persistence.schema import ProductionBridgeRevisionRow

        with store.repository._lifecycle_write() as session:
            row = session.scalar(
                select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == store.manifest.project_id,
                    ProductionBridgeRevisionRow.revision == proposal.revision,
                )
            )
            payload = deepcopy(row.proposal)
            payload["payload"]["bible"]["locations"][0]["allowedStates"] = ["night"]
            row.proposal = payload
            row.content_hash = store.repository.production_bridge._proposal_digest(
                row.inputs, payload, []
            )
            digest = row.content_hash
        before = _heads(store)
        with store.repository._read() as session:
            conflicts = store.repository.production_bridge._validate_payload(
                session, store.manifest.project_id, payload["payload"]
            )
            assert len(conflicts) == 1
            assert conflicts[0].code == "canonical_validation"
        assert _heads(store) == before
        with pytest.raises(ValueError):
            store.accept_production_bridge(
                ProductionBridgeAcceptRequest(
                    expected_proposal_revision=proposal.revision,
                    expected_content_hash=digest,
                )
            )
        assert _heads(store) == before
        assert store.production_bridge_state().installation is None
        saved = store.update_production_bridge_intent_package(
            ProductionBridgeIntentUpdateRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=digest,
                entries=[
                    {"id": entry.id, "text": entry.text}
                    for entry in proposal.intent_package.entries
                ],
            )
        ).proposal
        assert not saved.installable
        assert any(item.code == "canonical_validation" for item in saved.conflicts)
        assert _heads(store) == before
