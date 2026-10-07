"""Whole-package presentation review persisted through the bridge CAS owner."""
from sqlalchemy import select
from ...production_presentation import ProductionPresentation, ProductionPresentationUpdateRequest, review_presentation, project_presentation
from ...production_bridge_contracts import ProductionBridgeConflict
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..schema.project_production_bridge import ProductionBridgeRevisionRow


class ProductionBridgePresentationPersistence:
    def update_presentation(self, project_id: str, request: ProductionPresentationUpdateRequest):
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.status == "accepted":
                raise InvalidTransitionError("accepted production presentation cannot be edited")
            if head.revision != request.expected_proposal_revision:
                raise RevisionConflictError("production bridge", request.expected_proposal_revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != request.expected_content_hash:
                raise InvalidTransitionError("production presentation proposal changed")
            if self._current(session, project_id, row.inputs):
                raise InvalidTransitionError("production presentation source is stale")
            try:
                package = review_presentation(ProductionPresentation.model_validate(row.proposal["presentation"]), request)
                payload = project_presentation(row.proposal["payload"], package)
            except ValueError as error:
                raise InvalidTransitionError(str(error)) from error
            conflicts = [ProductionBridgeConflict.model_validate(item) for item in row.conflicts if item.get("code") not in {"presentation_required", "canonical_validation"}]
            if self._intent_package(session, row).review_state != "pending":
                conflicts.extend(self._validate_payload(session, project_id, payload))
            proposal = {**row.proposal, "payload": payload, "presentation": package.model_dump(mode="json", by_alias=True)}
            now = utc_now(); head.revision += 1; head.status = "ready"; head.updated_at = now
            session.add(ProductionBridgeRevisionRow(id=new_id(), project_id=project_id, revision=head.revision,
                content_hash=self._proposal_digest(row.inputs, proposal, conflicts), inputs=row.inputs,
                proposal=proposal, conflicts=[item.model_dump(mode="json") for item in conflicts],
                installable=not conflicts, prepared_at=now))
        return self.get_state(project_id)
