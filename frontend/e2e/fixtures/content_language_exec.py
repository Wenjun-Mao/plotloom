"""Request-scoped profile for completed synthetic checks; no offline dispatch."""
from contextlib import contextmanager
from contextvars import ContextVar
from types import SimpleNamespace
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from plotloom.exceptions import InvalidTransitionError
from tests.codex_exec_fixtures import install_profile

_ACTIVE = ContextVar("browser_completed_language_check", default=False)
_CHECK = re.compile(r"/api/v2/projects/[^/]+/(?:specialist-tasks|content-language)/(?:outline|branches|characters|art|script|storyboard|bridge-intent|bridge-presentation)/[^/]+/check")


def install(app):
    registry = app.state.specialists
    fixture = install_profile(SimpleNamespace(host_client=SimpleNamespace()))
    original_profile = registry.codex_exec_profile
    registry.codex_exec_profile = lambda: fixture.codex_exec_profile() if _ACTIVE.get() else original_profile()

    def closed(original):
        def call(*args, **kwargs):
            if _ACTIVE.get():
                raise InvalidTransitionError("Offline explicit checks require completed synthetic evidence; host execution is closed.")
            return original(*args, **kwargs)
        return call

    for name in ("require_codex_exec_readiness", "codex_exec_admit", "codex_exec_status",
                 "codex_exec_cancel", "codex_exec_suspend", "codex_exec_resume"):
        setattr(registry, name, closed(getattr(registry, name)))


@contextmanager
def explicit_check_scope(method, path):
    token = _ACTIVE.set(method == "POST" and _CHECK.fullmatch(path) is not None)
    try:
        yield
    finally:
        _ACTIVE.reset(token)
