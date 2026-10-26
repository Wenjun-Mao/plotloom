"""Missing-only all-route inventory and exact source/settings preflight."""
from secrets import randbits

from plotloom.stage_contracts import StageName
from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash
from .persistence.project.autopilot_closure import material_closure
from .project_storage.project_video import ProjectVideoRepository
from .provider_budgets import exceeds_budget
from .video_backends.minimax_h3.adapter import H3_QUALIFIED_DURATION_FRAMES
from .video_provider import VideoProviderError


def source_binding(store):
    project_id = store.manifest.project_id
    with store.repository._read() as session:
        return material_closure(session, project_id)


def current_approval(store):
    project_id = store.manifest.project_id
    for decision in reversed(store.authoring.list_approval_decisions(project_id)):
        if decision.decision == "approve" and store.authoring.get_approval_closure(decision.id).active:
            return decision
    raise InvalidTransitionError("approve the current storyboard and material before video batch setup")


def prepare_args(store, shot, approval, setup, *, seed):
    units = shot.duration_units
    if units <= 0 or units * 24 % 1000:
        raise InvalidTransitionError(f"{shot.id}: authored duration is not frame-exact at 24 fps")
    duration = next((seconds for seconds,frames in sorted(H3_QUALIFIED_DURATION_FRAMES.items()) if frames * 1000 >= units * 24), None)
    if duration is None:
        raise InvalidTransitionError(f"{shot.id}: no qualified source duration covers this shot")
    return {"approval_id": approval.id, "shot_id": shot.id, "storyboard_revision": approval.subject_revision,
        "expected_selection_revision": store.media.visual_selection_revision(store.manifest.project_id),
        "idempotency_key": "batch-preview-" + shot.id, "requested_seconds": duration,
        "resolution": None, "audio": True, "aspect_policy": setup.aspect_policy,
        "allow_letterbox": setup.aspect_policy == "contain_pad", "allow_center_crop": setup.aspect_policy == "cover_center_crop",
        "seed": seed, "profile_id": setup.profile_id,
        "playback_intent": "source_exact" if H3_QUALIFIED_DURATION_FRAMES[duration]*1000 == units*24 else "segment_required"}


def inventory(store, video, setup, *, rejected_history=()):
    project_id = store.manifest.project_id
    video._repository(store).assert_video_authority(project_id)
    approval = current_approval(store)
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    jobs = video.jobs(store)
    from sqlalchemy import select

    from .persistence.schema import VideoCandidateSelectionRow
    with store.repository._read() as session:
        selection_revisions = {row.shot_id: row.revision for row in session.scalars(select(VideoCandidateSelectionRow).where(VideoCandidateSelectionRow.project_id == project_id))}
    kept, targets, blockers = [], [], []
    seen = set()
    for shot in board.shots:
        if shot.id in seen:
            continue
        seen.add(shot.id)
        excluded = {fact["jobId"] for fact in rejected_history if fact["shotId"] == shot.id}
        retained = [job for job in jobs if job["snapshot"].get("shot", {}).get("id") == shot.id and job["id"] not in excluded]
        selected = [job for job in retained if job["selected"] and job.get("playbackSegment")]
        if len(selected) == 1:
            job = selected[0]
            storage = ProjectVideoRepository(store, video._application).get_selected_playback_storage(project_id, job["id"])
            store.artifacts.get(storage["uri"])
            kept.append({"shotId": shot.id, "jobId": job["id"], "selectionRevision": job["selectionRevision"],
                "segmentId": job["playbackSegment"]["id"], "derivativeHash": storage["hash"]})
            continue
        if len(retained) > 1 or any(not job["current"] or job["state"] not in {"prepared", "submitted", "retrieve_needed", "ingested"}
                or job.get("reviews") and job["reviews"][-1]["decision"] == "reject" for job in retained):
            blockers.append({"shotId": shot.id, "message": "已有冲突、过期、拒绝或不确定的视频任务；请在手动制作中处理原任务。"})
            continue
        job = retained[0] if retained else None
        seed = job["snapshot"]["request"].get("seed") if job else randbits(63)
        try:
            args = prepare_args(store, shot, approval, setup, seed=seed)
            if job and job["state"] in {"ingested", "submitted", "retrieve_needed"}:
                from .video_backends.minimax_h3.directions import direction_sources
                frozen = {key: value for key,value in job["snapshot"].items() if key not in {"reviewedDirections", "compiledPrompt"}}
                request = frozen["request"]
                args = args | {"requested_seconds": request["durationSeconds"], "profile_id": request["profileId"],
                    "resolution": request["resolution"], "audio": request["audio"], "aspect_policy": request["aspectPolicy"],
                    "allow_letterbox": request["allowLetterbox"], "allow_center_crop": request["allowCenterCrop"],
                    "playback_intent": frozen["playbackIntent"]}
                preview = direction_sources(frozen) | {"snapshot": frozen}
            else:
                preview = video.prepare(store, **args, reviewed_directions=None, preview_only=True)
                if job:
                    frozen = {key: value for key,value in job["snapshot"].items() if key not in {"reviewedDirections", "compiledPrompt"}}
                    if stable_hash(frozen) != preview["sourceHash"]:
                        raise InvalidTransitionError("existing prepared task differs from the displayed batch profile, timing or source")
            mode = {"prepared": "prepared", "submitted": "observe", "retrieve_needed": "observe", "ingested": "reuse"}.get(job["state"], "generate") if job else "generate"
            targets.append({"shotId": shot.id, "title": shot.title, "mode": mode, "jobId": job["id"] if job else None,
                "selectionRevision": selection_revisions.get(shot.id, 0),
                "sourceHash": preview["sourceHash"], "sources": preview["sources"], "snapshot": preview["snapshot"],
                "args": args, "directions": {key: value for key,value in job["snapshot"]["reviewedDirections"].items() if key in {"sourceHash", "fields"}} if job else None, "compiledPrompt": job["snapshot"]["compiledPrompt"] if job else None,
                "authoredDurationUnits": shot.duration_units, "requestedSeconds": args["requested_seconds"],
                "requestedFrames": preview["snapshot"]["request"]["frameCount"]})
        except (InvalidTransitionError, ValueError, VideoProviderError) as error:
            blockers.append({"shotId": shot.id, "message": str(error)})
    new_targets = [item for item in targets if item["mode"] in {"generate", "prepared"}]
    seconds = sum(item["requestedSeconds"] for item in new_targets)
    if exceeds_budget(len(new_targets), setup.max_jobs) or exceeds_budget(seconds, setup.max_requested_seconds):
        blockers.append({"shotId": "", "message": "完整清单超过本次任务或请求秒数上限；未发送视频任务。"})
    return {"version": "video-batch.manifest.v1", "projectId": project_id, "sourceBinding": source_binding(store),
        "setup": setup.model_dump(mode="json", by_alias=True), "scopeShotIds": sorted(seen), "kept": kept,
        "targets": targets, "blockers": blockers, "newJobs": len(new_targets), "requestedSeconds": seconds,
        "maxConcurrentJobs": 1, "attemptsPerTarget": 1, "nativeAudio": True, "monetaryEstimate": None,
        "backend": video._configured_backend_binding().snapshot()}


def validate_manifest(store, video, manifest, *, compiled=True, links=None):
    if manifest["blockers"]:
        raise InvalidTransitionError("resolve every batch preflight exception first")
    if source_binding(store) != manifest["sourceBinding"] or video._configured_backend_binding().snapshot() != manifest["backend"]:
        raise InvalidTransitionError("batch sources or backend changed; inspect a fresh manifest")
    scope = sorted({shot.id for shot in store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD).shots})
    if scope != manifest["scopeShotIds"]:
        raise InvalidTransitionError("all-route batch scope changed")
    if len(manifest["kept"]) + len(manifest["targets"]) != len(scope):
        raise InvalidTransitionError("batch does not cover the complete unique production scope")
    from .video_batch_work_inventory import assert_work_inventory
    with store.repository._read() as session:
        assert_work_inventory(session, store.manifest.project_id, manifest, links or {})
    for target in manifest["targets"]:
        if target["mode"] in {"observe", "reuse"}:
            job = next((job for job in video.jobs(store) if job["id"] == target["jobId"]), None)
            if not job or not job["current"]:
                raise InvalidTransitionError("existing observed/reused task is no longer current")
            frozen = {key: value for key,value in job["snapshot"].items() if key not in {"reviewedDirections", "compiledPrompt"}}
            current_source_hash = stable_hash(frozen)
        else:
            preview = video.prepare(store, **target["args"], reviewed_directions=None, preview_only=True)
            current_source_hash = preview["sourceHash"]
        if current_source_hash != target["sourceHash"]:
            raise InvalidTransitionError(f"{target['shotId']}: batch source or settings changed")
        if compiled:
            from .video_backends.minimax_h3.prompt import compile_i2va_prompt
            if target["directions"] is None or compile_i2va_prompt(target["snapshot"], target["directions"], draft=True) != target["compiledPrompt"]:
                raise InvalidTransitionError("batch English directions have not been completely prepared")
    planned = [target for target in manifest["targets"] if target["mode"] in {"generate", "prepared"}]
    if manifest["newJobs"] != len(planned) or manifest["requestedSeconds"] != sum(target["requestedSeconds"] for target in planned):
        raise InvalidTransitionError("frozen batch workload counts differ from its exact targets")
    setup = manifest["setup"]
    if exceeds_budget(manifest["newJobs"], setup["maxJobs"]) or exceeds_budget(manifest["requestedSeconds"], setup["maxRequestedSeconds"]):
        raise InvalidTransitionError("batch workload exceeds frozen limits")
