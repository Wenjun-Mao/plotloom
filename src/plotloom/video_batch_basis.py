"""Shared exact batch-direction authority at preparation and dispatch readers."""
import re
from .provider_budgets import exceeds_budget
from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash
from .persistence.schema import VideoBatchRow
from .video_batch_operator import intent_authorization


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
        and basis.get("version") in {"whole-batch-english.v1", "production-intent.v2"}
        and all(isinstance(basis.get(key), str) and basis[key] for key in ("batchId", "shotId"))
        and isinstance(basis.get("manifestHash"), str) and re.fullmatch(r"[a-f0-9]{64}", basis["manifestHash"]))


def authorized_directions(view, target):
    """Read projection for the manual API; never creates consent or checks."""
    if (view["execution"].get("intentReviewVersion") != "production-intent.v2"
            or view["execution"].get("authorizedManifestHash") != view["manifestHash"]
            or not target.get("directions") or not target["directions"].get("fidelityCheck")):
        return None
    from hashlib import sha256
    basis = {"version": "production-intent.v2", "batchId": view["id"],
        "manifestHash": view["manifestHash"], "shotId": target["shotId"]}
    if view["execution"].get("reviewAttribution"):
        basis["attribution"] = view["execution"]["reviewAttribution"]
    return target["directions"] | {"reviewBasis": basis,
        "intentAuthorization": intent_authorization(view["projectId"], view["execution"], target["productionBrief"]["briefHash"]),
        "promptSha256": sha256(target["compiledPrompt"].encode()).hexdigest()}


def assert_direction_basis(session, snapshot):
    """Validate retained English endorsement, independent of execution ownership."""
    package = snapshot.get("reviewedDirections") or {}
    basis = package.get("reviewBasis")
    if basis is None:
        if package.get("fidelityCheck") or package.get("intentAuthorization"):
            raise InvalidTransitionError("新制作指令缺少已保存的生成授权。")
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
            or target["directions"] != {key: value for key,value in package.items() if key not in {"reviewBasis", "promptSha256", "intentAuthorization"}}
            or target["compiledPrompt"] != snapshot.get("compiledPrompt")):
        raise InvalidTransitionError("batch directions or compiled prompt changed")
    frozen = {key: value for key,value in snapshot.items() if key not in {"reviewedDirections", "compiledPrompt", "executionRetry"}}
    if stable_hash(frozen) != target["sourceHash"]:
        raise InvalidTransitionError("batch source lineage changed")
    if basis["version"] == "production-intent.v2":
        from .production_brief import production_brief
        from .video_fidelity import assert_target_fidelity
        expected = intent_authorization(row.project_id, row.execution, production_brief(frozen)["briefHash"])
        if (row.manifest.get("version") != "video-batch.manifest.v2"
                or row.execution.get("intentReviewVersion") != "production-intent.v2"
                or package.get("intentAuthorization") != expected
                or target.get("productionBrief") != production_brief(frozen)):
            raise InvalidTransitionError("制作简报或生成授权已变化。")
        assert_target_fidelity(session, row.project_id, target)


def assert_new_dispatch_authority(snapshot):
    if snapshot.get("provider", {}).get("adapterId") != "minimax_h3_gateway":
        return
    package = snapshot.get("reviewedDirections") or {}
    if ((package.get("reviewBasis") or {}).get("version") != "production-intent.v2"
            or not package.get("fidelityCheck") or not package.get("intentAuthorization")
            or package.get("reviewedEnglish")):
        raise InvalidTransitionError("旧英文审阅记录仅保留原有证据；新派发需要独立保真检查及制作意图授权。")


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
    if target.get("existingJobIds"):
        existing = session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(target["existingJobIds"]))).all()
        if any(job.state in {"dispatching", "submitted", "retrieve_needed", "outcome_unknown"} for job in existing):
            raise InvalidTransitionError("原任务尚有未解决的派发；禁止发送新的单镜头候选。")
    selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": target["shotId"]})
    if (selection.revision if selection else 0) != target["selectionRevision"]:
        raise InvalidTransitionError("batch target playback selection changed")
    links = row.execution["jobs"]
    pending = session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(list(links.values())))).all()
    if any(job.id != video_job_id and (job.state in {"dispatching", "submitted", "retrieve_needed"} or job.state == "outcome_unknown" and not (job.observed or {}).get("localExecutionStopped")) for job in pending):
        raise InvalidTransitionError("one-concurrent-job batch has an unsettled existing submission")
    capped_ids = {links[item["shotId"]] for item in manifest["targets"] if item["mode"] in {"generate", "prepared"} and item["shotId"] in links}
    capped_ids |= {identifier for ids in row.execution.get("retryHistory", {}).values() for identifier in ids}
    claimed = session.scalars(select(ProjectVideoDispatchRow).where(ProjectVideoDispatchRow.video_job_id.in_(capped_ids))).all()
    spent = {claim.video_job_id for claim in claimed}
    jobs = {job.id: job for job in session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(capped_ids)))}
    candidate = jobs.get(video_job_id)
    if candidate is None or candidate.snapshot.get("compiledPrompt") != target["compiledPrompt"]:
        raise InvalidTransitionError("adopted batch prompt differs from the displayed manifest")
    additional = 0 if video_job_id in spent else 1
    seconds = sum(jobs[identifier].requested_seconds for identifier in spent) + (candidate.requested_seconds if additional else 0)
    if exceeds_budget(len(spent) + additional, manifest["setup"]["maxJobs"]) or exceeds_budget(seconds, manifest["setup"]["maxRequestedSeconds"]):
        raise InvalidTransitionError("batch dispatch cap is exhausted")
