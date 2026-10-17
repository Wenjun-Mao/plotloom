"""Manual image preparation and exact draft-source selection."""
from fastapi import status

from .models import ProjectFolderImageJobCreateRequest


def register_image_prepare_route(app, opened_project, image_job_target_id, require_media_draft_scope, project_h3_target):
    @app.post("/api/v2/projects/{project_id}/image-jobs", status_code=status.HTTP_201_CREATED)
    def prepare_project_image_job(project_id: str, body: ProjectFolderImageJobCreateRequest) -> dict:
        target_id = image_job_target_id(body)
        require_media_draft_scope(body.consumed_draft, required_scope="image_direction",
            required_entity_id=f"{body.shot_id}:{target_id}")
        draft_payload = {"shotId": body.shot_id, "targetId": target_id,
            "contextId": body.context_id, "presentationChange": body.presentation_change}
        adaptation = ({"targetProfile": project_h3_target(body.keyframe_adaptation_profile_id)}
            if body.keyframe_adaptation_profile_id is not None else None)
        with opened_project(project_id) as store:
            return store.media.prepare_image_job(project_id, approval_id=body.approval_id, shot_id=body.shot_id,
                storyboard_revision=body.storyboard_revision, parent_candidate_asset_id=body.parent_candidate_asset_id,
                scene_continuity_binding_id=body.scene_continuity_binding_id, keyframe_adaptation=adaptation,
                presentation_change=body.presentation_change, contract_version=body.contract_version,
                consumed_draft=(body.consumed_draft.entity_id, body.consumed_draft.draft_revision, draft_payload))
