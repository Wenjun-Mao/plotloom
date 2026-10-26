"""Run-scoped opaque credential leasing and lifecycle cleanup."""

from __future__ import annotations

from threading import RLock
from typing import Callable, Mapping, Protocol

from plotloom.provider_contracts import ProviderAuthMode
from .generation.exceptions import SecretLeaseError
from .generation.secrets import InMemorySecretVault, SecretLease


class RunSecretBroker:
    """Resolve server credentials and per-run browser overrides without storage.

    Only opaque leases leave this object. Run overrides are removed after the
    run ends, and neither names nor values are included in persistence models.
    """

    def __init__(
        self,
        server_text_key: str | None = None,
        *,
        server_profile_keys: Mapping[str, str] | None = None,
        server_key_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        self._vault = InMemorySecretVault()
        self._lock = RLock()
        self._run_aliases: dict[str, tuple[str, str]] = {}
        self._server_aliases: dict[str, str] = {}
        self._server_key_resolver = server_key_resolver
        if server_text_key:
            self._server_aliases["default"] = "server:default:text"
            self._vault.put(self._server_aliases["default"], server_text_key)
        for profile_id, value in (server_profile_keys or {}).items():
            normalized = value.strip()
            if not normalized:
                continue
            alias = f"server:{profile_id}:text"
            self._server_aliases[profile_id] = alias
            self._vault.put(alias, normalized)

    def server_key_available(self, profile_id: str = "default") -> bool:
        with self._lock:
            return self._server_alias_for(profile_id) is not None

    def _server_alias_for(self, profile_id: str) -> str | None:
        alias = self._server_aliases.get(profile_id)
        if alias is not None:
            return alias
        if self._server_key_resolver is None:
            return None
        value = (self._server_key_resolver(profile_id) or "").strip()
        if not value:
            return None
        alias = f"server:{profile_id}:text"
        self._vault.put(alias, value)
        self._server_aliases[profile_id] = alias
        return alias

    def register_run_override(
        self,
        run_id: str,
        value: str | None,
        *,
        profile_id: str = "default",
    ) -> None:
        normalized = (value or "").strip()
        if not normalized:
            return
        alias = f"run:{run_id}:text"
        with self._lock:
            previous = self._run_aliases.get(run_id)
            if previous:
                self._vault.remove(previous[0])
            self._vault.put(alias, normalized)
            self._run_aliases[run_id] = (alias, profile_id)

    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER,
        profile_id: str = "default",
    ) -> SecretLease | None:
        if auth_mode == ProviderAuthMode.NONE:
            return None
        with self._lock:
            override = self._run_aliases.get(run_id)
            if override is not None and override[1] != profile_id:
                raise SecretLeaseError(
                    "Run session credential is bound to a different provider profile"
                )
            alias = (
                override[0]
                if override is not None
                else self._server_alias_for(profile_id)
            )
            if alias is None:
                raise SecretLeaseError(
                    f"No text-provider key is available for profile {profile_id!r}; "
                    "configure its profile-specific environment key or provide a browser-session key"
                )
            return self._vault.lease(alias, ttl_seconds=900, max_uses=1)

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER,
    ) -> SecretLease | None:
        """Lease a server-owned key for a secret-free connection probe."""

        if auth_mode == ProviderAuthMode.NONE:
            return None
        with self._lock:
            alias = self._server_alias_for(profile_id)
            if alias is None:
                raise SecretLeaseError(
                    f"No text-provider key is available for profile {profile_id!r}"
                )
            return self._vault.lease(alias, ttl_seconds=60, max_uses=1)

    def release_run(self, run_id: str) -> None:
        with self._lock:
            binding = self._run_aliases.pop(run_id, None)
            if binding:
                self._vault.remove(binding[0])

    def close(self) -> None:
        with self._lock:
            self._run_aliases.clear()
            self._server_aliases.clear()
            self._server_key_resolver = None
            self._vault.clear()


class RunSecretLeaser(Protocol):
    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode,
        profile_id: str = "default",
    ) -> SecretLease | None: ...

    def release_run(self, run_id: str) -> None: ...
