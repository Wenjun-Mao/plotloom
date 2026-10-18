"""Explicit native window preparation updates an unconfirmed batch proposal."""
from copy import deepcopy
from ...domain import utc_now
from ...video_batch_basis import batch_for_job


def bind_current_proposal(session, segment):
    batch = batch_for_job(session, segment.project_id, segment.video_job_id)
    if batch is None or batch.state in {"approved", "retired", "cancelled"}:
        return
    execution = deepcopy(batch.execution)
    execution["segments"][segment.shot_id] = segment.id
    batch.execution = execution
    batch.revision += 1
    batch.updated_at = utc_now()
    session.flush()
