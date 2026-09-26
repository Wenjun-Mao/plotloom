"""Bounded, private-network retrieval of a source image for gateway admission."""
from __future__ import annotations

from typing import Any

import requests

from .contracts import MAX_UPLOAD_BYTES, GatewayError, GatewaySettings


class SourceImageFetcher:
    """Fetch bytes without sharing the ComfyUI transport or retaining source URLs."""

    def __init__(self, settings: GatewaySettings, session: requests.Session | Any | None = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        # requests follows redirects itself; this retains a bounded policy even
        # when the caller supplied a plain requests.Session implementation.
        self._session.max_redirects = settings.source_fetch_max_redirects

    def fetch(
        self, source_url: str, *, max_bytes: int = MAX_UPLOAD_BYTES,
        empty_code: str = "image_size_invalid",
    ) -> bytes:
        response: Any | None = None
        try:
            response = self._session.get(
                source_url,
                allow_redirects=True,
                stream=True,
                timeout=(
                    self._settings.source_fetch_connect_timeout_seconds,
                    self._settings.source_fetch_read_timeout_seconds,
                ),
            )
            response.raise_for_status()
            self._reject_declared_oversize(response, max_bytes)
            return self._read_bounded(response, max_bytes, empty_code)
        except GatewayError:
            raise
        except requests.RequestException as error:
            raise GatewayError("source_url_fetch_failed", 422) from error
        except (OSError, TypeError, ValueError) as error:
            raise GatewayError("source_url_fetch_failed", 422) from error
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

    @staticmethod
    def _reject_declared_oversize(response: Any, max_bytes: int) -> None:
        header = getattr(response, "headers", {}).get("Content-Length")
        if header is None:
            return
        try:
            declared_size = int(header)
        except (TypeError, ValueError):
            return
        if declared_size > max_bytes:
            raise GatewayError("source_url_too_large", 413)

    @staticmethod
    def _read_bounded(response: Any, max_bytes: int, empty_code: str) -> bytes:
        chunks: list[bytes] = []
        size_bytes = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                raise GatewayError("source_url_too_large", 413)
            chunks.append(chunk)
        if size_bytes == 0:
            raise GatewayError(empty_code, 413)
        return b"".join(chunks)
