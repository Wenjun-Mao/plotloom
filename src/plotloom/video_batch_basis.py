"""Shared exact batch-direction authority at preparation and dispatch readers."""
import re
from .provider_budgets import exceeds_budget
from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash
from .persistence.schema import VideoBatchRow


def valid_direction_endorsement(package):
    basis = package.get("reviewBasis")
    keys = {"version", "batchId", "manifestHash", "shotId"}
    if isinstance(basis, dict) and "attribution" in basis:
        from .delegated_qa_contracts import AgentQaAttribution
        try:
            AgentQaAttribution.model_validate(basis["attribution"])
        except ValueError:
            return False
        keys.add("attribution")
    return bool(isinstance(basis, dict) and set(basis) == keys
        and basis.get("version") == "whole-batch-english.v1"
        and all(isinstance(basis.get(key), str) and basis[key] for key in ("batchId", "shotId"))
        and isinstance(basis.get("manifestHash"), str) and re.fullmatch(r"[a-f0-9]{64}", basis["manifestHash"]))


def assert_direction_basis(session, snapshot):
    """Validate retained English endorsement, independent of execution ownership."""
    package = snapshot.get("reviewedDirections") or {}
    basis = package.get("reviewBasis")
    if basis is None:
        return
    if not valid_direction_endorsement(package):
        raise InvalidTransitionError("invalid batch English endorsement")
    row = session.get(VideoBatchRow, basis["batchId"])
    if (row is None or stable_hash(row.manifest) != row.manifest_hash
            or row.manifest_hash != basis["manifestHash"]
            or row.execution.get("authorizedManifestHash") != row.manifest_hash):
        raise InvalidTransitionError("batch English endorsement has no exact retained authorization")
    if basis.get("attribution") != row.execution.get("reviewAttribution"):
        raise InvalidTransitionError("batch English attribution changed")
    targets = [item for item in row.manifest["targets"] if item["shotId"] == basis["shotId"]]
    if len(targets) != 1:
        raise InvalidTransitionError("batch endorsement target is not in the manifest")
    target = targets[0]
    if (target["snapshot"]["shot"]["id"] != snapshot["shot"]["id"]
            or target["directions"] != {key: value for key,value in package.items() if key not in {"reviewBasis", "promptSha256"}}
            or target["compiledPrompt"] != snapshot.get("compiledPrompt")):
        raise InvalidTransitionError("batch directions or compiled prompt changed")
    frozen = {key: value for key,value in snapshot.items() if key not in {"reviewedDirections", "compiledPrompt"}}
    if stable_hash(frozen) != target["sourceHash"]:
        raise InvalidTransitionError("batch source lineage changed")


def batch_for_job(session, project_id, video_job_id):
    """Adoption fences the existing job without rewriting its reviewed snapshot."""
    from sqlalchemy import select
    rows = session.scalars(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id)
        .order_by(VideoBatchRow.created_at.desc(), VideoBatchRow.id.desc()))
    return next((row for row in rows if video_job_id in row.execution.get("jobs", {}).values()
        and row.execution.get("authorizedManifestHash")), None)


def assert_batch_dispatch_scope(session, project_id, video_job_id):
    from sqlalchemy import select
    from .persistence.schema import VideoJobRow, VideoCandidateSelectionRow, ProjectVideoDispatchRow
    from .persistence.project.autopilot_closure import material_closure
    row = batch_for_job(session, project_id, video_job_id)
    if row is None:
        return
    manifest = row.manifest
    if (row.state != "running" or stable_hash(manifest) != row.manifest_hash
            or row.execution["authorizedManifestHash"] != row.manifest_hash
            or material_closure(session, project_id) != manifest["sourceBinding"]):
        raise InvalidTransitionError("batch is paused, cancelled or its exact source authorization changed")
    for fact in manifest["kept"]:
        selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": fact["shotId"]})
        if selection is None or selection.revision != fact["selectionRevision"] or selection.selected_video_job_id != fact["jobId"]:
            raise InvalidTransitionError("kept batch playback selection changed")
    from .video_batch_work_inventory import assert_work_inventory
    assert_work_inventory(session, project_id, manifest, row.execution["jobs"])
    owned = [target for target in manifest["targets"] if row.execution["jobs"].get(target["shotId"]) == video_job_id]
    if len(owned) != 1 or owned[0]["mode"] not in {"generate", "prepared"}:
        raise InvalidTransitionError("batch does not authorize a new submission for this target")
    target = owned[0]
    selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": target["shotId"]})
    if (selection.revision if selection else 0) != target["selectionRevision"]:
        raise InvalidTransitionError("batch target playback selection changed")
    links = row.execution["jobs"]
    pending = session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(list(links.values())))).all()
    if any(job.id != video_job_id and job.state in {"dispatching", "submitted", "retrieve_needed", "outcome_unknown"} for job in pending):
        raise InvalidTransitionError("one-concurrent-job batch has an unsettled existing submission")
    capped_ids = {links[item["shotId"]] for item in manifest["targets"] if item["mode"] in {"generate", "prepared"} and item["shotId"] in links}
    claimed = session.scalars(select(ProjectVideoDispatchRow).where(ProjectVideoDispatchRow.video_job_id.in_(capped_ids))).all()
    spent = {claim.video_job_id for claim in claimed}
    jobs = {job.id: job for job in pending}
    candidate = jobs.get(video_job_id)
    if candidate is None or candidate.snapshot.get("compiledPrompt") != target["compiledPrompt"]:
        raise InvalidTransitionError("adopted batch prompt differs from the displayed manifest")
    additional = 0 if video_job_id in spent else 1
    seconds = sum(jobs[identifier].requested_seconds for identifier in spent) + (candidate.requested_seconds if additional else 0)
    if exceeds_budget(len(spent) + additional, manifest["setup"]["maxJobs"]) or exceeds_budget(seconds, manifest["setup"]["maxRequestedSeconds"]):
        raise InvalidTransitionError("batch dispatch cap is exhausted")
