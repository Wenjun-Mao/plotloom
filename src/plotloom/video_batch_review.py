"""Full-scope review projection and one atomic audiovisual selection receipt."""
from hashlib import sha256
from sqlalchemy import select
from .domain import new_id, utc_now
from .exceptions import InvalidTransitionError, RevisionConflictError, NotFoundError
from .project_storage.format import ProjectStorageError
from .persistence.codec import stable_hash
from .persistence.schema import VideoBatchRow, VideoBatchReceiptRow, VideoSegmentRow
from .project_storage.project_video import ProjectVideoRepository
from .video_batch_inventory import source_binding


def segment_confirmation_valid(session, segment):
    receipt_id = segment.confirmation_receipt_id
    if receipt_id is None:
        return True
    row = session.get(VideoBatchReceiptRow, receipt_id)
    if row:
        from .delegated_qa_video import assert_receipt_actor
        batch = session.get(VideoBatchRow, row.batch_id)
        try:
            if batch is None:
                return False
            assert_receipt_actor(segment.project_id, row.receipt, batch.execution.get("reviewAttribution"))
        except (ValueError, InvalidTransitionError):
            return False
    return bool(row and stable_hash(row.receipt) == row.receipt_hash
        and row.receipt.get("version") == "whole-pack-video-native-audio.v1"
        and any(fact.get("segmentId") == segment.id and fact.get("jobId") == segment.video_job_id
            and fact.get("derivativeHash") == segment.derivative_hash and type(fact.get("selectionRevision")) is int and segment.selected_revision is not None and fact["selectionRevision"] <= segment.selected_revision
            for fact in row.receipt.get("selections", [])))


def review_projection(store, application, view):
    manifest, execution = view["manifest"], view["execution"]
    repository = ProjectVideoRepository(store, application)
    jobs = {item["id"]: item for item in repository.list_video_jobs(view["projectId"])}
    errors, proposals = [], []
    from .video_batch_work_inventory import assert_work_inventory
    try:
        with store.repository._read() as session:
            if view["state"] != "approved":
                assert_work_inventory(session, view["projectId"], manifest, execution["jobs"])
    except InvalidTransitionError:
        errors.append({"shotId": "", "message": "已有视频任务或选择已变化，请核对原任务。"})
    if source_binding(store) != manifest["sourceBinding"]:
        errors.append({"shotId": "", "message": "来源已变化，请处理过期批次。"})
    if view["state"] not in {"awaiting_review", "approved"}:
        errors.append({"shotId": "", "message": "批次尚未全部完成。"})
    for kept in manifest["kept"]:
        job = jobs.get(kept["jobId"])
        if (not job or not job["selected"] or job["selectionRevision"] != kept["selectionRevision"]
                or not job["playbackSegment"] or job["playbackSegment"]["id"] != kept["segmentId"]):
            errors.append({"shotId": kept["shotId"], "message": "保留的视频选择已变化。"})
        else:
            try:
                storage = repository.get_selected_playback_storage(view["projectId"], job["id"])
                if storage["hash"] != kept["derivativeHash"] or sha256(store.artifacts.get(storage["uri"])).hexdigest() != kept["derivativeHash"]:
                    raise ValueError("kept video bytes changed")
            except (OSError, ValueError, NotFoundError, InvalidTransitionError, ProjectStorageError):
                errors.append({"shotId": kept["shotId"], "message": "保留的视频无法读取或字节已变化。"})
    for target in manifest["targets"]:
        shot_id = target["shotId"]
        job_id = execution["jobs"].get(shot_id)
        job = jobs.get(job_id)
        proposal_id = execution["segments"].get(shot_id)
        proposal = next((item for item in job.get("segments", []) if item["id"] == proposal_id), None) if job else None
        reason = None
        if not job or job["state"] != "ingested" or not job["current"]:
            reason = "视频缺失、失败或来源过期。"
        elif job["reviews"] and job["reviews"][-1]["decision"] == "reject":
            reason = "最新审阅已拒绝；须从原任务明确处理。"
        elif view["state"] != "approved" and job["selectionRevision"] != target["selectionRevision"]:
            reason = "视频选择版本已变化。"
        elif not proposal or not proposal["current"]:
            reason = "缺少有效的逐帧播放窗口；请从手动制作调整。"
        else:
            try:
                for storage in (repository.get_video_output_storage(view["projectId"], job_id),
                        repository.get_video_segment_preview_storage(view["projectId"], proposal_id)):
                    if sha256(store.artifacts.get(storage["uri"])).hexdigest() != storage["hash"]:
                        raise ValueError("video bytes changed")
            except (OSError, ValueError, NotFoundError, InvalidTransitionError, ProjectStorageError):
                reason = "视频原片或播放片段无法读取。"
        if reason:
            errors.append({"shotId": shot_id, "message": reason})
        proposals.append({"shotId": shot_id, "title": target["title"], "jobId": job_id,
            "segmentId": proposal_id, "segment": proposal, "job": job, "error": reason})
    bundle = {"batchId": view["id"], "manifestHash": view["manifestHash"], "kept": manifest["kept"],
        "proposals": proposals, "errors": errors}
    return bundle | {"reviewHash": stable_hash(bundle), "ready": not errors,
        "readyCount": sum(not item["error"] for item in proposals), "blockedCount": len(errors)}


def confirm_pack(store, application, view, request):
    owner = store.repository.video_batches
    from .delegated_qa_video import assert_receipt_actor
    actor = request.attribution.model_dump(mode="json", by_alias=True) if request.attribution else {"kind": "unnamed_creator"}
    inspection = {"inspection": request.inspection.model_dump(mode="json", by_alias=True)} if request.inspection else {}
    assert_receipt_actor(view["projectId"], {"attribution": actor, **inspection}, view["execution"].get("reviewAttribution"))
    prior = owner.receipt(view["id"])
    if prior:
        if prior["reviewHash"] != request.review_hash:
            raise InvalidTransitionError("this batch already has a different immutable confirmation")
        if prior["attribution"] != actor or {key: prior[key] for key in inspection if key in prior} != inspection:
            raise InvalidTransitionError("retained final confirmation attribution or observations differ")
        return prior
    with store.repository.manual_command() as session:
        row = session.get(VideoBatchRow, view["id"])
        if row.revision != request.expected_revision:
            raise RevisionConflictError("video-batch", request.expected_revision, row.revision)
        current = owner.view(row)
        if request.attribution:
            from .delegated_qa import require_qa_write
            require_qa_write(session, view["projectId"], request.attribution)
        review = review_projection(store, application, current)
        if not review["ready"] or review["reviewHash"] != request.review_hash:
            raise InvalidTransitionError("complete video review changed or has unresolved exceptions")
        identifier = new_id()
        session.info["pending_video_pack_receipt"] = identifier
        facts = []
        repository = ProjectVideoRepository(store, application)
        try:
            for target, proposal in zip(row.manifest["targets"], review["proposals"], strict=True):
                selected = repository.select_video_segment(view["projectId"], proposal["segmentId"], reviewer=request.attribution or "",
                    note="", expected_selection_revision=target["selectionRevision"])
                facts.append({"shotId": target["shotId"], "jobId": proposal["jobId"], "segmentId": selected["id"],
                    "selectionRevision": selected["selectedRevision"], "derivativeHash": selected["derivativeHash"]})
            receipt = {"id": identifier, "version": request.basis, "batchId": row.id, "projectId": row.project_id,
                "manifestHash": row.manifest_hash, "reviewHash": request.review_hash,
                "attribution": actor, **inspection, "confirmation": {"clips": True, "nativeAudio": True, "intent": True, "windows": True},
                "note": request.note, "kept": row.manifest["kept"], "selections": facts}
            session.add(VideoBatchReceiptRow(id=identifier, batch_id=row.id, receipt=receipt, receipt_hash=stable_hash(receipt), created_at=utc_now()))
            row.state, row.revision, row.updated_at = "approved", row.revision + 1, utc_now()
            session.flush()
            if any(not segment_confirmation_valid(session, session.get(VideoSegmentRow, fact["segmentId"])) for fact in facts):
                raise InvalidTransitionError("whole-pack selection receipt failed shared admission")
            return receipt
        finally:
            session.info.pop("pending_video_pack_receipt", None)
