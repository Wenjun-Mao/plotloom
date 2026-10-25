from __future__ import annotations

from typing import Any, Mapping, Protocol

from ..domain import (
    GenerationRun,
    ProviderAuthMode,
)
from ..generation.providers import ProviderAdapter
from ..generation.secrets import SecretLease


class RunScheduler(Protocol):
    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Any: ...

    def request_cancel(self, run_id: str) -> GenerationRun: ...






class TextProviderResolver(Protocol):
    def resolve(
        self, provider_snapshot: Mapping[str, Any]
    ) -> tuple[ProviderAdapter, str]: ...


class TextProfileSecretSource(Protocol):
    def server_key_available(self, profile_id: str = "default") -> bool: ...

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode,
    ) -> SecretLease | None: ...
