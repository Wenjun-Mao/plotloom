"""Portable frozen manifests, execution facts and CAS commands for video batches."""
from copy import deepcopy
from sqlalchemy import select
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ..codec import stable_hash
from ..schema import VideoBatchRow, VideoBatchReceiptRow


class VideoBatches:
    def __init__(self, access):
        self.access = access

    def latest(self, session, project_id):
        return session.scalar(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id)
            .order_by(VideoBatchRow.created_at.desc(), VideoBatchRow.id.desc()).limit(1))

    def retained_job_ids(self, project_id):
        with self.access.read() as session:
            rows = session.scalars(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id))
            return {identifier for row in rows if row.execution.get("authorizedManifestHash")
                for identifier in row.execution.get("jobs", {}).values()}

    def current(self, project_id):
        with self.access.read() as session:
            row = self.latest(session, project_id)
            return self.view(row) if row else None

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
