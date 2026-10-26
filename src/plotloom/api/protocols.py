from __future__ import annotations

from typing import Any, Protocol

from plotloom.provider_contracts import ProviderAuthMode
from plotloom.run_contracts import GenerationRun

from ..generation.secrets import SecretLease


class RunScheduler(Protocol):
    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Any: ...

    def request_cancel(self, run_id: str) -> GenerationRun: ...


class TextProfileSecretSource(Protocol):
    def server_key_available(self, profile_id: str = "default") -> bool: ...

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode,
    ) -> SecretLease | None: ...
