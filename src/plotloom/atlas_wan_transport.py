"""Real AtlasCloud Wan HTTP transport, disabled unless runtime preflight opts in."""
from __future__ import annotations

import ipaddress
import shutil
import socket
from time import monotonic
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from urllib3 import HTTPSConnectionPool, Timeout

from .video_ingestion import VideoIngestionError, assert_public_https_url
from .video_provider import DispatchPhase, WanDispatchDiagnostic, WanDispatchError, VideoProviderError


class AtlasCloudWanTransport:
    """Narrow transport with no POST retry and no credential-bearing download.

    It is constructed only by explicit runtime opt-in.  Credentials remain in
    process memory and are never exposed by its public job data.
    """
    def __init__(self, api_key: str, *, base_url: str = "https://api.atlascloud.ai/api/v1/model", timeout_seconds: float = 30.0, max_download_bytes: int = 100 * 1024 * 1024) -> None:
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self._session = requests.Session()
        self._session.trust_env = False  # no proxy/netrc ambient credentials

    def preflight(self) -> None:
        if not self._api_key:
            raise VideoProviderError("wan_transport_credential_unavailable")
        if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
            raise VideoProviderError("wan_media_probe_unavailable")

    def _authorized(self, phase: DispatchPhase, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._session.request(method, urljoin(self.base_url, path), headers={"Authorization": f"Bearer {self._api_key}"}, timeout=self.timeout_seconds, allow_redirects=False, **kwargs)
        except requests.RequestException as error:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "transport_unavailable")) from error
        if response.status_code < 200 or response.status_code >= 300:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "http_rejected", response.status_code))
        try:
            payload = response.json()
        except ValueError as error:
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_json")) from error
        if not isinstance(payload, dict):
            raise WanDispatchError(WanDispatchDiagnostic(phase, "invalid_envelope"))
        return payload

    def upload(self, image: bytes, *, mime_type: str) -> str:
        payload = self._authorized("upload", "POST", "uploadMedia", files={"file": ("approved-keyframe", image, mime_type)})
        url = self._upload_url(payload)
        if url is None:
            raise WanDispatchError(WanDispatchDiagnostic("upload", "invalid_upload_url"))
        return url

    @staticmethod
    def _upload_url(payload: dict[str, Any]) -> str | None:
        """Accept only the two documented Atlas upload envelopes.

        A response can be a successful HTTP envelope while still being an
        application error.  This parser deliberately does not search nested
        objects or use ``data.url`` as a compatibility fallback.
        """

        if payload.get("error") is not None:
            return None

        candidates: list[str] = []
        if "url" in payload:
            url = AtlasCloudWanTransport._valid_upload_url(payload["url"])
            if url is None:
                return None
            candidates.append(url)

        if "data" in payload:
            data = payload["data"]
            if not isinstance(data, dict):
                return None
            if "download_url" in data:
                url = AtlasCloudWanTransport._valid_upload_url(data["download_url"])
                if url is None:
                    return None
                candidates.append(url)

        if not candidates or any(url != candidates[0] for url in candidates[1:]):
            return None
        return candidates[0]

    @staticmethod
    def _valid_upload_url(value: object) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        if any(
            character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159
            for character in value
        ):
            return None
        try:
            parsed = urlparse(value)
            # Accessing ``port`` makes urllib reject non-numeric and out of
            # range ports.  A trailing colon has no port value, but is also
            # not a complete authority for this contract.
            _ = parsed.port
        except ValueError:
            return None
        if (
            parsed.scheme != "https"
            or not AtlasCloudWanTransport._has_valid_hostname(parsed.hostname)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.netloc.endswith(":")
        ):
            return None
        return value

    @staticmethod
    def _has_valid_hostname(hostname: str | None) -> bool:
        if not hostname:
            return False
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            pass
        try:
            ascii_hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError:
            return False
        labels = ascii_hostname.removesuffix(".").split(".")
        return bool(
            ascii_hostname
            and len(ascii_hostname) <= 253
            and all(
                0 < len(label) <= 63
                and label[0] != "-"
                and label[-1] != "-"
                and all(character.isascii() and (character.isalnum() or character == "-") for character in label)
                for label in labels
            )
        )

    def submit(
        self, payload: dict[str, Any], *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        # Atlas's documented payload has no idempotency field. Plotloom still
        # supplies its durable ID to adapters that support it (notably H3).
        _ = idempotency_key
        return self._authorized("submit", "POST", "generateVideo", json=payload)

    def poll(self, prediction_id: str) -> dict[str, Any]:
        return self._authorized("poll", "GET", f"prediction/{prediction_id}")

    def download(self, url: str) -> bytes:
        assert_public_https_url(url)
        host = urlparse(url).hostname
        assert host is not None
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
            if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
                raise VideoIngestionError("provider download host is not globally routable")
        except socket.gaierror as error:
            raise VideoIngestionError("provider download host could not resolve") from error
        deadline = monotonic() + self.timeout_seconds
        # Pin the validated address, while TLS SNI/certificate validation uses
        # the original hostname. This closes the second-DNS-resolution gap.
        target = urlparse(url)
        address = sorted(addresses)[0]
        request_path = target.path or "/"
        if target.query:
            request_path = f"{request_path}?{target.query}"
        pool = HTTPSConnectionPool(address, port=443, assert_hostname=host, server_hostname=host)
        response = pool.urlopen("GET", request_path, headers={"Host": host}, redirect=False, preload_content=False, timeout=Timeout(total=self.timeout_seconds))
        try:
            if response.status != 200:
                raise VideoIngestionError("provider video download was not successful")
            declared = response.headers.get("Content-Length")
            if declared is not None and (not declared.isdigit() or int(declared) > self.max_download_bytes):
                raise VideoIngestionError("provider video download exceeds configured limit")
            chunks: list[bytes] = []
            size = 0
            while True:
                if monotonic() > deadline:
                    raise VideoIngestionError("provider video download exceeded total deadline")
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_download_bytes:
                    raise VideoIngestionError("provider video download exceeds configured limit")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            response.release_conn()
            pool.close()
