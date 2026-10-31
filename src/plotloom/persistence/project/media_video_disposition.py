"""Protected H3 rejection is separate from optional quality observations."""
from sqlalchemy import select

from ...exceptions import InvalidTransitionError
from ..schema import VideoJobRow, VideoReviewRow


def h3_video_rejection_is_current(session, video_job_id: str) -> bool:
    job = session.get(VideoJobRow, video_job_id)
    snapshot = job.snapshot if job is not None else None
    provider = snapshot.get("provider") if isinstance(snapshot, dict) else None
    if not isinstance(provider, dict) or provider.get("adapterId") != "minimax_h3_gateway":
        return False
    decision = session.scalar(
        select(VideoReviewRow.decision)
        .where(VideoReviewRow.video_job_id == video_job_id)
        .order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc())
        .limit(1)
    )
    return decision == "reject"


def assert_h3_video_not_rejected(session, video_job_id: str) -> None:
    if h3_video_rejection_is_current(session, video_job_id):
        raise InvalidTransitionError(
            "video candidate is explicitly rejected; reopen its disposition before selection"
        )
