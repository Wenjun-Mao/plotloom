"""In-process passive reads yield to explicit per-project lifecycle transitions.

The OS project lease remains authoritative for writers and other processes.
This arbitration adds no files, database reads, retries or lease-free admission.
"""
from pathlib import Path
from threading import Condition, Lock
from weakref import WeakValueDictionary


class ObservationGate:
    def __init__(self):
        self.condition = Condition()
        self.observers = 0
        self.transitions = 0

    def admit(self, *, transition):
        with self.condition:
            if transition:
                self.transitions += 1
                try:
                    self.condition.wait_for(lambda: self.observers == 0)
                except BaseException:
                    self.transitions -= 1
                    self.condition.notify_all()
                    raise
            else:
                self.condition.wait_for(lambda: self.transitions == 0)
                self.observers += 1
        return ObservationAdmission(self, transition)


class ObservationAdmission:
    def __init__(self, gate, transition):
        self.gate, self.transition = gate, transition
        self.closed = False

    def close(self):
        with self.gate.condition:
            if self.closed:
                return
            self.closed = True
            if self.transition:
                self.gate.transitions -= 1
            else:
                self.gate.observers -= 1
            self.gate.condition.notify_all()


_gates: WeakValueDictionary[Path, ObservationGate] = WeakValueDictionary()
_gate_lock = Lock()


def admit_project_observation(home: Path, *, transition: bool):
    key = home.resolve()
    with _gate_lock:
        gate = _gates.get(key)
        if gate is None:
            gate = ObservationGate()
            _gates[key] = gate
    return gate.admit(transition=transition)
