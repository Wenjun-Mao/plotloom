"""In-memory secret vault with opaque, expiring leases.

This boundary prevents provider credentials from entering prompt variables,
request metadata, generation traces, or persisted run records. Python cannot
guarantee that temporary ``str`` copies are zeroized; the vault still wipes its
owned bytearrays when a secret is removed.
"""

from __future__ import annotations

import secrets as token_factory
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from .exceptions import SecretLeaseError


@dataclass
class _SecretRecord:
    value: bytearray


@dataclass
class _LeaseRecord:
    secret_name: str
    expires_at: float
    remaining_uses: int | None
    revoked: bool = False
    # Redaction is deliberately separate from revealing a credential.  A
    # provider adapter normally consumes its one permitted reveal before the
    # response reaches the durable evidence boundary, but that boundary still
    # has to remove an echoed credential.
    redaction_available: bool = True


class SecretLease:
    """Opaque handle that can reveal a secret only through its issuing vault."""

    __slots__ = ("_vault", "lease_id", "secret_name", "expires_at")

    def __init__(
        self,
        vault: "InMemorySecretVault",
        *,
        lease_id: str,
        secret_name: str,
        expires_at: float,
    ) -> None:
        self._vault = vault
        self.lease_id = lease_id
        self.secret_name = secret_name
        self.expires_at = expires_at

    @contextmanager
    def reveal(self) -> Iterator[str]:
        """Consume one permitted use and expose the value for a narrow scope."""

        value = self._vault._consume(self.lease_id)
        try:
            yield value
        finally:
            value = ""

    def revoke(self) -> None:
        self._vault.revoke_lease(self.lease_id)

    def redact_provider_evidence(self, value: Any) -> Any:
        """Return provider evidence with this lease's secret removed.

        This does not reveal the credential to the caller and does not consume
        a provider-use allowance.  It remains available after a one-use lease
        has been spent so the response from that exact request can be persisted
        safely; explicit revocation or secret removal disables it.
        """

        return self._vault._redact_provider_evidence(self.lease_id, value)

    def __repr__(self) -> str:
        return (
            f"SecretLease(secret_name={self.secret_name!r}, "
            f"lease_id={self.lease_id[:8]!r}..., expires_at={self.expires_at!r})"
        )


class InMemorySecretVault:
    """Thread-safe process-local secret storage.

    Secrets are intentionally not serializable. A caller stores a credential by
    alias and passes only a ``SecretLease`` to a provider adapter.
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self._secrets: dict[str, _SecretRecord] = {}
        self._leases: dict[str, _LeaseRecord] = {}

    def put(self, name: str, value: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Secret name must not be blank")
        if not isinstance(value, str) or not value:
            raise ValueError("Secret value must be a non-empty string")
        encoded = bytearray(value.encode("utf-8"))
        with self._lock:
            previous = self._secrets.pop(name, None)
            if previous is not None:
                self._wipe(previous.value)
            self._revoke_leases_for(name)
            self._secrets[name] = _SecretRecord(value=encoded)

    def lease(
        self,
        name: str,
        *,
        ttl_seconds: float = 300.0,
        max_uses: int | None = None,
    ) -> SecretLease:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        if max_uses is not None and max_uses < 1:
            raise ValueError("max_uses must be at least one when provided")
        with self._lock:
            if name not in self._secrets:
                raise SecretLeaseError(f"Unknown secret alias: {name}")
            lease_id = token_factory.token_urlsafe(32)
            expires_at = self._clock() + ttl_seconds
            self._leases[lease_id] = _LeaseRecord(
                secret_name=name,
                expires_at=expires_at,
                remaining_uses=max_uses,
            )
        return SecretLease(
            self,
            lease_id=lease_id,
            secret_name=name,
            expires_at=expires_at,
        )

    def revoke_lease(self, lease_id: str) -> None:
        with self._lock:
            record = self._leases.get(lease_id)
            if record is not None:
                record.revoked = True
                record.redaction_available = False

    def remove(self, name: str) -> None:
        with self._lock:
            record = self._secrets.pop(name, None)
            self._revoke_leases_for(name)
            if record is not None:
                self._wipe(record.value)

    def clear(self) -> None:
        with self._lock:
            names = tuple(self._secrets)
            for name in names:
                self.remove(name)

    def _consume(self, lease_id: str) -> str:
        with self._lock:
            lease = self._leases.get(lease_id)
            if lease is None:
                raise SecretLeaseError("Unknown secret lease")
            if lease.revoked:
                raise SecretLeaseError("Secret lease has been revoked")
            if self._clock() >= lease.expires_at:
                lease.revoked = True
                raise SecretLeaseError("Secret lease has expired")
            secret = self._secrets.get(lease.secret_name)
            if secret is None:
                lease.revoked = True
                raise SecretLeaseError("Secret has been removed")
            if lease.remaining_uses is not None:
                if lease.remaining_uses <= 0:
                    lease.revoked = True
                    raise SecretLeaseError("Secret lease has no remaining uses")
                lease.remaining_uses -= 1
                if lease.remaining_uses == 0:
                    lease.revoked = True
            return secret.value.decode("utf-8")

    def _redact_provider_evidence(self, lease_id: str, value: Any) -> Any:
        """Redact with an opaque lease without spending another use."""

        with self._lock:
            lease = self._leases.get(lease_id)
            secret = (
                self._secrets.get(lease.secret_name)
                if lease is not None and lease.redaction_available
                else None
            )
            known_secrets = (
                (secret.value.decode("utf-8"),) if secret is not None else ()
            )
        # Keep the credential inside the vault boundary: callers receive only
        # the sanitized copy produced by the shared response sanitizer.
        from .responses import redact_provider_response_evidence

        return redact_provider_response_evidence(value, known_secrets=known_secrets)

    def _revoke_leases_for(self, name: str) -> None:
        for lease in self._leases.values():
            if lease.secret_name == name:
                lease.revoked = True
                lease.redaction_available = False

    @staticmethod
    def _wipe(value: bytearray) -> None:
        for index in range(len(value)):
            value[index] = 0
