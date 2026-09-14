"""Image-job manual package, delivery, and candidate-lineage persistence."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ...image_job_contracts import ImageJobError
from ..codec import _stored_utc
from ..schema import (
    ImageJobCandidateRow,
    ImageJobDeliveryRow,
    ImageJobRow,
    ManagedAssetProvenanceRow,
    ManagedAssetRow,
)
from .access import ProjectPersistenceAccess
from .media_assets import ManagedAssetPersistence
from .media_image_currentness import ImageJobCurrentness


class ImageJobDeliveryPersistence:
    """Own exported image-job packages, delivery idempotency, and candidate assets."""

    def __init__(self, access: ProjectPersistenceAccess, currentness: ImageJobCurrentness) -> None:
        self._access = access
        self._currentness = currentness

    def image_job_package_sources(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._currentness.image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in job.request["frozenSnapshot"].get("references", []):
                if reference.get("role") not in {
                    "parent_output", "source_keyframe", "character_identity"
                }:
                    continue
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if (
                    asset is None or asset.project_id != project_id
                    or asset.original_hash != reference.get("originalHash")
                ):
                    raise InvalidTransitionError("frozen image-job reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                    "characterId": reference.get("characterId"),
                })
            return {"job": self._currentness.image_job_dict(job, current=True), "references": sources}

    def mark_image_job_exported(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._currentness.image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            if job.exported_at is None:
                job.exported_at = utc_now()
                job.state = "exported"
                session.flush()
            return self._currentness.image_job_dict(job, current=True)

    def cancel_image_job(self, project_id: str, job_id: str, reason: str) -> dict[str, Any]:
        reason = reason.strip()
        if not reason or len(reason) > 2_000:
            raise ValueError("image job cancellation reason must be between 1 and 2,000 characters")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state != "cancelled":
                job.state = "cancelled"
                job.cancelled_at = utc_now()
                job.cancellation_reason = reason
                session.flush()
            return self._currentness.image_job_dict(job, current=False)

    def image_job_delivery_context(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            return self._currentness.image_job_dict(job, current=self._currentness.image_job_is_current_in_session(session, job))

    def record_image_job_delivery_rejection(self, project_id: str, job_id: str, code: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            session.add(ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    @staticmethod
    def image_candidate_dict(session: Session, row: ImageJobCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "jobId": row.job_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": ManagedAssetPersistence.managed_asset_dict(asset) if asset else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_image_job_delivery(
        self, project_id: str, job_id: str, *, delivery_id: str, manifest: dict[str, Any],
        manifest_hash: str, outputs: Sequence[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        """Atomically admit one verified delivery, publishing only after admission.

        The artifact callback runs under the lifecycle writer only after the
        durable final-delivery, project-lifecycle, and currentness checks pass.
        It keeps a duplicate, cancelled, revoked, or archived Refresh from
        creating unowned content-addressed blobs before repository admission.
        """

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            existing = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == existing.id)
                    .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self.image_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "image job already has a final delivery")
            current = job.state in {"exported", "delivered"} and self._currentness.image_job_is_current_in_session(session, job)
            delivery = ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[ImageJobCandidateRow] = []
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
                        "origin": "codex_image_job", "rights": "unknown", "jobId": job.id,
                        "rightsNote": None, "declaredAdditions": [],
                        "deliveryId": delivery_id, "outputFilename": output["filename"],
                        "actualPrompt": manifest["actualPrompt"], "toolEvidence": manifest["toolEvidence"],
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = ImageJobCandidateRow(
                    id=new_id(), job_id=job.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            job.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self.image_candidate_dict(session, item) for item in candidates]}

    def list_image_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            jobs = session.scalars(
                select(ImageJobRow).where(ImageJobRow.project_id == project_id)
                .order_by(ImageJobRow.created_at.desc(), ImageJobRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for job in jobs:
                deliveries = session.scalars(
                    select(ImageJobDeliveryRow).where(ImageJobDeliveryRow.job_id == job.id)
                    .order_by(ImageJobDeliveryRow.created_at.desc(), ImageJobDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._currentness.image_job_dict(job, current=self._currentness.image_job_is_current_in_session(session, job)),
                    "deliveries": [
                        {
                            "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                            "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                            "createdAt": _stored_utc(delivery.created_at).isoformat(),
                            "candidates": [self.image_candidate_dict(session, candidate) for candidate in session.scalars(
                                select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == delivery.id)
                                .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                            ).all()],
                        }
                        for delivery in deliveries
                    ],
                })
            return result
