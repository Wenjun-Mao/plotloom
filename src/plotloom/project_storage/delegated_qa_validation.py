"""Portable QA evidence admission; retained facts never create runtime grants."""
import json
from typing import Literal

from ..delegated_qa import (
    attribution_for_reviewer,
    direction_attribution,
    keyframe_attribution,
    require_scope,
)
from ..delegated_qa_video import assert_snapshot
from ..exceptions import InvalidTransitionError
from .format import ProjectStorageCorruptionError


def assert_delegated_qa_contracts(
    connection,
    *,
    batch_layout: Literal["current", "prior_without_video_batches"] = "current",
):
    try:
        if batch_layout not in {"current", "prior_without_video_batches"}:
            raise ValueError("unsupported delegated QA batch layout")
        approvals = {}
        for identifier, project, digest, reviewer in connection.execute(
                "SELECT id,project_id,content_hash,reviewer FROM v2_approval_decisions"):
            actor = attribution_for_reviewer(project, reviewer)
            if actor and require_scope(project, actor).storyboard_hash != digest:
                raise ValueError("QA approval storyboard changed")
            approvals[identifier] = (project, actor)
        intents = {}
        for identifier, project, asset_id, raw in connection.execute("SELECT id,project_id,asset_id,intent FROM v2_visual_intents"):
            intent = json.loads(raw)
            actor = intent.get("attribution")
            if actor:
                scope = require_scope(project, actor)
                material = next((item for item in scope.materials if item.asset_id == asset_id), None)
                asset = connection.execute("SELECT original_hash FROM v2_managed_assets WHERE id=? AND project_id=?", (asset_id, project)).fetchone()
                if material is None or asset != (material.original_hash,) or intent.get("role") != "shot_keyframe":
                    raise ValueError("QA visual intent exceeds its granted material")
            intents[identifier] = (project, asset_id, actor)
        for project, shot, asset, approval, intent_id in connection.execute(
                "SELECT project_id,shot_id,asset_id,approval_id,visual_intent_id FROM v2_reviewed_shot_bindings"):
            intent = intents.get(intent_id)
            approved = approvals.get(approval)
            if intent is None or approved is None:
                continue  # General relationship admission remains with its existing owner.
            actor = intent[2]
            if actor != approved[1]:
                raise ValueError("QA material and storyboard attribution differ")
            if actor:
                scope = require_scope(project, actor)
                if intent[:2] != (project, asset) or approved[0] != project or not any(
                        item.shot_id == shot and item.asset_id == asset for item in scope.materials):
                    raise ValueError("QA reviewed binding exceeds its exact shot scope")
        qa_jobs = {}
        if batch_layout == "current":
            for project, raw in connection.execute("SELECT project_id,execution FROM v2_video_batches"):
                execution = json.loads(raw)
                if "reviewAttribution" not in execution:
                    continue
                actor = execution["reviewAttribution"]
                require_scope(project, actor)
                for job_id in execution["jobs"].values():
                    expected = (project, actor)
                    if job_id in qa_jobs and qa_jobs[job_id] != expected:
                        raise ValueError("QA job has conflicting batch attribution")
                    qa_jobs[job_id] = expected
        jobs = {}
        for identifier, project, raw in connection.execute("SELECT id,project_id,snapshot FROM v2_video_jobs"):
            snapshot = json.loads(raw)
            frame_actor = keyframe_attribution(snapshot)
            actor = direction_attribution(snapshot)
            approval_id = snapshot.get("approvalId") if isinstance(snapshot, dict) else None
            approval = approvals.get(approval_id) if isinstance(approval_id, str) else None
            if (actor is not None or frame_actor is not None or identifier in qa_jobs
                    or approval is not None and approval[1] is not None):
                scope = require_scope(project, actor)
                if frame_actor != actor or approval != (project, actor) or qa_jobs.get(identifier) != (project, actor):
                    raise ValueError("QA video source or review attribution differs")
                assert_snapshot(scope, snapshot)
            jobs[identifier] = (project, actor)
        for job_id, reviewer in connection.execute("SELECT video_job_id,reviewer FROM v2_video_reviews"):
            project, expected = jobs[job_id]
            if attribution_for_reviewer(project, reviewer) != expected:
                raise ValueError("QA video review attribution changed")
    except (ValueError, TypeError, KeyError, InvalidTransitionError) as error:
        raise ProjectStorageCorruptionError("persisted delegated QA evidence is invalid") from error
