"""Exact-geometry keyframe adaptation acceptance under the current image contract."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from tests.project_folder_image_delivery_fixtures import png, ready_exported_job


def test_keyframe_adaptation_accepts_frozen_geometry_and_keeps_source_selected(
    tmp_path: Path,
) -> None:
    client, project_id, original_job, _delivery = ready_exported_job(tmp_path)
    try:
        storyboard = client.get(f"/api/v2/projects/{project_id}/stages").json()[
            "stages"
        ][-1]
        shot = storyboard["payload"]["shots"][0]
        approval_id = original_job["request"]["frozenSnapshot"]["approvalId"]
        source = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={
                "image": (
                    "wide.png",
                    png((30, 70, 120), width=640, height=360),
                    "image/png",
                )
            },
            data={
                "origin": "wide source fixture",
                "rights": "unknown",
                "declared_additions_json": "[]",
            },
        )
        assert source.status_code == 201, source.text
        intent_draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot['id']}:{source.json()['id']}",
                "baseCanonicalRevision": storyboard["head"]["revision"],
                "expectedDraftRevision": 0,
                "payload": {
                    "assetId": source.json()["id"],
                    "shotId": shot["id"],
                    "role": "shot_keyframe",
                    "identityIntent": "Keep the source identity.",
                    "sourceRefs": ["fixture"],
                },
            },
        )
        assert intent_draft.status_code == 200, intent_draft.text
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{source.json()['id']}/visual-intents",
            json={
                "shotId": shot["id"],
                "role": "shot_keyframe",
                "identityIntent": "Keep the source identity.",
                "sourceRefs": ["fixture"],
                "consumedDraft": {
                    "editorScope": "visual_intent",
                    "entityId": f"{shot['id']}:{source.json()['id']}",
                    "draftRevision": intent_draft.json()["draftRevision"],
                },
            },
        )
        assert intent.status_code == 201, intent.text
        selected = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={
                "assetId": source.json()["id"],
                "shotId": shot["id"],
                "sceneId": shot["sceneId"],
                "expectedSelectionRevision": 0,
                "storyboardRevision": storyboard["head"]["revision"],
                "approvalId": approval_id,
                "compatibilityNote": "Creator reviewed the landscape source.",
                "visualIntentId": intent.json()["id"],
                "visualIntentRevision": intent.json()["revision"],
            },
        )
        assert selected.status_code == 201, selected.text

        profile_id = "minimax_h3_quality1_portrait_576x1024_v1"
        presentation_change = "Recompose for the frozen portrait frame."
        entity_id = f"{shot['id']}:keyframe_adaptation:{profile_id}"
        direction = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "image_direction",
                "entityId": entity_id,
                "baseCanonicalRevision": storyboard["head"]["revision"],
                "expectedDraftRevision": 0,
                "payload": {
                    "shotId": shot["id"],
                    "targetId": f"keyframe_adaptation:{profile_id}",
                    "contextId": "geometry-acceptance-fixture",
                    "presentationChange": presentation_change,
                },
            },
        )
        assert direction.status_code == 200, direction.text
        prepared = client.post(
            f"/api/v2/projects/{project_id}/image-jobs",
            json={
                "approvalId": approval_id,
                "shotId": shot["id"],
                "storyboardRevision": storyboard["head"]["revision"],
                "contractVersion": 3,
                "keyframeAdaptationProfileId": profile_id,
                "presentationChange": presentation_change,
                "contextId": "geometry-acceptance-fixture",
                "consumedDraft": {
                    "editorScope": "image_direction",
                    "entityId": entity_id,
                    "draftRevision": direction.json()["draftRevision"],
                },
            },
        )
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()["job"]
        request = job["request"]
        frozen = request["frozenSnapshot"]["keyframeAdaptation"]
        assert request["kind"] == "keyframe_adaptation"
        assert frozen["sourceBindingId"] == selected.json()["id"]
        assert frozen["sourceOriginalHash"] == source.json()["originalHash"]
        assert frozen["outputContract"] == {
            "width": 576,
            "height": 1024,
            "mimeTypes": ["image/jpeg", "image/png"],
        }
        assert [item["role"] for item in request["frozenSnapshot"]["references"]] == [
            "source_keyframe"
        ]

        copied = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/copy"
        )
        assert copied.status_code == 200, copied.text
        package_path = Path(copied.json()["packagePath"])
        delivery = Path(copied.json()["deliveryPath"])
        package_request = json.loads(
            (package_path / "request.json").read_text(encoding="utf-8")
        )
        assert package_request["packageVersion"] == 6
        assert package_request["nativeTaskBinding"] == {"mode": "current_task"}
        assert package_request["references"][0]["role"] == "source_keyframe"
        assert "complete 576x1024 composition" in package_request["deliveryInstruction"]

        native_task_id = "00000000-0000-4000-8000-000000000001"
        preflight = request["specialistPreflight"]
        provenance = {
            "codeRevision": "a" * 40,
            "skillVersion": preflight["skillVersion"],
            "skillHash": "b" * 64,
        }
        delivery.mkdir()
        (delivery / "executor-pin.json").write_text(
            json.dumps(
                {
                    "jobId": job["id"],
                    "requestHash": job["requestHash"],
                    "executionContract": preflight["executionContract"],
                    "nativeTaskId": native_task_id,
                    **provenance,
                }
            ),
            encoding="utf-8",
        )
        content = png((40, 90, 120), width=576, height=1024)
        (delivery / "outputs").mkdir()
        (delivery / "outputs" / "adapted.png").write_bytes(content)
        manifest = {
            "schemaVersion": 3,
            "jobId": job["id"],
            "requestHash": job["requestHash"],
            "deliveryId": "exact-geometry",
            "actualPrompt": "Adapt the frozen reviewed keyframe.",
            "outputs": [
                {
                    "filename": "adapted.png",
                    "sha256": sha256(content).hexdigest(),
                    "role": "keyframe_adaptation",
                }
            ],
            "toolEvidence": {
                "tool": "codex_imagegen",
                "nativeTaskId": native_task_id,
                "imageGenExecutionId": "exec-geometry-acceptance-fixture",
                "available": True,
            },
            "executorProvenance": provenance,
            "limitations": ["offline fixture bytes only"],
        }
        (delivery / "completion.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        accepted = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh"
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["state"] == "accepted"
        candidate = accepted.json()["candidates"][0]
        assert candidate["role"] == "keyframe_adaptation"
        assert candidate["assetId"] != source.json()["id"]
        workbench = client.get(
            f"/api/v2/projects/{project_id}/visual-workbench"
        ).json()
        assert workbench["reviewedKeyframes"][0]["assetId"] == source.json()["id"]
        assert workbench["selectionRevision"] == selected.json()["selectionRevision"]
    finally:
        client.close()
