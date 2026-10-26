"""Provider adapter resolution from immutable public run snapshots."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from plotloom.provider_contracts import ProviderAuthMode, ProviderSnapshot
from .generation.contracts import (
    ProviderCapabilities,
)
from .generation.providers import OpenAICompatibleAdapter, ProviderAdapter
from .provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    is_v2_snapshot,
    is_v3_snapshot,
)
from .text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY


class TextProviderResolver(Protocol):
    """Build one adapter from the public settings frozen on a run."""

    def resolve(
        self, provider_snapshot: Mapping[str, Any]
    ) -> tuple[ProviderAdapter, str]: ...


class SnapshotTextProviderResolver:
    """Resolve only from enqueue-time public settings plus runtime defaults.

    Reading mutable provider settings inside a worker would let a later settings
    edit silently change a queued run.  The API therefore stores a secret-free
    provider snapshot on each run, and this resolver consumes only that snapshot.
    """

    def resolve(
        self, provider_snapshot: Mapping[str, Any]
    ) -> tuple[ProviderAdapter, str]:
        snapshot: (
            ProviderSnapshot
            | TextProviderProfileSnapshot
            | TextProviderProfileSnapshotV3
        )
        if is_v3_snapshot(provider_snapshot):
            snapshot = TextProviderProfileSnapshotV3.model_validate(provider_snapshot)
            return DEFAULT_TEXT_ADAPTER_REGISTRY.resolve(snapshot), snapshot.text_model
        if is_v2_snapshot(provider_snapshot):
            snapshot = TextProviderProfileSnapshot.model_validate(provider_snapshot)
        else:
            snapshot = ProviderSnapshot.model_validate(provider_snapshot)
        capabilities = ProviderCapabilities.model_validate(
            snapshot.text_capabilities.model_dump()
        )
        adapter = OpenAICompatibleAdapter(
            name=snapshot.text_provider,
            base_url=snapshot.text_base_url,
            capabilities=capabilities,
            auth_mode=(
                snapshot.text_auth_mode.value
                if isinstance(snapshot.text_auth_mode, ProviderAuthMode)
                else snapshot.text_auth_mode
            ),
            connect_timeout_seconds=snapshot.text_connect_timeout_seconds,
            timeout_seconds=snapshot.text_attempt_timeout_seconds,
        )
        return adapter, snapshot.text_model
