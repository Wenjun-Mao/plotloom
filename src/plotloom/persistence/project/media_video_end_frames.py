"""Shot-owned end-frame choices for reviewed H3 first/last-frame requests."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..schema import ManagedAssetProvenanceRow, ManagedAssetRow, VideoEndFrameDecisionRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_video_source import VideoSourceTiming


class VideoEndFrames:
    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence,
                 admission: KeyframeAdmission, source_timing: VideoSourceTiming) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._source_timing = source_timing

    @staticmethod
    def latest(session: Session, project_id: str, shot_id: str) -> VideoEndFrameDecisionRow | None:
        return session.scalar(select(VideoEndFrameDecisionRow).where(
            VideoEndFrameDecisionRow.project_id == project_id,
            VideoEndFrameDecisionRow.shot_id == shot_id,
        ).order_by(VideoEndFrameDecisionRow.revision.desc()).limit(1))

    @staticmethod
    def _projection(row: VideoEndFrameDecisionRow | None) -> dict[str, Any]:
        if row is None:
            return {"revision": 0, "assetId": None}
        return {
            "revision": row.revision, "assetId": row.asset_id,
            "originalHash": row.original_hash, "aspectPolicy": row.aspect_policy,
            "mimeType": row.mime_type, "width": row.width, "height": row.height,
            "provenance": row.provenance,
            "approvalId": row.approval_id, "storyboardRevision": row.storyboard_revision,
            "sourceTiming": row.source_timing,
        }

    def current(self, session: Session, project_id: str, shot_id: str,
                approval_id: str, storyboard_revision: int, source_timing: dict[str, Any]) -> dict[str, Any]:
        row = self.latest(session, project_id, shot_id)
        if row is None:
            return self._projection(None)
        if (row.approval_id != approval_id or row.storyboard_revision != storyboard_revision
                or row.source_timing != source_timing):
            raise InvalidTransitionError("ending-frame decision is stale for this shot and approval")
        if row.asset_id is not None:
            asset = session.get(ManagedAssetRow, row.asset_id)
            if (asset is None or asset.project_id != project_id or asset.original_hash != row.original_hash
                    or asset.mime_type != row.mime_type or asset.width != row.width or asset.height != row.height):
                raise InvalidTransitionError("ending-frame asset changed")
        return self._projection(row)

    def decision_is_current(self, session: Session, project_id: str, shot_id: str,
                            frozen: object) -> bool:
        row = self.latest(session, project_id, shot_id)
        if row is None:
            # Older frozen jobs predate the optional decision table. They
            # mean the same absent decision at revision zero.
            return frozen is None or frozen == self._projection(None)
        if not isinstance(frozen, dict):
            return False
        try:
            return frozen == self.current(session, project_id, shot_id,
                                          row.approval_id, row.storyboard_revision, row.source_timing)
        except InvalidTransitionError:
            return False

    def get(self, project_id: str, shot_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            return self._projection(self.latest(session, project_id, shot_id))

    def choose(self, project_id: str, shot_id: str, *, asset_id: str | None,
               approval_id: str, storyboard_revision: int, expected_revision: int,
               aspect_policy: str | None) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            approval = self._admission.approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("ending-frame approval is not current")
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("ending frame needs one current storyboard shot")
            source = self._source_timing.binding_in_session(session, project_id, shot_id, shot.duration_units)
            previous = self.latest(session, project_id, shot_id)
            actual = previous.revision if previous else 0
            if actual != expected_revision:
                raise RevisionConflictError("video-end-frame", expected_revision, actual)
            asset = session.get(ManagedAssetRow, asset_id) if asset_id else None
            if asset_id is not None and (asset is None or asset.project_id != project_id):
                raise InvalidTransitionError("ending frame must be a managed asset in this project")
            if asset is not None and asset.mime_type not in {"image/png", "image/jpeg"}:
                raise InvalidTransitionError("ending frame must be PNG or JPEG")
            if asset is None and aspect_policy is not None:
                raise InvalidTransitionError("absent ending frame has no aspect treatment")
            if asset is not None and aspect_policy not in {"reject_mismatch", "contain_pad", "cover_center_crop"}:
                raise InvalidTransitionError("ending-frame aspect treatment must be reviewed")
            provenance = [] if asset is None else [
                {"id": item.id, "declaration": item.declaration}
                for item in session.scalars(select(ManagedAssetProvenanceRow).where(
                    ManagedAssetProvenanceRow.asset_id == asset.id,
                ).order_by(ManagedAssetProvenanceRow.created_at, ManagedAssetProvenanceRow.id))
            ]
            if asset is not None and not provenance:
                raise InvalidTransitionError("ending frame has no declared managed-asset provenance")
            row = VideoEndFrameDecisionRow(
                id=new_id(), project_id=project_id, shot_id=shot_id, revision=actual + 1,
                asset_id=asset_id, original_hash=asset.original_hash if asset else None,
                mime_type=asset.mime_type if asset else None,
                width=asset.width if asset else None, height=asset.height if asset else None,
                provenance=provenance,
                aspect_policy=aspect_policy, approval_id=approval_id,
                storyboard_revision=storyboard_revision, source_timing=source,
                created_at=utc_now(),
            )
            session.add(row)
            return self._projection(row)
