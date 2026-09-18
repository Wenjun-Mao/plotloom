"""Credential assignments and report JavaScript equality have distinct syntax."""
import pytest

from plotloom.domain import contains_secret_value


@pytest.mark.parametrize("prose", [
    "document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });",
    "if (token == previous) return;",
])
def test_equality_expressions_are_not_credential_assignments(prose: str) -> None:
    assert not contains_secret_value(prose)


@pytest.mark.parametrize("prose", [
    "api_key=private-value",
    "key = private-value",
    "authorization=private-value",
    "Bearer private-value",
    "sk-testCredential123",
    "https://owner:private-value@example.com",
    "https://example.com?token=private-value",
])
def test_credentials_remain_forbidden(prose: str) -> None:
    assert contains_secret_value(prose)
