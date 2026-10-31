"""Source-installed, API-selected synthetic clips; never contacts a provider."""
import subprocess
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from io import BytesIO

import pytest
from PIL import Image

from plotloom.contract_identity import utc_now
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.language_policy import language_contract
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project.media_identifiers import new_video_job_id
from plotloom.persistence.schema import (
    ApprovalDecisionRow,
    ManagedAssetRow,
    VideoJobRow,
)
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.stage_contracts import StageName
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.video_segments import derive_playback_segment
from tests.autopilot_controller_fixtures import PIN
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.test_frozen_video_integrity import _job
from tests.video_storage_fixtures import FakeH3, _approved_keyframe, _fixture_app


def synthetic_video(output, color="navy"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=640x360:r=24:d=8",
        "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=8", "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(output)], check=True, timeout=30)
    return output.read_bytes()


@pytest.fixture
def exportable_bridge(tmp_path, monkeypatch):
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: PIN)
    provider = FakeH3()
    # Any unexpected dispatch is a fixture failure, not live authorization.
    monkeypatch.setattr(provider, "submit_image", lambda *_a, **_k: pytest.fail("unexpected provider submission"))
    storage, client = _fixture_app(tmp_path, provider)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project = store.manifest.project_id
        proposal = _prepare_installable_bridge(store)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
        board = store.authoring.get_stage_payload(project, StageName.STORYBOARD)
        admission = store.production_bridge_installation().admission_id
    output = tmp_path / "synthetic-eight-seconds.mp4"
    original = synthetic_video(output)
    digest = sha256(original).hexdigest()
    duration = board.shots[0].duration_units
    assert all(shot.duration_units == duration for shot in board.shots)
    # One real decoded trim reused only for identical immutable fixture inputs.
    derived = derive_playback_segment(original, in_frame=0, out_frame=duration * 24 // 1000, authored_duration_units=duration)
    derived_by_hash = {digest: derived}
    def derive_same(raw, *, in_frame, out_frame, authored_duration_units):
        assert in_frame == 0 and out_frame == derived.out_frame and authored_duration_units == duration
        return derived_by_hash[sha256(raw).hexdigest()]
    monkeypatch.setattr("plotloom.project_storage.project_video.derive_playback_segment", derive_same)
    approval = None
    base = f"/api/v2/projects/{project}"
    snapshots = {}
    for index, shot in enumerate(board.shots):
        image = BytesIO()
        Image.new("RGB", (640, 360), (index, 30, 100)).save(image, format="PNG")
        approval, context = _approved_keyframe(client, storage, project, keyframe_bytes=image.getvalue(),
            author_frame_grid=False, shot_id=shot.id, approval=approval, selection_revision=index)
        with closing(storage.projects.open(project)) as store:
            uri = store.artifacts.put(original)
            with store.repository._write() as session:
                selection = context["selection"]
                asset = session.get(ManagedAssetRow, selection["assetId"])
                decision = session.get(ApprovalDecisionRow, approval["id"])
                frozen = deepcopy(_job().snapshot)
                frozen.update(shot=shot.model_dump(mode="json", by_alias=True),
                    sourceTiming=store.repository._media.direct_video._source_timing.binding_in_session(session, project, shot.id, duration),
                    approvalId=approval["id"], storyboardEntityRevisionId=decision.entity_revision_id,
                    languageContract=language_contract("zh-CN"),
                    keyframe={"bindingId": selection["id"], "assetId": asset.id, "originalHash": asset.original_hash,
                        "selectionRevision": selection["selectionRevision"]})
                snapshots[shot.id] = deepcopy(frozen)
                identifier = new_video_job_id()
                key = f"synthetic-export-{shot.id}"
                session.add(VideoJobRow(id=identifier, project_id=project, idempotency_key=key,
                    state="ingested", requested_seconds=8, output_uri=uri, output_hash=digest,
                    snapshot=frozen, snapshot_hash=stable_hash(frozen),
                    request_hash=stable_hash({"snapshot": frozen, "idempotencyKey": key}), created_at=utc_now(), updated_at=utc_now()))
        result = client.post(f"{base}/video-jobs/{identifier}/segments", json={"inFrame": 0, "outFrame": derived.out_frame, "expectedSelectionRevision": 0})
        assert result.status_code == 201, result.text
        result = client.post(f"{base}/video-segments/{result.json()['id']}/select", json={"expectedSelectionRevision": 0})
        assert result.status_code == 201, result.text
    def replace_first_slot():
        raw = synthetic_video(tmp_path / "alternate-slot.mp4", "maroon")
        digest = sha256(raw).hexdigest()
        derived_by_hash[digest] = derive_playback_segment(raw, in_frame=0, out_frame=derived.out_frame, authored_duration_units=duration)
        frozen = snapshots[board.shots[0].id]
        identifier, key = new_video_job_id(), "synthetic-alternate-slot"
        with closing(storage.projects.open(project)) as store:
            uri = store.artifacts.put(raw)
            with store.repository._write() as session:
                session.add(VideoJobRow(id=identifier, project_id=project, idempotency_key=key,
                    state="ingested", requested_seconds=8, output_uri=uri, output_hash=digest,
                    snapshot=frozen, snapshot_hash=stable_hash(frozen),
                    request_hash=stable_hash({"snapshot": frozen, "idempotencyKey": key}), created_at=utc_now(), updated_at=utc_now()))
        result = client.post(f"{base}/video-jobs/{identifier}/segments", json={"inFrame": 0, "outFrame": derived.out_frame, "expectedSelectionRevision": 1})
        assert result.status_code == 201, result.text
        result = client.post(f"{base}/video-segments/{result.json()['id']}/select", json={"expectedSelectionRevision": 1})
        assert result.status_code == 201, result.text
    return storage, client, project, {"admissionId": admission, "gameId": "synthetic-beacon",
        "intro": "Synthetic source-owned introduction", "endingCards": {
            "ending-a": {"title": "Beacon", "text": "Beacon ending from the project."},
            "ending-b": {"title": "Dock", "text": "Dock ending from the project."}},
        "nodeBindings": {"N00": "opening", "C01": "choose", "E01": "ending-a", "E02": "ending-b"},
        "slotBindings": {"opening-first": board.shots[0].id}}, replace_first_slot
