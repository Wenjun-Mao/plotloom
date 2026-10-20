"""Small, credential-free cache of the existing gateway's health observation."""
import json
import threading
import time
import urllib.request

from .reader import utc_now


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HealthProbe:
    def __init__(self, url="http://100.64.35.71:8090/health"):
        self.url = url
        self.lock = threading.Lock()
        self.cached = None
        self.checked = 0.0

    def get(self):
        with self.lock:
            if self.cached is not None and time.monotonic() - self.checked < 15:
                return self.cached
            observation = {"observedAt": utc_now().isoformat(), "status": "unavailable"}
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
                with opener.open(self.url, timeout=3) as response:
                    raw = response.read(65537)
                if len(raw) > 65536:
                    raise ValueError()
                payload = json.loads(raw)
                if not isinstance(payload, dict) or payload.get("status") != "ok":
                    raise ValueError()
                observation["status"] = "ok"
            except (OSError, ValueError):
                observation["error"] = "gateway_health_unavailable"
            self.cached, self.checked = observation, time.monotonic()
            return observation
