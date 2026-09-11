"""Trusted, versioned text-protocol adapter registry and readiness contract.

The registry is intentionally internal and finite.  A profile selects an
adapter by ID/version; endpoint and model values are adapter inputs, never
adapter dispatch selectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .generation.contracts import ProviderCapabilities
from .generation.exceptions import ProviderError
from .generation.providers import OpenAICompatibleAdapter, ProviderAdapter
from .provider_profiles import (
    OPENAI_COMPATIBLE_ADAPTER_ID,
    OPENAI_COMPATIBLE_ADAPTER_VERSION,
    TextProviderProfileSnapshotV3,
)


@dataclass(frozen=True)
class ReadinessResult:
    state: str
    reason_code: str
    checked: bool


AdapterFactory = Callable[[TextProviderProfileSnapshotV3], ProviderAdapter]


class TextAdapterRegistry:
    """Fixed trusted registry; arbitrary imports and provider heuristics are forbidden."""

    def __init__(self, entries: Mapping[tuple[str, str], AdapterFactory] | None = None) -> None:
        self._entries = dict(entries or {
            (OPENAI_COMPATIBLE_ADAPTER_ID, OPENAI_COMPATIBLE_ADAPTER_VERSION): _openai_compatible,
        })

    def supported(self) -> list[dict[str, str]]:
        return [
            {"adapterId": adapter_id, "adapterVersion": version}
            for adapter_id, version in sorted(self._entries)
        ]

    def resolve(self, snapshot: TextProviderProfileSnapshotV3) -> ProviderAdapter:
        factory = self._entries.get((snapshot.adapter_id, snapshot.adapter_version))
        if factory is None:
            raise ValueError(
                f"unsupported text adapter {snapshot.adapter_id!r} version {snapshot.adapter_version!r}"
            )
        return factory(snapshot)

    def preflight(self, snapshot: TextProviderProfileSnapshotV3, secret: Any | None) -> ReadinessResult:
        """Run a cheap protocol check, never a creative completion.

        Adapters without this capability intentionally return unverified; they
        are not treated as unavailable merely because no safe check exists.
        """

        adapter = self.resolve(snapshot)
        checker = getattr(adapter, "check_readiness", None)
        if checker is None:
            return ReadinessResult("unverified", "readiness.check_unsupported", False)
        try:
            return checker(snapshot.text_model, secret)
        except ProviderError:
            return ReadinessResult("unreachable", "readiness.transport_failed", True)


def _openai_compatible(snapshot: TextProviderProfileSnapshotV3) -> ProviderAdapter:
    return OpenAICompatibleAdapter(
        name=snapshot.text_provider,
        base_url=snapshot.text_base_url,
        capabilities=ProviderCapabilities.model_validate(snapshot.text_capabilities.model_dump()),
        auth_mode=snapshot.text_auth_mode,
        connect_timeout_seconds=snapshot.text_connect_timeout_seconds,
        timeout_seconds=snapshot.text_attempt_timeout_seconds,
    )


DEFAULT_TEXT_ADAPTER_REGISTRY = TextAdapterRegistry()
