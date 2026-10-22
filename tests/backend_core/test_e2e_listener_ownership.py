"""Deterministic coverage of browser-fixture port ownership, not port probing."""
import importlib.util
from pathlib import Path
import socket

import pytest


@pytest.fixture(scope="module")
def owned_listener():
    path = Path(__file__).resolve().parents[2] / "frontend/e2e/owned_listener.py"
    spec = importlib.util.spec_from_file_location("e2e_owned_listener", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.owned_loopback_listener


def test_released_port_number_is_not_a_reservation(owned_listener):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        released_port = probe.getsockname()[1]
    with socket.socket() as competing_owner:
        competing_owner.bind(("127.0.0.1", released_port))
        competing_owner.listen()
        with pytest.raises(OSError):
            with owned_listener(released_port):
                pytest.fail("must not bind an occupied port or fall back")


def test_live_owned_listeners_are_distinct_and_cannot_be_claimed(owned_listener):
    # The context is a deterministic startup barrier: serving has not begun,
    # but both addresses are already owned and never released for handoff.
    with owned_listener() as first, owned_listener() as second:
        assert first.getsockname() != second.getsockname()
        for listener in (first, second):
            with socket.socket() as competitor:
                competitor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                with pytest.raises(OSError):
                    competitor.bind(listener.getsockname())


def test_failed_startup_releases_listener_and_exact_restart_retains_address(owned_listener):
    with pytest.raises(RuntimeError, match="startup failure"):
        with owned_listener() as listener:
            original_address = listener.getsockname()
            raise RuntimeError("startup failure")
    assert listener.fileno() == -1
    with owned_listener(original_address[1]) as restarted:
        assert restarted.getsockname() == original_address


@pytest.mark.parametrize("port", [-1, 65536])
def test_invalid_fixture_ports_refuse_before_socket_allocation(owned_listener, port):
    with pytest.raises(ValueError, match="fixture listener port"):
        with owned_listener(port):
            pytest.fail("must refuse")
