"""Whole-package presentation review persisted through the bridge CAS owner."""
from .autopilot_authority import require_human_command
from sqlalchemy import select
from ...production_presentation import ProductionPresentation, ProductionPresentationUpdateRequest, review_presentation, project_presentation, bind_presentation_spans
from ...production_bridge_contracts import ProductionBridgeConflict
from plotloom.contract_identity import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..schema.project_production_bridge import ProductionBridgeRevisionRow


class ProductionBridgePresentationPersistence:
    def update_presentation(self, project_id: str, request: ProductionPresentationUpdateRequest):
        require_human_command(self._access)
        return self._save_presentation(project_id, revision=request.expected_proposal_revision,
            digest=request.expected_content_hash, request=request)

    def adopt_machine_presentation(self, project_id, *, decision_id, expected_revision, expected_hash):
        from .bridge_machine_adoption import bridge_adoption
        from ...native_bridge_presentation_contract import native_presentation_suggestions
        from ...creative_handoff_contracts import CreativeHandoffRequest
        from ...production_presentation import PresentationUpdate
        from ..schema import ProductionBridgeIntentJobRow
        with self._access.leases.lifecycle_write() as session:
            adoption = bridge_adoption(session, self._access, project_id, decision_id, "bridge-presentation", expected_revision, expected_hash)
            job = session.get(ProductionBridgeIntentJobRow, adoption.job_id)
            if job is None or job.project_id != project_id or job.status != "ready" or job.proposal_revision != expected_revision or job.proposal_content_hash != expected_hash:
                raise InvalidTransitionError("machine adoption requires the exact native presentation candidate")
            suggestions = native_presentation_suggestions(CreativeHandoffRequest.model_validate(job.native_request), job.candidate)
            entries = [PresentationUpdate(id=entry.id, spans=entry.spans) for entry in suggestions.entries]
            return self._save_presentation(project_id, revision=expected_revision, digest=expected_hash, entries=entries, adoption=adoption)

    def _save_presentation(self, project_id, *, revision, digest, request=None, entries=None, adoption=None):
        if request is not None:
            require_human_command(self._access)
        with self._access.leases.lifecycle_write() as session:
            if request is None:
                from .bridge_machine_adoption import bridge_adoption
                if adoption is None or adoption != bridge_adoption(session, self._access, project_id, adoption.decision_id, "bridge-presentation", revision, digest):
                    raise InvalidTransitionError("machine presentation adoption provenance changed")
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.status == "accepted":
                raise InvalidTransitionError("accepted production presentation cannot be edited")
            if head.revision != revision:
                raise RevisionConflictError("production bridge", revision, head.revision)
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == head.revision))
            if row is None or row.content_hash != digest:
                raise InvalidTransitionError("production presentation proposal changed")
            if self._proposal_stale(session, project_id, row):
                raise InvalidTransitionError("production presentation source is stale")
            try:
                original = ProductionPresentation.model_validate(row.proposal["presentation"])
                if request is not None:
                    from ..schema import ProductionBridgeIntentJobRow
                    from ...content_language_candidates import require_generated_bridge_edit
                    from ...language_policy import report_locale
                    jobs = session.scalars(select(ProductionBridgeIntentJobRow).where(
                        ProductionBridgeIntentJobRow.project_id == project_id,
                        ProductionBridgeIntentJobRow.transport == "codex_native",
                        ProductionBridgeIntentJobRow.status == "ready",
                        ProductionBridgeIntentJobRow.native_request["stage"].as_string() == "bridge-presentation",
                    ).order_by(ProductionBridgeIntentJobRow.created_at.desc())).all()
                    job = next((item for item in jobs if item.native_request.get("inputArtifacts", {}).get(
                        "presentation-source.json", {}).get("sourceHash") == original.source_hash), None)
                    if job is not None:
                        if job.native_request["source"].get("intentPackage") != row.proposal["intentPackage"]:
                            raise InvalidTransitionError("呈现建议的原始意图已改变；请重新准备当前来源的建议。")
                        candidate = {"lang": report_locale(job.native_request["inputArtifacts"]),
                            "entries": [entry.model_dump(mode="json", by_alias=True) for entry in request.entries]}
                        require_generated_bridge_edit(session, project_id, job.id, "bridge-presentation", candidate)
                package = (review_presentation(original, request) if request is not None else
                    ProductionPresentation.model_validate(original.model_dump() | {"reviewed": False,
                        "sources": bind_presentation_spans(original, entries), "machine_adoption": adoption}))
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
