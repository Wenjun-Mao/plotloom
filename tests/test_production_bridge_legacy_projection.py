"""Read-only projection for the retained pre-correction accepted bridge fixture."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from sqlalchemy import select

from plotloom.pipeline import RunSecretBroker
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest, ProductionBridgeConflict, ProductionBridgeIntentUpdateRequest,
)
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from plotloom.persistence.schema.project_production_bridge import (
    ProductionBridgeAdmissionRow, ProductionBridgeRevisionRow,
)
from tests.test_production_bridge_intent import FakeAdapter, FakeResolver, _pending_project, _profile, _wait_for_job


def test_retained_accepted_row_projects_source_model_and_author_without_rewriting(tmp_path: Path) -> None:
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter(held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job_id = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        _wait_for_job(service, adapter, job_id)
        with closing(storage.projects.open(project_id)) as store:
            inferred = store.production_bridge_state().proposal
            assert inferred
            reviewed = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
                expected_proposal_revision=inferred.revision,
                expected_content_hash=inferred.content_hash,
                entries=[{"id": entry.id, "text": f"作者修订：{entry.id}"} for entry in inferred.intent_package.entries],
            )).proposal
            assert reviewed
            store.accept_production_bridge(ProductionBridgeAcceptRequest(
                expected_proposal_revision=reviewed.revision, expected_content_hash=reviewed.content_hash,
            ))

            bridge = store.repository.production_bridge
            with bridge._access.leases.lifecycle_write() as session:
                rows = list(session.scalars(select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == project_id,
                ).order_by(ProductionBridgeRevisionRow.revision)))
                for row in rows:
                    package = row.proposal["intentPackage"]
                    origin, review_state = package["suggestionOrigin"], package["reviewState"]
                    method = "author_reviewed.v1" if review_state == "author_saved" else (
                        "model_inference.v1" if origin == "model_inference.v1" else "pending_inference.v1"
                    )
                    old_entries = [{
                        **{key: value for key, value in entry.items() if key not in {"sourceExcerpt", "suggestedText"}},
                        "method": method,
                        "suggestedText": entry["suggestedText"] if origin == "model_inference.v1" else entry["sourceExcerpt"],
                    } for entry in package["entries"]]
                    old_package = {"method": method, "entries": old_entries, "provenance": package.get("provenance")}
                    row.proposal = {**row.proposal, "intentPackage": old_package}
                    row.content_hash = bridge._proposal_digest(
                        row.inputs, row.proposal,
                        [ProductionBridgeConflict.model_validate(conflict) for conflict in row.conflicts],
                    )
                admission = session.scalar(select(ProductionBridgeAdmissionRow).where(
                    ProductionBridgeAdmissionRow.project_id == project_id,
                ))
                assert admission
                admission.proposal_content_hash = rows[-1].content_hash
            with bridge._access.leases.read() as session:
                before = [row.proposal for row in session.scalars(select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == project_id,
                ).order_by(ProductionBridgeRevisionRow.revision))]
            state = store.production_bridge_state()
            assert state.status == "accepted" and state.proposal
            package = state.proposal.intent_package
            assert package.suggestion_origin == "model_inference.v1"
            assert package.review_state == "author_saved"
            assert package.provenance["jobId"] == job_id
            first = package.entries[0]
            assert first.source_excerpt == "Lin chooses."
            assert first.suggested_text == f"角色在此推动冲突并改变局势：{first.id}"
            assert first.text == f"作者修订：{first.id}"
            with bridge._access.leases.read() as session:
                after = [row.proposal for row in session.scalars(select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == project_id,
                ).order_by(ProductionBridgeRevisionRow.revision))]
            assert after == before
    finally:
        service.close()
