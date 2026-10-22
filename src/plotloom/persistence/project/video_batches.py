"""Portable frozen manifests, execution facts and CAS commands for video batches."""
from copy import deepcopy
from sqlalchemy import select
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..codec import stable_hash
from ..schema import VideoBatchRow, VideoBatchReceiptRow, VideoJobRow, VideoReviewRow


class VideoBatches:
    def __init__(self, access):
        self.access = access

    def latest(self, session, project_id):
        return session.scalar(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id)
            .order_by(VideoBatchRow.created_at.desc(), VideoBatchRow.id.desc()).limit(1))

    def _known_predictions(self, session, project_id):
        rows = session.scalars(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id))
        identifiers = {identifier for row in rows if row.execution.get("authorizedManifestHash")
            for identifier in row.execution.get("jobs", {}).values()}
        return list(session.scalars(select(VideoJobRow.id).where(VideoJobRow.project_id == project_id,
            VideoJobRow.id.in_(identifiers), VideoJobRow.state.in_(("submitted", "retrieve_needed"))))) if identifiers else []

    def known_prediction_ids(self, project_id):
        with self.access.read() as session:
            return self._known_predictions(session, project_id)

    def job_states(self, project_id, identifiers):
        with self.access.read() as session:
            return dict(session.execute(select(VideoJobRow.id, VideoJobRow.state).where(
                VideoJobRow.project_id == project_id, VideoJobRow.id.in_(identifiers))).all()) if identifiers else {}

    def needs_step(self, project_id):
        """Cheap work predicate; never grants dispatch or proves source authority."""
        with self.access.read() as session:
            row = self.latest(session, project_id)
            if row is None:
                return False
            draft = row.execution.get("draft")
            unsettled_draft = draft and draft["attempt"]["state"] not in {"completed", "failed", "settled"}
            return bool(row.state in {"running", "drafting"} or unsettled_draft or self._known_predictions(session, project_id))

    def current(self, project_id):
        with self.access.read() as session:
            row = self.latest(session, project_id)
            if row is None:
                return None
            from ...workflow_timing import timing_projection
            receipt = session.scalar(select(VideoBatchReceiptRow).where(VideoBatchReceiptRow.batch_id == row.id))
            timing = timing_projection(row.created_at, terminal=row.state in {"approved", "cancelled", "retired", "stale"},
                milestone="完整视频审阅已保存" if receipt else None,
                milestone_at=receipt.created_at if receipt else None,
                completed_at=receipt.created_at if receipt and row.state == "approved" else None)
            rejected = []
            for fact in row.manifest.get("rejectedHistory", []):
                review = session.get(VideoReviewRow, fact["rejectionId"])
                if review is None or review.video_job_id != fact["jobId"] or review.decision != "reject":
                    raise InvalidTransitionError("retained rejected take observation changed")
                rejected.append({"shotId": fact["shotId"], "jobId": fact["jobId"], "reason": review.note})
            return self.view(row) | {"timing": timing.model_dump(mode="json", by_alias=True), "rejectedTakes": rejected}

    @staticmethod
    def view(row):
        if stable_hash(row.manifest) != row.manifest_hash:
            raise InvalidTransitionError("video batch manifest is corrupt")
        return {"id": row.id, "projectId": row.project_id, "revision": row.revision,
            "state": row.state, "controlRevision": row.execution["controlRevision"], "manifest": deepcopy(row.manifest), "manifestHash": row.manifest_hash,
            "execution": deepcopy(row.execution)}

    def create(self, project_id, manifest):
        with self.access.lifecycle_write() as session:
            existing = self.latest(session, project_id)
            if existing and existing.state not in {"approved", "cancelled", "retired"}:
                return self.view(existing)
            now = utc_now()
            row = VideoBatchRow(id=new_id(), project_id=project_id, revision=1, state="setup",
                manifest=manifest, manifest_hash=stable_hash(manifest), execution={"jobs": {}, "segments": {}, "controlRevision": 1},
                created_at=now, updated_at=now)
            session.add(row)
            session.flush()
            return self.view(row)

    def change(self, project_id, batch_id, *, expected_revision=None, control=False, mutate):
        with self.access.lifecycle_write() as session:
            row = session.get(VideoBatchRow, batch_id)
            if row is None or row.project_id != project_id:
                raise InvalidTransitionError("video batch not found")
            self.view(row)
            if expected_revision is not None and row.revision != expected_revision:
                raise RevisionConflictError("video-batch", expected_revision, row.revision)
            # JSON values are assigned anew; nested changes cannot evade SQLAlchemy.
            row.execution, row.manifest = deepcopy(row.execution), deepcopy(row.manifest)
            mutate(row)
            if control:
                row.execution = row.execution | {"controlRevision": row.execution["controlRevision"] + 1}
            row.manifest_hash = stable_hash(row.manifest)
            row.revision += 1
            row.updated_at = utc_now()
            session.flush()
            return self.view(row)

    def receipt(self, batch_id):
        with self.access.read() as session:
            row = session.scalar(select(VideoBatchReceiptRow).where(VideoBatchReceiptRow.batch_id == batch_id))
            if row is None:
                return None
            if stable_hash(row.receipt) != row.receipt_hash:
                raise InvalidTransitionError("video pack receipt is corrupt")
            return deepcopy(row.receipt)
