"""Offline, source-grounded H3 review packages for fixture-only video tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from plotloom.video_batch_contracts import BatchSetup, BatchControl
from plotloom.video_batch_basis import authorized_directions


_FIXTURE_ENGLISH = {
    "交代选择": "The shot establishes a choice.",
    "角色握紧信件。": "The character tightens their grip on the letter.",
    "稳定推进": "The camera advances steadily.",
}


def reviewed_h3_body(client: TestClient, project_id: str, body: dict, *, directions_fields=None) -> dict:
    body = {"playbackIntent": "segment_required", **body}
    endpoint = f"/api/v2/projects/{project_id}/video-jobs/prompt-preview"
    sources_response = client.post(endpoint, json=body)
    assert sources_response.status_code == 200, sources_response.text
    sources = sources_response.json()
    fields = []
    for source in sources["sources"]:
        path, text = source["path"], source["text"]
        if path == "reviewedSoundscape":
            english = "A soft paper rustle accompanies the visible hand movement."
        elif text in _FIXTURE_ENGLISH:
            english = _FIXTURE_ENGLISH[text]
        else:
            english = text if text.isascii() else "Preserve the authored shot continuity and camera treatment."
        fields.append({"path": path, "english": english})
    if directions_fields is not None:
        fields = directions_fields
    from tests.video_fidelity_fixtures import checked_batch
    # Exercise the supported native single-shot lifecycle with a synthetic host.
    # This is contract-fixture evidence, never a live semantic-quality claim.
    service = client.app.state.video_batch_service
    current = service.current(project_id)
    if current and current["state"] not in {"cancelled", "approved", "retired"}:
        service.control(project_id, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="cancel"))
    capability = service.video.public_capability()
    profile = body.get("profileId") or capability.get("defaultProfileId") or capability["profiles"][0]["id"]
    policy = body.get("aspectPolicy") or "reject_mismatch"
    single = service.setup(project_id, BatchSetup(profileId=profile, aspectPolicy=policy,
        shotIds=[body["shotId"]], singleRequest=body))
    assert not single["manifest"]["blockers"], single["manifest"]["blockers"]
    from plotloom.video_batch_contracts import BatchDirectionsDraft, BatchStart
    draft = BatchDirectionsDraft(targets=[{"shotId": body["shotId"], "sourceHash": sources["sourceHash"], "fields": fields}])
    ready = checked_batch(service, project_id, single, draft)
    started = service.start(project_id, BatchStart(expectedRevision=ready["revision"], manifestHash=ready["manifestHash"], basis="production-intent.v2"))
    reviewed = authorized_directions(started, started["manifest"]["targets"][0])
    return {**body, "reviewedDirections": reviewed}
