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
    VideoBackendInstanceIdentity,
    VideoProviderError,
    WanDispatchDiagnostic,
    WanDispatchError,
)
from .adapter import H3_PROFILE_CONTRACT_VERSION, H3_PROFILES_BY_ID, H3_QUALIFIED_DURATION_FRAMES


class MiniMaxH3GatewayTransport:
    """Bearer-authenticated, no-retry transport for the fixed H3 catalog."""

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
            or payload.get("inputModes") != ["image", "text"]
            or type(payload.get("queuedJobs")) is not int
            or payload["queuedJobs"] < 0
            or type(payload.get("activeDispatches")) is not int
            or payload["activeDispatches"] not in {0, 1}
            or payload.get("dispatchConcurrency") != 1
        ):
            raise VideoProviderError("h3_gateway_profile_unavailable")

    def configured_backend_identity(self) -> VideoBackendInstanceIdentity:
        """Return a stable local fingerprint, never the gateway URL itself."""

        parsed = urlparse(self.base_url)
        # ``_validated_private_base_url`` has already rejected userinfo,
        # queries, fragments, and non-root paths.  Keep the exact configured
        # HTTP(S) endpoint in the hash so two private/Tailscale gateways do
        # not share a project binding merely because they run H3.
        endpoint = f"{parsed.scheme.lower()}://{parsed.hostname.lower()}"
        if parsed.port is not None:
            endpoint += f":{parsed.port}"
        return VideoBackendInstanceIdentity.from_public_configuration(
            "minimax_h3_gateway_endpoint_v1", {"endpoint": endpoint}
        )

    def submit_image(self, image: bytes, *, mime_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a frozen Plotloom keyframe through the direct gateway route."""

        if set(payload) != {"prompt", "profileId", "aspectPolicy", "seed", "durationSeconds"}:
            raise WanDispatchError(WanDispatchDiagnostic("request_compile", "local_precondition_failed"))
        duration = payload["durationSeconds"]
        expected_frame_count = H3_QUALIFIED_DURATION_FRAMES.get(duration) if type(duration) is int else None
        if expected_frame_count is None:
            raise WanDispatchError(WanDispatchDiagnostic("request_compile", "local_precondition_failed"))
        result = self._request_json(
            "submit", "POST", "v1/video-jobs/from-image",
            files={"image": ("approved-keyframe", image, mime_type)},
            data={key: str(value) for key, value in payload.items()},
        )
        self._validate_job_envelope(
            result,
            phase="submit_response_parse",
            expected_duration_seconds=payload["durationSeconds"],
            expected_frame_count=expected_frame_count,
            expected_seed=payload["seed"],
        )
        if result.get("inputMode") != "image":
            raise WanDispatchError(WanDispatchDiagnostic("submit_response_parse", "invalid_envelope"))
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
        expected_duration_seconds: int | None = None,
        expected_frame_count: int | None = None,
        expected_seed: int | None = None,
    ) -> None:
        expected = {
            "id", "status", "inputMode", "profileId", "aspectPolicy", "seed",
            "requestedDurationSeconds", "frameCount", "actualDurationSeconds",
            "generationSubmittedAt", "generationCompletedAt", "generationElapsedMs",
            "error", "outputReady",
        }
        if set(value) != expected:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        identifier = value.get("id")
        if not isinstance(identifier, str) or not cls._JOB_ID.fullmatch(identifier) or (expected_id is not None and identifier != expected_id):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("profileId") not in H3_PROFILES_BY_ID:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("status") not in {
            "reserved", "queued", "submitting", "submitted", "running",
            "transfer_pending", "succeeded", "failed",
            "outcome_unknown", "cancelled",
        }:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("inputMode") not in {"image", "text"}:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("inputMode") == "image" and value.get("aspectPolicy") not in {"cover_center_crop", "contain_pad", "reject_mismatch"}:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("inputMode") == "text" and value.get("aspectPolicy") is not None:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if type(value.get("seed")) is not int or value["seed"] < 0:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        duration = value.get("requestedDurationSeconds")
        frame_count = value.get("frameCount")
        if type(duration) is not int or not 5 <= duration <= 15 or type(frame_count) is not int or frame_count % 17 != 5:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if (
            expected_duration_seconds is not None and duration != expected_duration_seconds
            or expected_frame_count is not None and frame_count != expected_frame_count
        ):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if expected_seed is not None and value.get("seed") != expected_seed:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        actual = value.get("actualDurationSeconds")
        if type(actual) not in {float, int} or abs(float(actual) - frame_count / 24) > 0.0001:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        for key in ("generationSubmittedAt", "generationCompletedAt"):
            if value.get(key) is not None and not isinstance(value.get(key), str):
                raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        elapsed = value.get("generationElapsedMs")
        if elapsed is not None and (type(elapsed) is not int or elapsed < 0):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if value.get("error") is not None and not isinstance(value.get("error"), str):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        if type(value.get("outputReady")) is not bool:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
