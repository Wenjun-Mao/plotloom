"""Typed transport for the private MiniMax-H3 gateway.

This module talks only to Plotloom's narrow gateway contract.  It cannot
submit ComfyUI graphs, choose a model, follow redirects, or download an output
from an arbitrary URL.
"""
from __future__ import annotations

import ipaddress
import re
import shutil
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests

from ...video_provider import (
    DispatchPhase,
    VideoProviderError,
    WanDispatchDiagnostic,
    WanDispatchError,
)
from .adapter import H3_PROFILE_CONTRACT_VERSION, H3_PROFILES_BY_ID


class MiniMaxH3GatewayTransport:
    """Bearer-authenticated, no-retry transport for the fixed H3 catalog."""

    _ASSET_ID = re.compile(r"^asset_[0-9a-f]{32}$")
    _JOB_ID = re.compile(r"^h3_[0-9a-f]{32}$")

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str,
        timeout_seconds: float = 30.0,
        max_download_bytes: int = 100 * 1024 * 1024,
        session: requests.Session | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self.base_url = self._validated_private_base_url(base_url)
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self._session = session or requests.Session()
        self._session.trust_env = False

    @staticmethod
    def _validated_private_base_url(value: str) -> str:
        candidate = value.strip().rstrip("/")
        parsed = urlparse(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("H3 gateway base URL must be a credential-free HTTP(S) host root")
        try:
            host = ipaddress.ip_address(parsed.hostname)
            port = parsed.port
        except ValueError as error:
            raise ValueError("H3 gateway host and port must be valid") from error
        tailnet = ipaddress.ip_network("100.64.0.0/10")
        if not (host.is_loopback or host.is_private or host in tailnet):
            raise ValueError("H3 gateway must use a loopback, private, or Tailnet address")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("H3 gateway port is invalid")
        return candidate + "/"

    def preflight(self) -> None:
        if not self._api_key:
            raise VideoProviderError("h3_gateway_credential_unavailable")
        if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
            raise VideoProviderError("h3_media_probe_unavailable")
        payload = self._request_json("request_compile", "GET", "health", authenticated=False)
        if (
            not isinstance(payload, dict)
            or payload.get("status") != "ok"
            or payload.get("profileContractVersion") != H3_PROFILE_CONTRACT_VERSION
            or payload.get("profiles") != [profile.public_descriptor() for profile in H3_PROFILES_BY_ID.values()]
            or type(payload.get("maxQueueDepth")) is not int
            or payload["maxQueueDepth"] < 1
        ):
            raise VideoProviderError("h3_gateway_profile_unavailable")

    def upload(self, image: bytes, *, mime_type: str) -> str:
        payload = self._request_json(
            "upload",
            "POST",
            "v1/assets",
            files={"image": ("approved-keyframe", image, mime_type)},
        )
        if set(payload) != {"assetId", "mimeType", "width", "height", "sha256"}:
            raise WanDispatchError(WanDispatchDiagnostic("upload", "invalid_envelope"))
        asset_id = payload.get("assetId")
        if not isinstance(asset_id, str) or not self._ASSET_ID.fullmatch(asset_id):
            raise WanDispatchError(WanDispatchDiagnostic("upload", "invalid_envelope"))
        if payload.get("mimeType") != mime_type or type(payload.get("width")) is not int or type(payload.get("height")) is not int:
            raise WanDispatchError(WanDispatchDiagnostic("upload", "invalid_envelope"))
        digest = payload.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise WanDispatchError(WanDispatchDiagnostic("upload", "invalid_envelope"))
        return asset_id

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._request_json("submit", "POST", "v1/video-jobs", json=payload)
        self._validate_job_envelope(result, phase="submit_response_parse")
        return result

    def poll(self, prediction_id: str) -> dict[str, Any]:
        self._validate_job_id(prediction_id)
        result = self._request_json("poll", "GET", f"v1/video-jobs/{quote(prediction_id, safe='')}")
        self._validate_job_envelope(result, phase="poll", expected_id=prediction_id)
        return result

    def download(self, reference: str) -> bytes:
        self._validate_job_id(reference)
        try:
            response = self._session.get(
                urljoin(self.base_url, f"v1/video-jobs/{quote(reference, safe='')}/output"),
                headers=self._headers(),
                timeout=self.timeout_seconds,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as error:
            raise VideoProviderError("H3 gateway output is unavailable") from error
        try:
            if response.status_code != 200:
                raise VideoProviderError("H3 gateway output was not successful")
            if not response.headers.get("Content-Type", "").lower().startswith("video/mp4"):
                raise VideoProviderError("H3 gateway output has an unexpected content type")
            declared = response.headers.get("Content-Length")
            if declared is not None and (not declared.isdigit() or int(declared) > self.max_download_bytes):
                raise VideoProviderError("H3 gateway output exceeds configured limit")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > self.max_download_bytes:
                    raise VideoProviderError("H3 gateway output exceeds configured limit")
                chunks.append(chunk)
            if not chunks:
                raise VideoProviderError("H3 gateway output is empty")
            return b"".join(chunks)
        finally:
            response.close()

    def _request_json(
        self,
        phase: DispatchPhase,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = self._headers() if authenticated else {}
        try:
            response = self._session.request(
                method,
                urljoin(self.base_url, path),
                headers=headers,
                timeout=self.timeout_seconds,
                allow_redirects=False,
                **kwargs,
            )
        except requests.RequestException as error:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "transport_unavailable")) from error
        if not 200 <= response.status_code < 300:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "http_rejected", response.status_code))
        try:
            payload = response.json()
        except ValueError as error:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_json")) from error
        if not isinstance(payload, dict):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        return payload

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    @classmethod
    def _validate_job_id(cls, value: str) -> None:
        if not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 gateway job ID is invalid")

    @classmethod
    def _validate_job_envelope(
        cls,
        value: dict[str, Any],
        *,
        phase: DispatchPhase,
        expected_id: str | None = None,
    ) -> None:
        expected = {"id", "status", "profileId", "aspectPolicy", "error", "outputReady"}
        if set(value) != expected:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        identifier = value.get("id")
        if not isinstance(identifier, str) or not cls._JOB_ID.fullmatch(identifier) or (expected_id is not None and identifier != expected_id):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("profileId") not in H3_PROFILES_BY_ID:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("status") not in {"reserved", "submitted", "running", "succeeded", "failed", "outcome_unknown", "cancelled"}:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("aspectPolicy") not in {"cover_center_crop", "contain_pad", "reject_mismatch"}:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("error") is not None and not isinstance(value.get("error"), str):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if type(value.get("outputReady")) is not bool:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
