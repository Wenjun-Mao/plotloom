"""Revalidate missing-only and selection CAS against the live native job inventory."""
from sqlalchemy import select

from .exceptions import InvalidTransitionError
from .persistence.schema import VideoCandidateSelectionRow, VideoJobRow


def assert_work_inventory(session, project_id, manifest, links):
    from .video_batch_replacement import assert_rejected_history, evidence_reader
    assert_rejected_history(evidence_reader(session), project_id, manifest)
    jobs = session.scalars(select(VideoJobRow).where(VideoJobRow.project_id == project_id)).all()
    by_shot = {}
    for job in jobs:
        snapshot = job.snapshot
        shot = snapshot.get("shot") if isinstance(snapshot, dict) else None
        if isinstance(shot, dict):
            by_shot.setdefault(shot.get("id"), []).append(job.id)
    for target in manifest["targets"]:
        identifier = links.get(target["shotId"], target["jobId"])
        existing = target.get("existingJobIds", [])
        if existing and not manifest["setup"].get("singleRequest"):
            raise InvalidTransitionError("preexisting candidates require explicit single-shot authorization")
        expected = existing + ([identifier] if identifier else []) + [fact["jobId"] for fact in manifest.get("rejectedHistory", []) if fact["shotId"] == target["shotId"]]
        # A child may retain only the exact immutable predecessors in its snapshot.
        current = next((job for job in jobs if job.id == identifier), None)
        if current is not None:
            expected += current.snapshot.get("executionRetry", {}).get("predecessorJobIds", [])
        expected.sort()
        if sorted(by_shot.get(target["shotId"], [])) != expected:
            raise InvalidTransitionError(f"{target['shotId']}: existing video work changed; no replacement may be prepared or submitted")
        selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": target["shotId"]})
        if (selection.revision if selection else 0) != target["selectionRevision"]:
            raise InvalidTransitionError("batch video selection changed")
    for fact in manifest["kept"]:
        selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": fact["shotId"]})
        if selection is None or selection.revision != fact["selectionRevision"] or selection.selected_video_job_id != fact["jobId"]:
            raise InvalidTransitionError("kept batch video selection changed")
