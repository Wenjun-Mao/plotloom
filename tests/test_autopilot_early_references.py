"""Real owner scheduler and complete material gates, synthetic native receipts only."""
from contextlib import closing

import pytest

from tests.autopilot_controller_fixtures import environment


def current(storage, run):
    with closing(storage.projects.open(run.project_id)) as store:
        return store.repository.autopilot.current(run.project_id)


@pytest.mark.parametrize("stage", ["characters", "art"])
def test_discovery_uses_adopted_logical_owner_for_corrective_checkpoint(tmp_path, monkeypatch, stage):
    from plotloom import autopilot_early_references
    from plotloom.autopilot_early_references import discover_early_references
    # This consumer test uses validated adopted owner evidence; it varies only
    # the physical key in the read projection, never persists fabricated lineage.
    monkeypatch.setattr(autopilot_early_references, "advance_early_references", lambda *_args: None)
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    try:
        assert service.acquire_controller()
        for _ in range(24):
            service.step(run.project_id)
            view = current(storage, run)
            if any(c["operationKey"] == "art" and c["state"] == "adopted" for c in view.checkpoints):
                break
        else:
            raise AssertionError("fixture text prefix did not adopt Art")
        assert run.policy.early_reference_limit == 4
        checkpoints = [c | {"operationKey": f"{stage}:correction:1"} if c["operationKey"] == stage else c for c in view.checkpoints]
        with closing(storage.projects.open(run.project_id)) as store:
            discovery = discover_early_references(store, view.model_copy(update={"checkpoints": checkpoints}))
            assert discovery is not None and discovery.cast_revision >= 1 and discovery.art_revision >= 1
            assert any(subject.owner == "art-reference" for subject in discovery.subjects)
        assert not registry._codex_exec_test_host.image_calls
    finally:
        service.close()


def test_early_reference_delivery_precedes_installation_and_remains_candidate_only(tmp_path, monkeypatch):
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    host = registry._codex_exec_test_host
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(run.project_id)
            view = current(storage, run)
            early = [item for item in view.checkpoints if item["evidence"]["result"].get("earlyReference")]
            assert len(early) <= 4
            if any(item["state"] == "delivered" for item in early):
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("no early delivery")
        assert run.policy.early_reference_limit == 4
        assert not any(item["operationKey"] == "installation" for item in view.checkpoints)
        assert len(host.calls) < 8 and host.image_calls
        assert all(item["state"] != "adopted" for item in early)
        assert view.bundle is None and view.handoff is None
        assert not any(item["operationKey"] == "material.inventory" for item in view.checkpoints)
        with closing(storage.projects.open(run.project_id)) as store:
            assert store.media.list_character_reference_decisions(run.project_id)["decisions"] == []
    finally:
        service.close()


def test_pending_art_gallery_does_not_block_frames_with_current_canonical_character_references(tmp_path, monkeypatch):
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    host = registry._codex_exec_test_host
    status = host.status
    def hold_art(attempt_id):
        retained = host.statuses.get(str(attempt_id))
        if retained is not None and retained.attempt.operation_key.startswith("art-reference:"):
            return retained
        return status(attempt_id)
    monkeypatch.setattr(registry, "codex_exec_status", hold_art)
    try:
        assert service.acquire_controller()
        for _ in range(100):
            service.step(run.project_id)
            view = current(storage, run)
            if any(item["evidence"]["owner"] == "image" and item["state"] == "sent" for item in view.checkpoints):
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("own-character-ready frame blocked by unrelated Art gallery")
        art = [item for item in view.checkpoints if item["evidence"]["owner"] == "art-reference"]
        assert art and any(item["state"] != "adopted" for item in art)
        refs = [item for item in view.checkpoints if item["evidence"]["owner"] == "character-reference"]
        assert refs and all(item["state"] == "adopted" for item in refs)
        with closing(storage.projects.open(run.project_id)) as store:
            decisions = store.media.list_character_reference_decisions(run.project_id)["decisions"]
            assert decisions and all(item["characterContext"]["authority"] == "story_bible" for item in decisions)
            for checkpoint in refs:
                evidence = checkpoint["evidence"]
                context = store.media.character_reference_proposal_delivery_context(run.project_id, evidence["jobId"])
                assert context["requestHash"] == evidence["requestHash"]
                assert context["request"]["frozenSnapshot"]["characterContextHash"] != evidence["result"]["canonicalCharacterContextHash"]
                assert evidence["result"]["assetId"] in evidence["result"]["candidateAssetIds"]
        assert view.bundle is None
    finally:
        service.close()


@pytest.mark.parametrize("non_identity", [False, True], ids=["identity", "mapped-consumer"])
def test_complete_early_pack_reuses_original_jobs_and_budgets_once(tmp_path, monkeypatch, non_identity):
    from sqlalchemy import select

    from plotloom.autopilot_materials import initial_inventory
    from plotloom.persistence.schema import AutopilotExecAttemptRow
    if non_identity:
        from plotloom.cast_contracts import CastConsumerMapping
        from plotloom.persistence.project.cast import ProjectCastPersistence
        accept = ProjectCastPersistence.accept_candidate
        def accept_mapped(owner, project_id, request):
            # Supply the supported explicit map to the real owner BEFORE its
            # accepted revision or any exploratory job exists.
            mappings = [CastConsumerMapping(cast_character_id=item.cast_character_id,
                consumer_character_id=f"canonical_{item.cast_character_id}") for item in request.consumer_mappings]
            return accept(owner, project_id, request.model_copy(update={"consumer_mappings": mappings}))
        monkeypatch.setattr(ProjectCastPersistence, "accept_candidate", accept_mapped)
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    host = registry._codex_exec_test_host
    frozen_early_jobs = {}
    try:
        assert service.acquire_controller()
        for _ in range(400):
            service.step(run.project_id)
            view = current(storage, run)
            for item in view.checkpoints:
                if item["evidence"]["result"].get("earlyReference"):
                    prior = frozen_early_jobs.setdefault(item["operationKey"], item["evidence"]["jobId"])
                    assert prior == item["evidence"]["jobId"]
            if view.state == "awaiting_review":
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("bounded early pack did not complete")
        with closing(storage.projects.open(run.project_id)) as store:
            inventory = initial_inventory(store, view.policy)
            from copy import deepcopy

            from plotloom.autopilot_contracts import CheckpointEvidence
            from plotloom.persistence.project.autopilot_bindings import (
                assert_checkpoint_binding,
            )
            from plotloom.persistence.project.autopilot_inventory_validation import (
                assert_inventory_binding,
            )
            from plotloom.project_storage.material_bundle_validation import (
                assert_material_bundle,
            )
            historical_inventory = deepcopy(view.bundle["inventory"])
            historical_inventory["version"] = "pre-video.inventory.v1"
            for subject in historical_inventory["subjects"]:
                subject.pop("consumerCharacterId", None)
            with store.repository.engine.connect() as connection:
                sqlite = connection.connection.driver_connection
                # Historical evidence keeps its original shape. A current v8
                # run cannot choose that decoder to skip consumer binding.
                assert_inventory_binding(sqlite, run.project_id, historical_inventory, executor_contract="plotloom.codex-exec.v7")
                downgraded = deepcopy(view.bundle) | {"inventory": historical_inventory}
                with pytest.raises(ValueError, match="current CLI inventories"):
                    assert_material_bundle(sqlite, run.id, run.project_id, view.bundle["policyHash"], view.policy, downgraded)
                inventory_checkpoint = next(item for item in view.checkpoints if item["operationKey"] == "material.inventory")
                evidence = CheckpointEvidence.model_validate(inventory_checkpoint["evidence"])
                with pytest.raises(ValueError, match="current CLI inventories"):
                    assert_checkpoint_binding(sqlite, run.project_id, "adopted",
                        evidence.model_copy(update={"result": evidence.result | {"inventory": historical_inventory}}),
                        run_id=run.id, operation_key="material.inventory")
            if non_identity:
                for subject in inventory.subjects:
                    if subject.owner != "character-reference":
                        continue
                    assert subject.consumer_character_id == f"canonical_{subject.id}"
                    checkpoint = next(item for item in view.checkpoints if item["operationKey"] == subject.operation_key)
                    evidence = checkpoint["evidence"]
                    assert evidence["subjectId"] == subject.consumer_character_id
                    context = store.media.character_reference_proposal_delivery_context(run.project_id, evidence["jobId"])
                    assert context["requestHash"] == evidence["requestHash"]
                    assert context["request"]["frozenSnapshot"]["acceptedCast"]["castCharacterId"] == subject.id
                    assert context["request"]["frozenSnapshot"]["characterContext"]["characterId"] == subject.consumer_character_id
                    assert evidence["result"]["consumerCharacterId"] == subject.consumer_character_id
                    assert evidence["result"]["assetId"] in evidence["result"]["candidateAssetIds"]
                assert all(entry["characterId"].startswith("canonical_") for frame in view.frames for entry in frame.character_identity)
            with store.repository._read() as session:
                rows = session.scalars(select(AutopilotExecAttemptRow).where(AutopilotExecAttemptRow.run_id == run.id)).all()
                images = [item for item in rows if item.domain == "image"]
                assert len(images) == len(inventory.subjects)
                assert sum(item.reserved_image_outputs for item in images) == len(images)
                assert all(item.image_budget_state == "consumed" for item in images)
        assert frozen_early_jobs and len(frozen_early_jobs) <= 4
        assert len(host.image_calls) == len(set(host.image_calls)) == len(inventory.subjects)
        assert len(host.calls) == 8 and view.handoff is None
        assert view.bundle and len(view.frames) == sum(item.owner == "image" for item in inventory.subjects)
    finally:
        service.close()


def test_first_install_independence_refuses_manual_foreign_non_early_drift_and_replacement(tmp_path, monkeypatch):
    from copy import deepcopy

    from sqlalchemy import select

    from plotloom.autopilot_contracts import CommandAuthority, OperationScope
    from plotloom.domain import utc_now
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.persistence.codec import stable_hash
    from plotloom.persistence.project.first_install_references import (
        first_install_reference_is_independent,
    )
    from plotloom.persistence.project.media_identifiers import new_image_job_id
    from plotloom.persistence.project.production_rebuild_quiescence import (
        assert_production_quiescent,
    )
    from plotloom.persistence.schema import (
        ArtReferenceProposalRow,
        AutopilotCheckpointRow,
        ProjectRow,
    )
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    host = registry._codex_exec_test_host
    status = host.status
    def hold_art(attempt_id):
        retained = host.statuses.get(str(attempt_id))
        if retained is not None and retained.attempt.operation_key.startswith("art-reference:"):
            return retained
        return status(attempt_id)
    monkeypatch.setattr(registry, "codex_exec_status", hold_art)
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(run.project_id)
            view = current(storage, run)
            if any(item["operationKey"] == "bridge.prepare" for item in view.checkpoints):
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("first bridge preparation blocked")
        early_art = next(item for item in view.checkpoints if item["evidence"]["owner"] == "art-reference")
        job_id = early_art["evidence"]["jobId"]
        host_snapshot = deepcopy(host.statuses)
        with closing(storage.projects.open(run.project_id)) as store:
            access = store.repository._project_access
            with store.repository._read() as session:
                assert not first_install_reference_is_independent(access, session, run.project_id,
                    session.get(ArtReferenceProposalRow, job_id))
                with pytest.raises(InvalidTransitionError, match="active project work"):
                    assert_production_quiescent(access, session, run.project_id)
            authority = CommandAuthority(run.id, service.claim, OperationScope.INSTALL)
            with store.repository.autopilot_command(authority):
                with store.repository._read() as session:
                    assert_production_quiescent(access, session, run.project_id)
                    for fault in ("non-early", "foreign", "source-drift"):
                        with session.begin_nested() as savepoint:
                            if fault == "non-early":
                                checkpoint = session.scalar(select(AutopilotCheckpointRow).where(
                                    AutopilotCheckpointRow.run_id == run.id,
                                    AutopilotCheckpointRow.operation_key == early_art["operationKey"],
                                ))
                                payload = deepcopy(checkpoint.evidence)
                                payload["result"].pop("earlyReference")
                                checkpoint.evidence = payload
                            elif fault == "foreign":
                                original = session.get(ArtReferenceProposalRow, job_id)
                                foreign_id = new_image_job_id()
                                request = deepcopy(original.request) | {"jobId": foreign_id}
                                session.add(ArtReferenceProposalRow(id=foreign_id, project_id=run.project_id,
                                    subject_type=original.subject_type, subject_id=original.subject_id,
                                    request=request, request_hash=stable_hash(request), state="prepared", created_at=utc_now()))
                            else:
                                project = session.get(ProjectRow, run.project_id)
                                project.brief = project.brief | {"visual_direction": "changed saved source"}
                            session.flush()
                            with pytest.raises(InvalidTransitionError, match="unresolved publication"):
                                assert_production_quiescent(access, session, run.project_id)
                            savepoint.rollback()
                        session.expire_all()
                        assert_production_quiescent(access, session, run.project_id)
        for _ in range(20):
            service.step(run.project_id)
            view = current(storage, run)
            if any(item["operationKey"] == "installation" for item in view.checkpoints):
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("held independent reference blocked first installation")
        assert not any(item["evidence"]["owner"] == "image" for item in view.checkpoints)
        with closing(storage.projects.open(run.project_id)) as store:
            with store.repository.autopilot_command(authority):
                with store.repository._read() as session:
                    with pytest.raises(InvalidTransitionError, match="unresolved publication"):
                        assert_production_quiescent(store.repository._project_access, session, run.project_id)
        # Read-only installation checks never release, replace or settle the
        # uncertain external operation's original host reservation.
        assert host.statuses[str(early_art["evidence"]["executorAttemptId"])].attempt == host_snapshot[str(early_art["evidence"]["executorAttemptId"])].attempt
    finally:
        service.close()
