from __future__ import annotations

import pytest

from plotloom.generation.exceptions import SecretLeaseError
from plotloom.generation.secrets import InMemorySecretVault


def test_secret_lease_is_opaque_and_use_limited() -> None:
    vault = InMemorySecretVault()
    vault.put("provider", "never-in-a-trace")
    lease = vault.lease("provider", max_uses=1)

    assert "never-in-a-trace" not in repr(lease)
    with lease.reveal() as value:
        assert value == "never-in-a-trace"
    with pytest.raises(SecretLeaseError, match="revoked"):
        with lease.reveal():
            pass


def test_spent_lease_redacts_provider_evidence_without_another_reveal() -> None:
    vault = InMemorySecretVault()
    vault.put("provider", "echoed-only-by-provider")
    lease = vault.lease("provider", max_uses=1)

    with lease.reveal() as value:
        assert value == "echoed-only-by-provider"

    cleaned = lease.redact_provider_evidence(
        {
            "providerDiagnostic": "request used echoed-only-by-provider",
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        }
    )

    assert cleaned == {
        "providerDiagnostic": "request used [redacted]",
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    }
    with pytest.raises(SecretLeaseError, match="revoked"):
        with lease.reveal():
            pass


def test_expired_and_replaced_secrets_invalidate_leases() -> None:
    now = [10.0]
    vault = InMemorySecretVault(clock=lambda: now[0])
    vault.put("provider", "first")
    expired = vault.lease("provider", ttl_seconds=5)
    now[0] = 15.0
    with pytest.raises(SecretLeaseError, match="expired"):
        with expired.reveal():
            pass

    old = vault.lease("provider")
    vault.put("provider", "second")
    with pytest.raises(SecretLeaseError, match="revoked"):
        with old.reveal():
            pass
