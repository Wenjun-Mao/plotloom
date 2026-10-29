"""Synthetic old source representation; real current owners and immutable rows."""
from contextlib import closing, nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.persistence.project.autopilot_continuation_selection import select_inherited_checkpoints
from plotloom.persistence.schema import AutopilotCheckpointRow
from plotloom.production_presentation import prepare_presentation
from sqlalchemy import select
from tests.autopilot_controller_fixtures import environment, run_text
from tests.test_autopilot_continuation import origin_rows, request_for


def frame_bound_fixture(**kwargs):
    """Author a disposable historical representation before any job is frozen."""
    package = prepare_presentation(**kwargs)
    sources = []
    for source in package.sources:
        if source.kind == "composition":
            coords = source.coordinates
            episode = next(item for item in kwargs["storyboard"]["episodes"] if item["ep"] == coords["episode"])
            cut = episode["segments"][coords["segmentIndex"] - 1]["cuts"][coords["cutIndex"] - 1]
            source = source.model_copy(update={"coordinates": coords | {"field": "frame"}, "source_text": cut["frame"]})
        sources.append(source)
    return package.model_copy(update={"sources": sources})


def installed(tmp_path, monkeypatch, *, frame_bound, corrected_cast=False):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    with monkeypatch.context() as frozen_fixture:
        if frame_bound:
            frozen_fixture.setattr("plotloom.persistence.project.production_bridge.prepare_presentation", frame_bound_fixture)
        if corrected_cast:
            from tests.content_language_fixtures import result_for
            rejected = False

            def reject_original_cast(request):
                nonlocal rejected
                if request.stage == "characters" and not rejected:
                    rejected = True
                    return result_for(request, rejected_path="$.summary")
                return result_for(request)

            frozen_fixture.setattr("tests.content_language_fixtures.result_for", reject_original_cast)
        current = run_text(service, view)
    return storage, registry, service, current, calls


@pytest.mark.parametrize("frame_bound", [False, True])
def test_preview_write_share_exact_selection_and_rebuild_only_bridge(tmp_path, monkeypatch, frame_bound):
    storage, registry, service, current, calls = installed(tmp_path, monkeypatch, frame_bound=frame_bound)
    try:
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            before = origin_rows(store, current.id)
            preview = store.repository.autopilot.continuation_context(current.project_id)
            assert preview["eligible"] and preview["inheritedOperations"] == (7 if frame_bound else 11)
            request = request_for(store, stopped)
            parent_policy = stopped.policy.model_dump(mode="json", by_alias=True)
            original_calls = list(calls)
            for changes in ({"expected_run_revision": request.expected_run_revision + 1},
                            {"expected_material_closure": "f" * 64}):
                with pytest.raises((InvalidTransitionError, RevisionConflictError)):
                    service.continue_material(current.project_id, request.model_copy(update=changes))
                assert origin_rows(store, current.id) == before
        child = service.continue_material(current.project_id, request)
        assert len(child.checkpoints) == preview["inheritedOperations"]
        if frame_bound:
            assert {item["operationKey"] for item in child.checkpoints} == {"source", "outline", "branches", "characters", "art", "script", "storyboard"}
            complete = run_text(service, child)
            assert len(complete.checkpoints) == 11
            assert len(calls) == len(original_calls) + 4
            assert calls[:len(original_calls)] == original_calls
            assert len(calls) == len(set(calls))
        else:
            assert calls == original_calls
        assert not registry._codex_exec_test_host.image_calls
        with closing(storage.projects.open(current.project_id)) as store:
            assert origin_rows(store, current.id) == before
            with store.repository.engine.connect() as connection:
                import json
                assert json.loads(connection.exec_driver_sql("SELECT policy FROM v2_autopilot_runs WHERE id=?", (str(current.id),)).scalar()) == parent_policy
            proposal = store.production_bridge_state().proposal
            assert {source.coordinates["field"] for source in proposal.presentation.sources if source.kind == "composition"} == {"composition"}
        with closing(storage.projects.open(current.project_id)) as store:
            assert store.repository.autopilot.current(current.project_id).id == child.id
    finally:
        service.close()


def test_corrected_cast_keeps_exact_physical_row_in_seven_logical_owners(tmp_path, monkeypatch):
    storage, registry, service, current, calls = installed(tmp_path, monkeypatch, frame_bound=True, corrected_cast=True)
    try:
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            before = origin_rows(store, current.id)
            source = {item["operationKey"]: item for item in stopped.checkpoints}
            assert source["characters"]["state"] == "delivered"
            assert source["characters:correction:1"]["state"] == "adopted"
            request = request_for(store, stopped)
            context = store.repository.autopilot.continuation_context(current.project_id)
            assert context["eligible"] and context["inheritedOperations"] == 7
            original_calls = list(calls)
            with store.repository._read() as session:
                owner = store.repository.autopilot
                run = owner.row(session, current.project_id)
                rows = session.scalars(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run.id)).all()
                for mutation in ("ordinal", "extra_correction", "missing_retry_proof", "superseded_adopted", "extra_owner"):
                    copies = [SimpleNamespace(id=row.id, operation_key=row.operation_key, state=row.state,
                        evidence=deepcopy(row.evidence)) for row in rows]
                    cast = next(row for row in copies if row.operation_key == "characters:correction:1")
                    if mutation == "ordinal":
                        cast.evidence["result"]["correctionOrdinal"] = 2
                    elif mutation == "superseded_adopted":
                        next(row for row in copies if row.operation_key == "characters").state = "adopted"
                    else:
                        extra = SimpleNamespace(id="foreign-row", operation_key="characters:correction:2",
                            state="adopted", evidence=deepcopy(cast.evidence))
                        if mutation == "extra_correction":
                            extra.evidence["result"]["correctionOrdinal"] = 2
                        elif mutation == "missing_retry_proof":
                            extra.operation_key = "characters:correction:1:retry:1"
                        else:
                            extra.operation_key = "foreign"
                            extra.evidence["owner"] = "foreign"
                        copies.append(extra)
                    with pytest.raises((ValueError, InvalidTransitionError)):
                        select_inherited_checkpoints(owner, session, run, copies)
        child = service.continue_material(current.project_id, request)
        assert len(child.checkpoints) == 7
        inherited = {item["operationKey"]: item for item in child.checkpoints}
        assert "characters" not in inherited
        assert inherited["characters:correction:1"]["evidence"] == source["characters:correction:1"]["evidence"]
        complete = run_text(service, child)
        assert len(complete.checkpoints) == 11
        assert calls[:len(original_calls)] == original_calls and len(calls) == len(original_calls) + 4
        assert len(calls) == len(set(calls)) and not registry._codex_exec_test_host.image_calls
        with closing(storage.projects.open(current.project_id)) as store:
            assert origin_rows(store, current.id) == before
    finally:
        service.close()


def test_second_continue_holds_references_until_replacement_installation(tmp_path, monkeypatch):
    storage, registry, service, current, calls = installed(tmp_path, monkeypatch, frame_bound=True)
    try:
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            root_before = origin_rows(store, current.id)
            child = service.continue_material(current.project_id, request_for(store, stopped))
        host = registry._codex_exec_test_host
        # Explicitly cancel the seven-row child before any new dispatch.
        assert len(child.checkpoints) == 7
        cancelled = service.control(current.project_id, RunControlRequest(expected_revision=child.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            child_before = origin_rows(store, child.id)
            request = request_for(store, cancelled)
            grandchild = service.continue_material(current.project_id, request)
        assert grandchild.policy.early_reference_limit == 4
        assert len(grandchild.checkpoints) == 7
        inherited = {item["operationKey"]: item["evidence"] for item in grandchild.checkpoints}
        assert inherited == {item["operationKey"]: item["evidence"] for item in cancelled.checkpoints if item["state"] == "adopted"}
        complete = run_text(service, grandchild)
        assert len(complete.checkpoints) == 11 and not host.image_calls
        assert len(calls) == len(set(calls))
        with closing(storage.projects.open(current.project_id)) as store:
            assert origin_rows(store, current.id) == root_before
            assert origin_rows(store, child.id) == child_before
        service.step(current.project_id)
        service.step(current.project_id)
        with closing(storage.projects.open(current.project_id)) as store:
            after = store.repository.autopilot.current(current.project_id)
        assert any(item["evidence"]["owner"] == "character-reference" for item in after.checkpoints)
    finally:
        service.close()


@pytest.mark.parametrize("links", [[("child", "root"), ("root", "child")],
    [("child", "foreign")], [("root", None), ("child", "root"), ("newer", "child")]])
def test_reference_hold_refuses_cyclic_foreign_or_stale_ancestry(links):
    from plotloom.autopilot_contracts import POLICY_VERSION
    from plotloom.autopilot_early_references import discover_early_references

    rows = [SimpleNamespace(id=key, predecessor_run_id=parent) for key, parent in links]
    session = SimpleNamespace(scalars=lambda _statement: SimpleNamespace(all=lambda: rows))
    store = SimpleNamespace(repository=SimpleNamespace(_read=lambda: nullcontext(session)))
    view = SimpleNamespace(policy=SimpleNamespace(version=POLICY_VERSION, early_reference_limit=4),
        id="child", project_id="project", predecessor_run_id="root", checkpoints=[])
    with pytest.raises(InvalidTransitionError, match="same-project ancestry"):
        discover_early_references(store, view)


def test_exact_inventory_refuses_mixed_missing_hash_text_and_coordinates(tmp_path, monkeypatch):
    storage, _registry, service, current, _calls = installed(tmp_path, monkeypatch, frame_bound=True)
    try:
        with closing(storage.projects.open(current.project_id)) as store, store.repository._read() as session:
            owner = store.repository.autopilot
            run = owner.row(session, current.project_id)
            checkpoints = session.scalars(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run.id)).all()
            context = owner.continuation_source_context(session, current.project_id)
            installed_evidence, proposal, inputs, script, board, mapping = context
            for mutation in ("mixed", "missing", "hash", "text", "coordinates", "spans", "unknown"):
                payload = deepcopy(proposal.proposal)
                source = next(item for item in payload["presentation"]["sources"] if item["kind"] == "composition")
                if mutation == "mixed":
                    replacement = next(item for item in prepare_presentation(inputs=inputs, script=script, storyboard=board, mapping=mapping).sources if item.id == source["id"])
                    source.update(replacement.model_dump(mode="json", by_alias=True))
                elif mutation == "missing":
                    payload["presentation"]["sources"].pop()
                elif mutation == "hash":
                    source["sourceHash"] = "f" * 64
                elif mutation == "text":
                    source["sourceText"] += " Foreign text"
                elif mutation == "coordinates":
                    source["coordinates"]["cutIndex"] += 1
                elif mutation == "spans":
                    source["spans"].pop()
                else:
                    source["unknownCreativeRequirement"] = "Never drop"
                with monkeypatch.context() as patched:
                    patched.setattr(owner, "continuation_source_context", lambda *_args:
                        (installed_evidence, SimpleNamespace(proposal=payload), inputs, script, board, mapping))
                    with pytest.raises(InvalidTransitionError):
                        select_inherited_checkpoints(owner, session, run, checkpoints)
    finally:
        service.close()


def test_frame_bound_continuation_refuses_prepared_reference_without_deletion(tmp_path, monkeypatch):
    storage, registry, service, current, calls = installed(tmp_path, monkeypatch, frame_bound=True)
    try:
        # Normal existing image owner prepares its inventory, then one reference.
        service.step(current.project_id)
        service.step(current.project_id)
        with closing(storage.projects.open(current.project_id)) as store:
            active = store.repository.autopilot.current(current.project_id)
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=active.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            before = origin_rows(store, current.id)
            context = store.repository.autopilot.continuation_context(current.project_id)
            assert not context["eligible"] and "dependent material" in " ".join(context["blockers"])
            request = request_for(store, stopped)
            with pytest.raises(InvalidTransitionError, match="dependent material"):
                service.continue_material(current.project_id, request)
            assert origin_rows(store, current.id) == before
        assert len(calls) == 16 and not registry._codex_exec_test_host.image_calls
    finally:
        service.close()
