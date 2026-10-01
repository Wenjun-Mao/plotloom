"""Gateway voice facade and CPU-only registration control surface."""

import hashlib
import hmac
import re

from fastapi import Depends, Header, Request
from fastapi.responses import Response

from .contracts import GatewayError
from .voice_control import VoiceRegistration


def require_id(value, prefix):
    if not re.fullmatch(prefix + r"_[0-9a-f]{32}", value):
        raise GatewayError("voice.identifier_invalid", 422)
    return value


def install_voice_api(app, gateway, authorize):
    auth = [Depends(authorize)]
    control = gateway.voice_control

    def private_authorize(authorization: str | None = Header(default=None)):
        key = gateway.settings.voice_lab_key
        if not key or authorization is None or not hmac.compare_digest(authorization, f"Bearer {key}"):
            raise GatewayError("voice.dispatch_unauthorized", 401)

    private_auth = [Depends(private_authorize)]

    @app.post("/internal/voice-registrations", dependencies=private_auth, status_code=202)
    def register(body: VoiceRegistration):
        entry = gateway.lane.register_voice(body.kind, body.jobId, body.bindingHash)
        return {"sequence": entry["sequence"], "jobId": entry["job_id"]}

    @app.get("/internal/voice-registrations/{job_id}", dependencies=private_auth)
    def progress(job_id: str):
        if not re.fullmatch(r"(vg|vt|take)_[0-9a-f]{32}", job_id):
            raise GatewayError("voice.identifier_invalid", 422)
        return gateway.lane.progress("voice_lab", job_id)

    @app.post("/v1/voice-takes", dependencies=auth, status_code=202)
    async def create(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise GatewayError("request_media_type_not_supported", 415)
        try:
            body = await request.json()
        except ValueError as error:
            raise GatewayError("request_body_invalid", 422) from error
        if not isinstance(body, dict):
            raise GatewayError("request_body_invalid", 422)
        return control.request("POST", "/internal/voice-takes", body=body)

    @app.get("/v1/voice-takes", dependencies=auth)
    def list_takes(voiceId: str):
        require_id(voiceId, "voice")
        return control.request("GET", f"/internal/voice-takes?voiceId={voiceId}")

    @app.get("/v1/voice-takes/{take_id}", dependencies=auth)
    def get(take_id: str):
        require_id(take_id, "take")
        return control.request("GET", f"/internal/voice-takes/{take_id}")

    @app.get("/v1/voice-takes/{take_id}/audio", dependencies=auth)
    def audio(take_id: str, kind: str = "source"):
        require_id(take_id, "take")
        if kind not in {"source", "h3"}:
            raise GatewayError("voice.audio_kind_invalid", 422)
        metadata = control.request("GET", f"/internal/voice-takes/{take_id}")
        content = control.request("GET", f"/internal/voice-takes/{take_id}/audio?kind={kind}", audio=True)
        if hashlib.sha256(content).hexdigest() != metadata.get(f"{kind}Sha256"):
            raise GatewayError("voice.audio_hash_mismatch", 409)
        return Response(content, media_type="audio/wav")

    @app.delete("/v1/voice-takes/{take_id}", dependencies=auth, status_code=204)
    async def delete(take_id: str, request: Request):
        require_id(take_id, "take")
        try:
            body = await request.json()
        except ValueError as error:
            raise GatewayError("request_body_invalid", 422) from error
        control.request("DELETE", f"/internal/voice-takes/{take_id}", body=body)
