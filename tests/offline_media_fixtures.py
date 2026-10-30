"""Opt-in live-dispatch tripwire; injected provider/session fakes stay usable."""
from dataclasses import dataclass, field

import pytest
import requests


@dataclass
class OfflineMediaGuard:
    attempts: list[str] = field(default_factory=list)

    def refuse(self, boundary):
        # Never retain URLs, arguments or credentials in a failure receipt.
        self.attempts.append(boundary)
        raise AssertionError(f"offline media validation attempted live {boundary}")

    def assert_clean(self):
        assert not self.attempts, f"offline media validation attempted live dispatch: {self.attempts}"


def block_live_media(monkeypatch):
    from plotloom.codex_exec_host_client import CodexExecHostClient

    guard = OfflineMediaGuard()
    monkeypatch.setattr(requests.Session, "send", lambda *_a, **_k: guard.refuse("HTTP"))
    monkeypatch.setattr(CodexExecHostClient, "_codex_exec_request",
        lambda *_a, **_k: guard.refuse("native Codex host"))
    return guard


@pytest.fixture
def offline_media(monkeypatch):
    guard = block_live_media(monkeypatch)
    yield guard
    guard.assert_clean()
