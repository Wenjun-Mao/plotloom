"""Managed project asset and immutable crop lineage persistence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...keyframe_preparation import has_matching_aspect
from ..codec import _stored_utc
from ..schema import ManagedAssetProvenanceRow, ManagedAssetRow, ReviewedShotBindingRow
from .access import ProjectPersistenceAccess
from .media_admission import KeyframeAdmission


class ManagedAssetPersistence:
    """Own immutable managed assets, provenance, and approved-source crops."""

    def __init__(self, access: ProjectPersistenceAccess, admission: KeyframeAdmission) -> None:
        self._access = access
        self._admission = admission

    @staticmethod
    def managed_asset_dict(row: ManagedAssetRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "projectId": row.project_id,
            "originalHash": row.original_hash,
            "displayHash": row.display_hash,
            "mimeType": row.mime_type,
            "byteSize": row.byte_size,
            "width": row.width,
            "height": row.height,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_managed_import(
        self,
        project_id: str,
        *,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        declaration: dict[str, Any],
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Publish one independent project provenance record over stored bytes."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            # Publish under the same lifecycle writer lease that admits the
            # immutable metadata, so a rejected/archived project never leaves
            # a newly written unowned blob behind.
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type, byte_size=byte_size,
                width=width, height=height, created_at=now,
            )
            session.add(asset)
            # These rows intentionally have no ORM relationship (their
            # history stays one-way immutable), so establish the asset FK
            # before adding the independent provenance declaration.
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration=declaration, created_at=now,
            ))
            session.flush()
            return self.managed_asset_dict(asset)

    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            return {
                **self.managed_asset_dict(asset),
                "originalUri": asset.original_uri,
                "displayUri": asset.display_uri,
            }

    def reviewed_keyframe_crop_source(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        """Read the exact current selected source for a proposed crop.

        The write method repeats these checks. This read projection only lets
        the API obtain bytes for a transform; it does not authorize publishing
        a derivative after a selection has changed.
        """

        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            state = self._admission.selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if (
                binding is None
                or not self._admission.reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop needs the current reviewed selected keyframe"
                )
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            return {
                "bindingId": binding.id,
                "selectionRevision": binding.selection_revision,
                "assetId": asset.id,
                "originalHash": asset.original_hash,
                "mimeType": asset.mime_type,
                "width": asset.width,
                "height": asset.height,
                "originalUri": asset.original_uri,
            }

    def record_reviewed_keyframe_center_crop(
        self,
        project_id: str,
        *,
        source: dict[str, Any],
        target_profile: dict[str, Any],
        expected_selection_revision: int,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Persist a source-bound crop without selecting it for the Shot."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            state = self._admission.selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, source["bindingId"])
            if (
                binding is None
                or binding.asset_id != source["assetId"]
                or binding.selection_revision != source["selectionRevision"]
                or not self._admission.reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop source is no longer the current reviewed keyframe"
                )
            source_asset = session.get(ManagedAssetRow, binding.asset_id)
            if (
                source_asset is None
                or source_asset.project_id != project_id
                or source_asset.original_hash != source["originalHash"]
            ):
                raise InvalidTransitionError("keyframe crop source bytes are unavailable")
            target_width, target_height = int(target_profile["width"]), int(target_profile["height"])
            if has_matching_aspect(
                source_asset.width, source_asset.height, target_width, target_height
            ):
                raise InvalidTransitionError(
                    "keyframe already matches the requested profile aspect"
                )
            if (width, height) != (target_width, target_height):
                raise InvalidTransitionError(
                    "derived keyframe crop does not match the requested profile"
                )
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type,
                byte_size=byte_size, width=width, height=height, created_at=now,
            )
            session.add(asset)
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration={
                    "origin": "plotloom_keyframe_center_crop",
                    "sourceBindingId": binding.id,
                    "sourceAssetId": source_asset.id,
                    "sourceOriginalHash": source_asset.original_hash,
                    "targetProfile": dict(target_profile),
                    "transform": {
                        "version": 1,
                        "strategy": "cover_center_crop",
                        "centering": [0.5, 0.5],
                    },
                },
                created_at=now,
            ))
            session.flush()
            return self.managed_asset_dict(asset)

    def list_managed_assets(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(ManagedAssetRow)
                .where(ManagedAssetRow.project_id == project_id)
                .order_by(ManagedAssetRow.created_at, ManagedAssetRow.id)
            ).all()
            result = []
            for row in rows:
                provenance = session.scalar(
                    select(ManagedAssetProvenanceRow)
                    .where(ManagedAssetProvenanceRow.asset_id == row.id)
                    .order_by(ManagedAssetProvenanceRow.created_at)
                    .limit(1)
                )
                result.append({
                    **self.managed_asset_dict(row),
                    "provenance": provenance.declaration if provenance else None,
                })
            return result
