"""Explicit H3 reconsideration; QA observation does not mutate selection CAS."""
from datetime import timedelta
from typing import Any

from sqlalchemy import select

from ...contract_identity import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...video_batch_replacement import assert_rejected_take_mutable
from ..codec import _stored_utc, stable_hash
from ..schema import (
    VideoBatchReceiptRow,
    VideoBatchRow,
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoReviewRow,
    VideoSegmentRow,
)
from .autopilot_closure import material_closure


def reopen_rejected_h3_review(
    owner, project_id: str, video_job_id: str, *, reviewer: str, reason: str,
    expected_selection_revision: int, acceptance_basis: str | None = None,
) -> dict[str, Any]:
    """Append explicit reconsideration while preserving current shot playback."""
    from ...delegated_qa import reject_reserved_reviewer, reviewer_for
    from ...delegated_qa_contracts import AgentQaAttribution
    from ...functional_qa import assert_functional_qa
    qa_reviewer = reviewer if isinstance(reviewer, AgentQaAttribution) else None
    actor = qa_reviewer.model_dump(mode="json", by_alias=True) if qa_reviewer else None
    reason = reason.strip()
    if qa_reviewer:
        if acceptance_basis != "functional_workflow_only":
            raise InvalidTransitionError("QA reconsideration requires the explicit functional-only basis")
        assert_functional_qa(project_id, actor)
        reviewer = reviewer_for(qa_reviewer)
    else:
        reviewer = reviewer.strip()
        reject_reserved_reviewer(reviewer)
        if acceptance_basis is not None:
            raise InvalidTransitionError("human reconsideration cannot claim a QA acceptance basis")
    if not reviewer or not reason:
        raise InvalidTransitionError("reopening a rejected H3 take requires a reviewer and reason")

    with owner._access.leases.lifecycle_write() as session:
        job = session.get(VideoJobRow, video_job_id)
        if job is None or job.project_id != project_id:
            raise NotFoundError("video job not found")
        assert_rejected_take_mutable(session, project_id, video_job_id)
        snapshot = job.snapshot
        from ...delegated_qa import direction_attribution
        generation_actor = direction_attribution(snapshot)
        if qa_reviewer:
            from ...delegated_qa import require_qa_write
            require_qa_write(session, project_id, qa_reviewer)
            if generation_actor != actor:
                raise InvalidTransitionError("QA reconsideration requires the exact generation actor")
        elif generation_actor:
            raise InvalidTransitionError("QA rejection cannot be reopened through a human review path")
        provider = snapshot.get("provider") if isinstance(snapshot, dict) else None
        if (
            job.state != "ingested"
            or not isinstance(provider, dict)
            or provider.get("adapterId") != "minimax_h3_gateway"
            or not owner._currentness.video_job_current_in_session(session, job)
        ):
            raise InvalidTransitionError("only a current ingested H3 take can be reopened")

        latest = session.scalar(
            select(VideoReviewRow)
            .where(VideoReviewRow.video_job_id == job.id)
            .order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc())
            .limit(1)
        )
        if latest is None or latest.decision != "reject":
            raise InvalidTransitionError("only the latest rejected H3 review can be reopened")
        if qa_reviewer and latest.reviewer != reviewer:
            raise InvalidTransitionError("QA reconsideration cannot replace a different review actor")

        owner._source(job)
        shot_id = snapshot["shot"]["id"]
        selection = owner._selection(session, project_id, shot_id)
        actual_revision = selection.revision if selection is not None else 0
        if actual_revision != expected_selection_revision:
            raise RevisionConflictError(
                "video-candidate-selection", expected_selection_revision, actual_revision
            )
        if actual_revision < 0:
            raise InvalidTransitionError("video selection revision is invalid")
        if selection is not None and selection.selected_video_job_id == job.id:
            raise InvalidTransitionError("a rejected H3 take cannot remain the selected video job")

        if qa_reviewer:
            _assert_review_only_batch(owner, session, job, actual_revision, selection)
            next_revision = actual_revision
        else:
            next_revision = actual_revision + 1
            if selection is None:
                selection = VideoCandidateSelectionRow(
                    project_id=project_id, shot_id=shot_id,
                    selected_video_job_id=None, revision=next_revision, updated_at=utc_now(),
                )
                session.add(selection)
            else:
                selected_id = selection.selected_video_job_id
                if selected_id is not None:
                    selected_job = session.get(VideoJobRow, selected_id)
                    selected_snapshot = selected_job.snapshot if selected_job is not None else None
                    selected_shot = selected_snapshot.get("shot") if isinstance(selected_snapshot, dict) else None
                    if (
                        selected_job is None
                        or selected_job.project_id != project_id
                        or not isinstance(selected_shot, dict)
                        or selected_shot.get("id") != shot_id
                    ):
                        raise InvalidTransitionError("current video selection is inconsistent")
                    active_segments = session.scalars(
                        select(VideoSegmentRow).where(
                            VideoSegmentRow.project_id == project_id,
                            VideoSegmentRow.shot_id == shot_id,
                            VideoSegmentRow.video_job_id == selected_id,
                            VideoSegmentRow.selected_revision == actual_revision,
                        )
                    ).all()
                    if len(active_segments) > 1:
                        raise InvalidTransitionError("current video selection has multiple active segments")
                    if active_segments:
                        active_segments[0].selected_revision = next_revision
                selection.revision = next_revision
                selection.updated_at = utc_now()

        # Review projection sorts by createdAt and then id. Keep the
        # explicit reopen event after its rejection even within one clock tick.
        created_at = max(
            utc_now(), _stored_utc(latest.created_at) + timedelta(microseconds=1)
        )
        review = VideoReviewRow(
            id=new_id(), video_job_id=job.id, reviewer=reviewer,
            decision="reopen", note=reason, created_at=created_at,
        )
        session.add(review)
        return {
            "id": review.id, "videoJobId": job.id, "reviewer": reviewer,
            "decision": "reopen", "note": reason,
            "createdAt": _stored_utc(created_at).isoformat(),
            "selectionRevision": next_revision,
            **({"attribution": actor, "acceptanceBasis": acceptance_basis} if actor else {}),
        }


def _assert_review_only_batch(owner, session, job, revision, selection):
    """Reconsider one completed unselected take, without dispatch or a CAS waiver."""
    basis = job.snapshot.get("reviewedDirections", {}).get("reviewBasis", {})
    batch = session.get(VideoBatchRow, basis.get("batchId"))
    from .video_batches import VideoBatches
    current = VideoBatches(owner._access).latest(session, job.project_id)
    if (batch is None or batch.project_id != job.project_id
            or current is None or current.id != batch.id
            or basis.get("version") != "production-intent.v2"
            or basis.get("manifestHash") != batch.manifest_hash
            or batch.state not in {"cancelled", "awaiting_review"}
            or stable_hash(batch.manifest) != batch.manifest_hash
            or batch.execution.get("authorizedManifestHash") != batch.manifest_hash
            or batch.execution.get("reviewAttribution") != basis.get("attribution")
            or session.scalar(select(VideoBatchReceiptRow).where(VideoBatchReceiptRow.batch_id == batch.id)) is not None):
        raise InvalidTransitionError("QA reconsideration requires its original complete unconfirmed batch")
    targets = batch.manifest["targets"]
    shot_id = job.snapshot["shot"]["id"]
    if (len(targets) != 1 or targets[0]["shotId"] != shot_id
            or batch.execution.get("jobs") != {shot_id: job.id}
            or shot_id not in batch.execution.get("segments", {})
            or targets[0]["selectionRevision"] != revision
            or selection is not None and selection.selected_video_job_id is not None):
        raise InvalidTransitionError("QA reconsideration cannot change selection or production scope")
    for key in ("draft", "fidelity"):
        data = batch.execution.get(key)
        if data and data["attempt"]["state"] not in {"completed", "failed", "settled"}:
            raise InvalidTransitionError("QA reconsideration cannot cross unresolved native execution")
    if material_closure(session, job.project_id) != batch.manifest["sourceBinding"]:
        raise InvalidTransitionError("QA reconsideration source changed")
    frozen = {key: value for key, value in job.snapshot.items()
        if key not in {"compiledPrompt", "reviewedDirections", "executionRetry"}}
    if stable_hash(frozen) != targets[0]["sourceHash"]:
        raise InvalidTransitionError("QA reconsideration differs from the frozen generation source")
    from ...video_batch_work_inventory import assert_work_inventory
    from ...video_fidelity import assert_target_fidelity
    assert_work_inventory(session, job.project_id, batch.manifest, batch.execution["jobs"])
    assert_target_fidelity(session, job.project_id, targets[0])
