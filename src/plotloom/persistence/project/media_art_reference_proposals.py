"""Accepted-art-bound manual environment and prop reference studies."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import json
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import ProjectLifecycleStatus, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ...exceptions import RevisionConflictError
from ...image_job_contracts import ImageJobError
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ArtReferenceProposalCandidateRow,
    ArtReferenceDecisionRow,
    ArtReferenceDecisionStateRow,
    ArtReferenceProposalDeliveryRow,
    ArtReferenceProposalRow,
    ArtRevisionRow,
    ManagedAssetProvenanceRow,
    ManagedAssetRow,
    ProjectRow,
)
from .access import ProjectPersistenceAccess
from .art import ProjectArtPersistence
from .media_assets import ManagedAssetPersistence
from .media_identifiers import new_image_job_id


ArtSubjectType = Literal["scene", "prop"]


def _content_hash(value: dict[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class ArtReferenceProposalPersistence:
    """Keep F3B study lifecycle separate from art canon and production shots."""

    def __init__(self, access: ProjectPersistenceAccess, art: ProjectArtPersistence) -> None:
        self._access, self._art = access, art

    @staticmethod
    def _proposal_dict(row: ArtReferenceProposalRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "subjectType": row.subject_type,
            "subjectId": row.subject_id, "request": row.request, "requestHash": row.request_hash,
            "state": row.state, "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _accepted_subject(
        self,
        session: Session, project_id: str, subject_type: ArtSubjectType, subject_id: str
    ) -> tuple[ArtRevisionRow, dict[str, Any]]:
        return self._art.accepted_current_subject(
            session, project_id, subject_type, subject_id
        )

    def _proposal_is_current_in_session(self, session: Session, proposal: ArtReferenceProposalRow) -> bool:
        if proposal.state == "cancelled":
            return False
        project = session.get(ProjectRow, proposal.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        snapshot = proposal.request.get("frozenSnapshot")
        if not isinstance(snapshot, dict):
            return False
        accepted = snapshot.get("acceptedArt")
        subject = snapshot.get("subject")
        if not isinstance(accepted, dict) or not isinstance(subject, dict):
            return False
        try:
            revision, current_subject = self._accepted_subject(
                session, proposal.project_id, proposal.subject_type, proposal.subject_id  # type: ignore[arg-type]
            )
        except InvalidTransitionError:
            return False
        return (
            accepted.get("revision") == revision.revision
            and accepted.get("contentHash") == revision.content_hash
            and subject.get("id") == proposal.subject_id
            and subject.get("contentHash") == _content_hash(current_subject)
        )

    def prepare_art_reference_proposal(
        self, project_id: str, *, subject_type: ArtSubjectType, subject_id: str,
        render_direction: str,
    ) -> dict[str, Any]:
        """Freeze only a current art subject plus an explicit render-direction overlay."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            revision, subject = self._accepted_subject(session, project_id, subject_type, subject_id)
            job_id = new_image_job_id()
            snapshot = {
                "snapshotVersion": 1,
                "compilerVersion": "plotloom.art-reference-proposal.v1",
                "projectId": project_id,
                "target": "art_reference_proposal",
                "acceptedArt": {"revision": revision.revision, "contentHash": revision.content_hash},
                "subject": {
                    "type": subject_type, "id": subject_id, "content": subject,
                    "contentHash": _content_hash(subject),
                },
                "renderDirection": render_direction.strip(),
                "authority": "accepted_art_subject_plus_creator_render_overlay_exploratory_only_no_selection_or_shot",
            }
            request = {
                "schemaVersion": 3, "jobId": job_id,
                "executionContract": "codex_specialist.v2",
                "specialistPreflight": {
                    "version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3",
                    "executionContract": "codex_specialist.v2",
                },
                "kind": "art_reference", "target": "art_reference_proposal", "frozenSnapshot": snapshot,
            }
            proposal = ArtReferenceProposalRow(
                id=job_id, project_id=project_id, subject_type=subject_type, subject_id=subject_id,
                request=request, request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=utc_now(),
            )
            session.add(proposal)
            session.flush()
            return {"proposal": self._proposal_dict(proposal, current=True)}

    def art_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("art reference proposal is no longer current and cannot be copied")
            return {"proposal": self._proposal_dict(proposal, current=True), "references": []}

    def mark_art_reference_proposal_exported(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("art reference proposal is no longer current and cannot be copied")
            if proposal.exported_at is None:
                proposal.exported_at, proposal.state = utc_now(), "exported"
                session.flush()
            return self._proposal_dict(proposal, current=True)

    def cancel_art_reference_proposal(self, project_id: str, proposal_id: str, reason: str) -> dict[str, Any]:
        normalized = reason.strip()
        if not normalized or len(normalized) > 2_000:
            raise ValueError("art reference proposal cancellation reason must be between 1 and 2,000 characters")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            if proposal.state not in {"prepared", "exported", "cancelled"}:
                raise InvalidTransitionError("only a prepared or exported art reference proposal can be cancelled")
            if proposal.state != "cancelled":
                proposal.state, proposal.cancelled_at, proposal.cancellation_reason = "cancelled", utc_now(), normalized
                session.flush()
            return self._proposal_dict(proposal, current=False)

    def art_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            return self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal))

    def record_art_reference_proposal_rejection(self, project_id: str, proposal_id: str, code: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            session.add(ArtReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    def record_art_reference_proposal_delivery(
        self, project_id: str, proposal_id: str, *, delivery_id: str, manifest: dict[str, Any],
        manifest_hash: str, outputs: list[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(ArtReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("art reference proposal not found")
            existing = session.scalar(select(ArtReferenceProposalDeliveryRow).where(
                ArtReferenceProposalDeliveryRow.proposal_id == proposal_id,
                ArtReferenceProposalDeliveryRow.delivery_id == delivery_id,
            ).limit(1))
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "art reference delivery identity was already recorded with different content")
                return self._delivery_result(session, existing, idempotent=True)
            finalized = session.scalar(select(ArtReferenceProposalDeliveryRow).where(
                ArtReferenceProposalDeliveryRow.proposal_id == proposal_id,
                ArtReferenceProposalDeliveryRow.delivery_id.is_not(None),
            ).limit(1))
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "art reference proposal already has a final delivery")
            current = proposal.state in {"exported", "delivered"} and self._proposal_is_current_in_session(session, proposal)
            delivery = ArtReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return self._delivery_result(session, delivery, idempotent=False)
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri, original_hash=output["originalHash"],
                    display_uri=display_uri, display_hash=output["displayHash"], mime_type=output["mimeType"],
                    byte_size=output["byteSize"], width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset); session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "art_reference_proposal", "rights": "unknown", "proposalId": proposal.id,
                        "subjectType": proposal.subject_type, "subjectId": proposal.subject_id,
                        "deliveryId": delivery_id, "outputFilename": output["filename"],
                        "actualPrompt": manifest["actualPrompt"], "toolEvidence": manifest["toolEvidence"],
                        "executorProvenance": manifest.get("executorProvenance"), "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                session.add(ArtReferenceProposalCandidateRow(
                    id=new_id(), proposal_id=proposal.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                ))
            proposal.state = "delivered"; session.flush()
            return self._delivery_result(session, delivery, idempotent=False)

    @staticmethod
    def _candidate_dict(session: Session, row: ArtReferenceProposalCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "proposalId": row.proposal_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": ManagedAssetPersistence.managed_asset_dict(asset) if asset is not None else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _delivery_result(self, session: Session, delivery: ArtReferenceProposalDeliveryRow, *, idempotent: bool) -> dict[str, Any]:
        candidates = session.scalars(select(ArtReferenceProposalCandidateRow).where(
            ArtReferenceProposalCandidateRow.delivery_id == delivery.id
        ).order_by(ArtReferenceProposalCandidateRow.created_at, ArtReferenceProposalCandidateRow.id)).all()
        return {"deliveryId": delivery.delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                "idempotent": idempotent, "candidates": [self._candidate_dict(session, item) for item in candidates]}

    def list_art_reference_proposals(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            proposals = session.scalars(select(ArtReferenceProposalRow).where(
                ArtReferenceProposalRow.project_id == project_id
            ).order_by(ArtReferenceProposalRow.created_at.desc(), ArtReferenceProposalRow.id.desc())).all()
            result: list[dict[str, Any]] = []
            for proposal in proposals:
                deliveries = session.scalars(select(ArtReferenceProposalDeliveryRow).where(
                    ArtReferenceProposalDeliveryRow.proposal_id == proposal.id
                ).order_by(ArtReferenceProposalDeliveryRow.created_at.desc(), ArtReferenceProposalDeliveryRow.id.desc())).all()
                result.append({
                    **self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal)),
                    "deliveries": [{
                        "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                        "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                        "createdAt": _stored_utc(delivery.created_at).isoformat(),
                        "candidates": [self._candidate_dict(session, item) for item in session.scalars(select(ArtReferenceProposalCandidateRow).where(
                            ArtReferenceProposalCandidateRow.delivery_id == delivery.id
                        ).order_by(ArtReferenceProposalCandidateRow.created_at, ArtReferenceProposalCandidateRow.id)).all()],
                    } for delivery in deliveries],
                })
            return result

    def _decision_state_in_session(
        self, session: Session, project_id: str, subject_type: ArtSubjectType, subject_id: str, now: Any,
    ) -> ArtReferenceDecisionStateRow:
        state = session.get(ArtReferenceDecisionStateRow, (project_id, subject_type, subject_id))
        if state is None:
            state = ArtReferenceDecisionStateRow(
                project_id=project_id, subject_type=subject_type, subject_id=subject_id,
                revision=0, active_decision_id=None, updated_at=now,
            )
            session.add(state); session.flush()
        return state

    @staticmethod
    def _decision_dict(row: ArtReferenceDecisionRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "subjectType": row.subject_type,
            "subjectId": row.subject_id, "referenceRevision": row.reference_revision,
            "acceptedArtRevision": row.accepted_art_revision, "acceptedArtHash": row.accepted_art_hash,
            "subject": row.subject, "subjectHash": row.subject_hash, "assetId": row.asset_id,
            "assetHash": row.asset_hash, "proposalId": row.proposal_id, "candidateId": row.candidate_id,
            "current": current, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _decision_is_current_in_session(
        self, session: Session, project_id: str, decision_id: str | None,
    ) -> bool:
        if decision_id is None:
            return False
        decision = session.get(ArtReferenceDecisionRow, decision_id)
        if decision is None or decision.project_id != project_id:
            return False
        try:
            revision, subject = self._accepted_subject(
                session, project_id, decision.subject_type, decision.subject_id  # type: ignore[arg-type]
            )
        except InvalidTransitionError:
            return False
        if (
            decision.accepted_art_revision != revision.revision
            or decision.accepted_art_hash != revision.content_hash
            or decision.subject_hash != _content_hash(subject)
        ):
            return False
        asset = session.get(ManagedAssetRow, decision.asset_id)
        candidate = session.get(ArtReferenceProposalCandidateRow, decision.candidate_id)
        proposal = session.get(ArtReferenceProposalRow, decision.proposal_id)
        delivery = session.get(ArtReferenceProposalDeliveryRow, candidate.delivery_id) if candidate is not None else None
        return bool(
            asset is not None and asset.project_id == project_id and asset.original_hash == decision.asset_hash
            and candidate is not None and candidate.asset_id == decision.asset_id and candidate.proposal_id == decision.proposal_id
            and delivery is not None and delivery.state == "accepted"
            and proposal is not None and proposal.project_id == project_id
            and proposal.subject_type == decision.subject_type and proposal.subject_id == decision.subject_id
            and self._proposal_is_current_in_session(session, proposal)
        )

    def create_art_reference_decision(
        self, project_id: str, *, subject_type: ArtSubjectType, subject_id: str, asset_id: str,
        expected_reference_revision: int,
    ) -> dict[str, Any]:
        """Explicitly select one current F3B candidate; never infer or consume it."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            revision, subject = self._accepted_subject(session, project_id, subject_type, subject_id)
            now = utc_now()
            state = self._decision_state_in_session(session, project_id, subject_type, subject_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("art-reference", expected_reference_revision, state.revision)
            candidate = session.scalar(select(ArtReferenceProposalCandidateRow).join(
                ArtReferenceProposalRow, ArtReferenceProposalCandidateRow.proposal_id == ArtReferenceProposalRow.id
            ).where(
                ArtReferenceProposalCandidateRow.asset_id == asset_id,
                ArtReferenceProposalRow.project_id == project_id,
                ArtReferenceProposalRow.subject_type == subject_type,
                ArtReferenceProposalRow.subject_id == subject_id,
            ).order_by(ArtReferenceProposalCandidateRow.created_at.desc(), ArtReferenceProposalCandidateRow.id.desc()).limit(1))
            if candidate is None:
                raise NotFoundError("art reference candidate not found for this accepted subject")
            proposal = session.get(ArtReferenceProposalRow, candidate.proposal_id)
            asset = session.get(ManagedAssetRow, asset_id)
            delivery = session.get(ArtReferenceProposalDeliveryRow, candidate.delivery_id)
            if (
                proposal is None or asset is None or asset.project_id != project_id
                or delivery is None or delivery.state != "accepted"
                or not self._proposal_is_current_in_session(session, proposal)
            ):
                raise InvalidTransitionError("art reference decision requires a current same-subject F3B candidate")
            state.revision += 1
            state.updated_at = now
            decision = ArtReferenceDecisionRow(
                id=new_id(), project_id=project_id, subject_type=subject_type, subject_id=subject_id,
                reference_revision=state.revision, accepted_art_revision=revision.revision,
                accepted_art_hash=revision.content_hash, subject=subject, subject_hash=_content_hash(subject),
                asset_id=asset.id, asset_hash=asset.original_hash, proposal_id=proposal.id,
                candidate_id=candidate.id, created_at=now,
            )
            session.add(decision); session.flush()
            state.active_decision_id = decision.id
            session.flush()
            return self._decision_dict(decision, current=True) | {"stateRevision": state.revision}

    def list_art_reference_decisions(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(select(ArtReferenceDecisionRow).where(
                ArtReferenceDecisionRow.project_id == project_id
            ).order_by(ArtReferenceDecisionRow.created_at.desc(), ArtReferenceDecisionRow.id.desc())).all()
            states = session.scalars(select(ArtReferenceDecisionStateRow).where(
                ArtReferenceDecisionStateRow.project_id == project_id
            )).all()
            state_by_subject = {(item.subject_type, item.subject_id): item for item in states}
            return {
                "states": [{
                    "subjectType": state.subject_type, "subjectId": state.subject_id,
                    "revision": state.revision, "activeDecisionId": state.active_decision_id,
                    "current": self._decision_is_current_in_session(session, project_id, state.active_decision_id),
                } for state in sorted(states, key=lambda item: (item.subject_type, item.subject_id))],
                "decisions": [self._decision_dict(
                    row,
                    current=(
                        state_by_subject.get((row.subject_type, row.subject_id)) is not None
                        and state_by_subject[(row.subject_type, row.subject_id)].active_decision_id == row.id
                        and self._decision_is_current_in_session(session, project_id, row.id)
                    ),
                ) for row in rows],
            }
