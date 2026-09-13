"""Single process-local worker for the gateway's durable FIFO queue."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import H3Gateway


class GatewayDispatchWorker:
    """Advance at most one H3/ComfyUI job at a time for one gateway database."""

    def __init__(self, gateway: H3Gateway) -> None:
        self._gateway = gateway
        self._stopped = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="plotloom-h3-dispatch", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stopped.set()
        self._thread.join(timeout=max(1.0, self._gateway.settings.request_timeout_seconds + 1.0))

    def _run(self) -> None:
        while not self._stopped.is_set():
            for operation in (
                self._gateway.cleanup_expired_outputs,
                self._gateway.cleanup_expired_gateway_keyframes,
                self._gateway.cleanup_due_job_records,
                self._gateway.dispatch_once,
            ):
                try:
                    operation()
                except Exception:
                    # Status and known job evidence are the safe recovery path;
                    # never let background cleanup or dispatch stop the worker.
                    pass
            self._stopped.wait(self._gateway.settings.worker_poll_seconds)
