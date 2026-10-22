"""One in-process use of the existing QueueBridge and Mac supervisor owners."""
import secrets
import sys
from pathlib import Path

from plotloom.codex_exec_contracts import CodexExecProfile, CodexExecReadiness
from plotloom.image_job_contracts import ImageJobError


class OutlineExecRegistry:
    """Only the existing core Exec operations; no specialist queue or new host."""
    def __init__(self, bridge):
        self.bridge = bridge

    def codex_exec_profile(self):
        return CodexExecProfile.model_validate(self.bridge.exec_profile())

    def require_codex_exec_readiness(self) -> CodexExecReadiness:
        readiness = CodexExecReadiness.model_validate(self.bridge.exec_readiness())
        if readiness.state != "ready":
            raise ImageJobError("codex_exec_unavailable", "The frozen Codex Exec host is not ready.")
        return readiness

    def codex_exec_admit(self, attempt):
        return self.bridge.exec_supervisor().admit(attempt)

    def codex_exec_status(self, attempt_id):
        return self.bridge.exec_supervisor().status(attempt_id)

    def codex_exec_suspend(self, attempt):
        return self.bridge.exec_supervisor().suspend(attempt)


def compose_registry(source_root, executable, application, outputs, private, *, limits, namespace_pin=None):
    service = Path(source_root) / "services/creator_workbench"
    if str(service) not in sys.path:
        sys.path.insert(0, str(service))
    from host_bridge import QueueBridge
    # This existing bridge is used in process. No listener, token file, shim,
    # ambient endpoint or general queue is exposed by this composition.
    bridge = QueueBridge(Path(executable), Path(application) / "specialists/settings.json",
        secrets.token_urlsafe(32), source_root=Path(source_root), outputs_root=Path(outputs),
        private_root=Path(private), pool_limits=limits, namespace_binding_sha256=namespace_pin)
    return OutlineExecRegistry(bridge)
