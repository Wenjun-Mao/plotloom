"""Character-reference proposal preparation and manual delivery persistence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import ProjectLifecycleStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ...image_job_contracts import ImageJobError
from ..codec import _stored_utc, stable_hash
from ..schema import (
    CharacterReferenceProposalCandidateRow,
    CharacterReferenceProposalDeliveryRow,
    CharacterReferenceProposalRow,
    ManagedAssetProvenanceRow,
    ManagedAssetRow,
    ProjectRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_assets import ManagedAssetPersistence
from .media_character_references import CharacterReferencePersistence
from .media_identifiers import new_image_job_id


class CharacterReferenceProposalPersistence:
    """Own exploratory character-reference requests and their delivery lineage."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        references: CharacterReferencePersistence,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._references = references

    @staticmethod
    def _proposal_dict(row: CharacterReferenceProposalRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "parentCandidateAssetId": row.parent_candidate_asset_id, "request": row.request,
            "requestHash": row.request_hash, "state": row.state, "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _proposal_is_current_in_session(
        self, session: Session, proposal: CharacterReferenceProposalRow
    ) -> bool:
        if proposal.state == "cancelled":
            return False
        project = session.get(ProjectRow, proposal.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        snapshot = proposal.request.get("frozenSnapshot")
        if not isinstance(snapshot, dict):
            return False
        accepted_cast = snapshot.get("acceptedCast")
        if not isinstance(accepted_cast, dict) or not isinstance(accepted_cast.get("revision"), int):
            return False
        context = self._references.cast_reference_context(
            session,
            proposal.project_id,
            proposal.character_id,
            expected_cast_revision=accepted_cast["revision"],
        )
        if context is None:
            return False
        return snapshot.get("characterContextHash") == stable_hash(
            context
        )

    def prepare_character_reference_proposal(
        self,
        project_id: str,
        *,
        character_id: str,
        cast_revision: int,
        visual_direction: str,
        parent_candidate_asset_id: str | None,
    ) -> dict[str, Any]:
        """Freeze a cast-owned exploratory request without a Bible, Shot, or Approval."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            context = self._references.cast_reference_context(
                session, project_id, character_id, expected_cast_revision=cast_revision
            )
            if context is None:
                raise InvalidTransitionError(
                    "character reference proposal must name a current accepted cast subject at its accepted revision"
                )
            references: list[dict[str, Any]] = []
            if parent_candidate_asset_id is not None:
                candidate = session.scalar(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.asset_id == parent_candidate_asset_id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at.desc()).limit(1)
                )
                parent = session.get(CharacterReferenceProposalRow, candidate.proposal_id) if candidate else None
                asset = session.get(ManagedAssetRow, parent_candidate_asset_id)
                if (
                    candidate is None or parent is None or asset is None or asset.project_id != project_id
                    or parent.character_id != character_id or not self._proposal_is_current_in_session(session, parent)
                ):
                    raise InvalidTransitionError("proposal refinement must name a current candidate for the same character")
                references.append({
                    "assetId": asset.id, "role": "parent_output", "required": True,
                    "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                })
            job_id = new_image_job_id()
            snapshot = {
                "snapshotVersion": 4, "compilerVersion": "plotloom.cast-reference-proposal.v1",
                "projectId": project_id, "target": "character_reference_proposal",
                "characterId": character_id, "castRevision": cast_revision,
                "acceptedCast": context["acceptedCast"],
                "characterContext": context, "characterContextHash": stable_hash(context),
                "visualDirection": visual_direction.strip(), "references": references,
                "authority": "cast_owned_exploratory_only_no_story_bible_shot_approval_or_keyframe_selection",
            }
            request = {
                "schemaVersion": 3, "jobId": job_id, "executionContract": "codex_specialist.v2",
                "specialistPreflight": {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2"},
                "kind": "refinement" if parent_candidate_asset_id else "original",
                "target": "character_reference_proposal", "frozenSnapshot": snapshot,
            }
            proposal = CharacterReferenceProposalRow(
                id=job_id, project_id=project_id, character_id=character_id,
                parent_candidate_asset_id=parent_candidate_asset_id, request=request,
                request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=utc_now(),
            )
            session.add(proposal)
            session.flush()
            return {"proposal": self._proposal_dict(proposal, current=True)}

    def character_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in proposal.request["frozenSnapshot"].get("references", []):
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if asset is None or asset.project_id != project_id or asset.original_hash != reference.get("originalHash"):
                    raise InvalidTransitionError("frozen proposal reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                })
            return {"proposal": self._proposal_dict(proposal, current=True), "references": sources}

    def mark_character_reference_proposal_exported(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            if proposal.exported_at is None:
                proposal.exported_at = utc_now()
                proposal.state = "exported"
                session.flush()
            return self._proposal_dict(proposal, current=True)

    def cancel_character_reference_proposal(
        self, project_id: str, proposal_id: str, reason: str
    ) -> dict[str, Any]:
        """End a specialist handoff so it cannot strand project lifecycle work."""

        normalized_reason = reason.strip()
        if not normalized_reason or len(normalized_reason) > 2_000:
            raise ValueError(
                "character reference proposal cancellation reason must be between 1 and 2,000 characters"
            )
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if proposal.state not in {"prepared", "exported", "cancelled"}:
                raise InvalidTransitionError(
                    "only a prepared or exported character reference proposal can be cancelled"
                )
            if proposal.state != "cancelled":
                proposal.state = "cancelled"
                proposal.cancelled_at = utc_now()
                proposal.cancellation_reason = normalized_reason
                session.flush()
            return self._proposal_dict(proposal, current=False)

    def character_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            return self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal))

    def record_character_reference_proposal_rejection(
        self, project_id: str, proposal_id: str, code: str, *, publication_phase: str | None = None,
    ) -> None:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            session.add(CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, publication_phase=publication_phase, created_at=utc_now(),
            ))

    def record_character_reference_proposal_delivery(
        self,
        project_id: str,
        proposal_id: str,
        *,
        delivery_id: str,
        manifest: dict[str, Any],
        manifest_hash: str,
        outputs: list[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            existing = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "proposal delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.delivery_id == existing.id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "character proposal already has a final delivery")
            current = proposal.state in {"exported", "delivered"} and self._proposal_is_current_in_session(session, proposal)
            delivery = CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[CharacterReferenceProposalCandidateRow] = []
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri,
                    original_hash=output["originalHash"], display_uri=display_uri,
                    display_hash=output["displayHash"], mime_type=output["mimeType"], byte_size=output["byteSize"],
                    width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset)
                session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "character_reference_proposal", "rights": "unknown", "proposalId": proposal.id,
                        "rightsNote": None, "declaredAdditions": [], "deliveryId": delivery_id,
                        "outputFilename": output["filename"], "actualPrompt": manifest["actualPrompt"],
                        "toolEvidence": manifest["toolEvidence"], "executorProvenance": manifest.get("executorProvenance"),
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = CharacterReferenceProposalCandidateRow(
                    id=new_id(), proposal_id=proposal.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            proposal.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}

    @staticmethod
    def _proposal_candidate_dict(session: Session, row: CharacterReferenceProposalCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "proposalId": row.proposal_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": ManagedAssetPersistence.managed_asset_dict(asset) if asset is not None else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def list_character_reference_proposals(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            proposals = session.scalars(
                select(CharacterReferenceProposalRow).where(CharacterReferenceProposalRow.project_id == project_id)
                .order_by(CharacterReferenceProposalRow.created_at.desc(), CharacterReferenceProposalRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for proposal in proposals:
                deliveries = session.scalars(
                    select(CharacterReferenceProposalDeliveryRow)
                    .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal.id)
                    .order_by(CharacterReferenceProposalDeliveryRow.created_at.desc(), CharacterReferenceProposalDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal)),
                    "deliveries": [{
                        "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                        "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                        "publicationPhase": delivery.publication_phase,
                        "createdAt": _stored_utc(delivery.created_at).isoformat(),
                        "candidates": [self._proposal_candidate_dict(session, item) for item in session.scalars(
                            select(CharacterReferenceProposalCandidateRow)
                            .where(CharacterReferenceProposalCandidateRow.delivery_id == delivery.id)
                            .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                        ).all()],
                    } for delivery in deliveries],
                })
            return result
