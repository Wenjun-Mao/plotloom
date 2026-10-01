"""Narrow configured Voice Lab control transport; no inference imports."""

import requests
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

from .contracts import GatewayError


class VoiceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["generation", "clone", "take"]
    jobId: str = Field(pattern=r"^(vg|vt|take)_[0-9a-f]{32}$")
    bindingHash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def matching_kind(self):
        if not self.jobId.startswith({"generation": "vg_", "clone": "vt_", "take": "take_"}[self.kind]):
            raise ValueError("dispatch.kind_mismatch")
        return self


class VoiceControl:
    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session or requests.Session()

    def request(self, method, path, *, body=None, audio=False):
        if not self.settings.voice_lab_url or not self.settings.voice_lab_key:
            raise GatewayError("voice.control_unconfigured", 503)
        try:
            response = self.session.request(
                method, self.settings.voice_lab_url + path,
                json=body, headers={"Authorization": f"Bearer {self.settings.voice_lab_key}"},
                timeout=(3, 3), allow_redirects=False,
            )
        except requests.RequestException as error:
            code = "voice.dispatch_outcome_unknown" if method == "POST" else "voice.control_unavailable"
            raise GatewayError(code, 503) from error
        if response.status_code == 204:
            return None
        if response.status_code not in {200, 201, 202}:
            # Do not forward arbitrary backend bodies/paths or redirect requests.
            code = "voice.control_rejected"
            try:
                value = response.json().get("detail", {})
                if isinstance(value, dict) and isinstance(value.get("code"), str):
                    code = value["code"]
            except (ValueError, AttributeError):
                pass
            raise GatewayError(code, response.status_code if 400 <= response.status_code < 500 else 503)
        if audio:
            return response.content
        try:
            value = response.json()
        except ValueError as error:
            raise GatewayError("voice.control_invalid_response") from error
        if not isinstance(value, dict):
            raise GatewayError("voice.control_invalid_response")
        return value

    def execute(self, entry):
        return self.request("POST", "/internal/executions", body={
            "kind": entry["job_kind"], "jobId": entry["job_id"],
            "bindingHash": entry["binding_hash"], "grantId": entry["grant_id"],
        })

    def execution(self, entry):
        return self.request("GET", f"/internal/executions/{entry['grant_id']}")
