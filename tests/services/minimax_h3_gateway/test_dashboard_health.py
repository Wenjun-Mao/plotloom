"""Health is an observed bounded GET, never a generation or secret-bearing proxy."""
import io
import json

from plotloom_h3_gateway.dashboard.health import HealthProbe


def test_gateway_health_is_cached_and_only_safe_observation_is_projected(monkeypatch):
    calls = []

    class Opener:
        def open(self, url, timeout):
            calls.append((url, timeout))
            return io.BytesIO(json.dumps({"status": "ok", "secret": "not-public"}).encode())

    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Opener())
    probe = HealthProbe()
    first = probe.get()
    assert first == probe.get() and len(calls) == 1
    assert calls[0] == ("http://100.64.35.71:8090/health", 3)
    assert "secret" not in first and first["status"] == "ok"


def test_gateway_health_error_is_bounded_and_does_not_return_raw_exception(monkeypatch):
    class Opener:
        def open(self, *args, **kwargs):
            raise OSError("private network details")

    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Opener())
    result = HealthProbe().get()
    assert result["status"] == "unavailable"
    assert result["error"] == "gateway_health_unavailable"
    assert "private network details" not in str(result)
