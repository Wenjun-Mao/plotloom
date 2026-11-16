"""Managed proxy trust reaches Uvicorn without widening to arbitrary callers."""

import asyncio
import json
from pathlib import Path

import manage
import pytest
from uvicorn import Config
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


@pytest.mark.parametrize("value", ["*", "192.168.156.0/24", "localhost", "127.0.0.1,", ","])
def test_proxy_trust_rejects_non_exact_addresses(value):
    with pytest.raises(ValueError, match="exact IP"):
        manage.trusted_proxy_ips(value)


def test_proxy_configuration_persists_and_reaches_uvicorn(tmp_path, monkeypatch):
    path = tmp_path / "deployment.json"
    monkeypatch.setattr(manage, "CONFIG", path)
    config = {"data": "/existing/data", "token": "/private/token", "h3_config": "/private/h3"}
    manage.configure_trusted_proxies(config, " 192.168.156.1,::1,192.168.156.1 ")
    persisted = json.loads(path.read_text())
    assert persisted == config
    assert persisted["trusted_proxy_ips"] == "192.168.156.1,::1"
    observed = {}
    monkeypatch.setattr(manage, "run", lambda command, **kwargs: observed.update(kwargs))
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    manage.compose(persisted, "config", "--quiet")
    value = observed["env"]["PLOTLOOM_CREATOR_TRUSTED_PROXY_IPS"]
    assert value == "192.168.156.1,::1"
    # This is the variable wired into the Compose service's FORWARDED_ALLOW_IPS.
    compose = Path(manage.SERVICE / "compose.yaml").read_text()
    assert "FORWARDED_ALLOW_IPS: ${PLOTLOOM_CREATOR_TRUSTED_PROXY_IPS-127.0.0.1}" in compose
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", value)
    assert Config(lambda *_: None).forwarded_allow_ips == value


def test_proxy_default_and_explicit_disable(tmp_path, monkeypatch):
    monkeypatch.setattr(manage, "CONFIG", tmp_path / "deployment.json")
    config = {"data": "/data", "token": "/token"}
    observed = {}
    monkeypatch.setattr(manage, "run", lambda command, **kwargs: observed.update(kwargs))
    manage.compose(config, "config", "--quiet")
    assert observed["env"]["PLOTLOOM_CREATOR_TRUSTED_PROXY_IPS"] == "127.0.0.1"
    manage.configure_trusted_proxies(config, "")
    manage.compose(config, "config", "--quiet")
    assert observed["env"]["PLOTLOOM_CREATOR_TRUSTED_PROXY_IPS"] == ""


@pytest.mark.parametrize("action", ["status", "logs", "stop", "check-bridge"])
def test_only_explicit_start_can_change_trust(action, monkeypatch):
    monkeypatch.setattr(manage.sys, "argv", ["manage.py", action, "--trusted-proxy-ips", "192.168.156.1"])
    monkeypatch.setattr(manage, "load_config", lambda *_: pytest.fail("configuration was touched"))
    with pytest.raises(SystemExit) as error:
        manage.main()
    assert error.value.code == 2


@pytest.mark.parametrize(
    ("peer", "forwarded", "expected"),
    [
        ("192.168.156.1", b"100.96.187.4", "100.96.187.4"),
        ("192.168.156.1", b"203.0.113.99, 100.124.174.97", "100.124.174.97"),
        ("198.51.100.2", b"100.96.187.4", "198.51.100.2"),
    ],
)
def test_deployed_proxy_chain_attribution(peer, forwarded, expected):
    observed = {}

    async def app(scope, receive, send):
        observed["client"] = scope["client"][0]

    proxy = ProxyHeadersMiddleware(app, trusted_hosts="192.168.156.1")
    scope = {"type": "http", "client": (peer, 1234), "headers": [(b"x-forwarded-for", forwarded)]}
    asyncio.run(proxy(scope, None, None))
    assert observed["client"] == expected
