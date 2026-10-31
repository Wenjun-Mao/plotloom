"""Authored requirements and offline capture of the final H3 multipart request."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from plotloom.video_backends.minimax_h3 import (
    MiniMaxH3GatewayAdapter,
    MiniMaxH3GatewayTransport,
)
from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
from tests.test_h3_authored_soundtrack import package, source
from tests.video_backends.minimax_h3.test_transport import _job, _Response


def authored_request(*, action=None):
    snapshot = source()
    if action is not None:
        snapshot["shot"]["action"] = action[0]
    snapshot.pop("shotPresentation")
    for state in ("entryState", "exitState"):
        snapshot["shot"][state]["sound"] = "房间底噪"
    snapshot["request"]["profileId"] = "minimax_h3_quality8_portrait_576x1024_v2"
    fixtures = Path(__file__).parent / "fixtures"
    images = [(fixtures / name).read_bytes() for name in ("h3-opening.png", "h3-ending.png")]
    for key, blob in zip(("keyframe", "endFrame"), images, strict=True):
        snapshot[key]["originalHash"] = sha256(blob).hexdigest()
    _, target = package(snapshot)
    states = "The letter stays unsent; door closed; both hands present. Face left in soft morning light. Quiet room tone. Do not open the door."
    translations = {
        "shot.composition": "A person left of the door.",
        "shot.visualIntent": "Clearly visible envelope.",
        "shot.action": "The person does not open the door and only raises the envelope.",
        "shot.motionIntent": "Slowly raise one hand.",
        "shot.cameraMovement": "Hold still.", "shot.cameraAngle": "Eye level.",
        "shot.transition": "Hard cut.", "shot.entryState": states, "shot.exitState": states,
        "shot.requiredEntityStates": "The letter stays unsent.",
        "resolvedContext.characters.C01.voiceAnchors.0": "A steady voice.",
        "resolvedContext.dialogueCues.0.delivery": "natural",
        "resolvedContext.dialogueCues.0.performanceNotes": "Speak with restraint.",
    }
    if action is not None:
        translations["shot.action"] = action[1]
    for field in target["fields"]:
        if field["path"] in translations:
            field["english"] = translations[field["path"]]
    # Synthetic adaptation, not a claimed semantic-checker or live-provider pass.
    prompt = compile_i2va_prompt(snapshot, target, draft=True)
    return snapshot, prompt, images


class CaptureSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, deepcopy(kwargs)))
        return _Response(202, _job("queued", False, duration=8, frame_count=192) | {
            "quality": 8, "aspectPolicy": "contain_pad", "seed": int(kwargs["data"]["seed"])})


def capture_request(snapshot, prompt, images):
    request = snapshot["request"]
    payload = MiniMaxH3GatewayAdapter().compile_image(prompt=prompt,
        duration=request["durationSeconds"], resolution=request["resolution"], audio=request["audio"],
        aspect_policy=request["aspectPolicy"], seed=request["seed"], profile_id=request["profileId"],
        profile_version=request["profileVersion"], width=request["width"], height=request["height"],
        fps=request["fps"], frame_count=request["frameCount"], quality=request["quality"])
    session = CaptureSession()
    transport = MiniMaxH3GatewayTransport("synthetic-test-key", base_url="http://127.0.0.1:9", session=session)
    transport.submit_image(images[0], mime_type="image/png", payload=payload,
        end_image=images[1], end_mime_type="image/png")
    assert len(session.calls) == 1
    method, url, call = session.calls[0]
    assert call["allow_redirects"] is False
    assert call["headers"] == {"Authorization": "Bearer synthetic-test-key"}
    return {"method": method, "path": urlsplit(url).path, "data": call["data"],
        "files": [{"field": name, "filename": value[0], "mimeType": value[2],
            "sha256": sha256(value[1]).hexdigest()} for name, value in call["files"].items()]}
