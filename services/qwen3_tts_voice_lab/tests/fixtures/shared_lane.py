"""Explicit non-GPU fixture using the real gateway's durable lane/dispatcher."""

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "minimax_h3_gateway" / "src"))

from plotloom_h3_gateway.lane import GenerationLane, LaneDispatcher
from plotloom_h3_gateway.store import GatewayStore
from plotloom_voice_lab.dispatch import ExecutionGrant


class SharedLaneFixture:
    def __init__(self, root):
        self.store = GatewayStore(root / "fixture-gateway.sqlite3")
        self.lane = GenerationLane(self.store)
        self.stop_event = threading.Event()

    def bind(self, worker):
        self.worker = worker
        gateway = SimpleNamespace(lane=self.lane, store=self.store)
        self.dispatcher = LaneDispatcher(gateway, self)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_event.wait(.005):
            self.dispatcher.advance()

    def register(self, body):
        return self.lane.register_voice(body["kind"], body["jobId"], body["bindingHash"])

    def progress(self, job_id):
        return self.lane.progress("voice_lab", job_id)

    def execute(self, entry):
        return self.worker.execute(ExecutionGrant(kind=entry["job_kind"], jobId=entry["job_id"],
            grantId=entry["grant_id"], bindingHash=entry["binding_hash"]))

    def execution(self, entry):
        return self.worker.store.dispatch.execution(entry["grant_id"])

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)
