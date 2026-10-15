"""The public bridge freezes the persisted host capacity, including narrow proofs."""
import pytest
from codex_exec_supervisor_test_support import _write_fake_cli
from host_bridge import QueueBridge

from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits


def test_bridge_profile_observes_same_persisted_pool_after_reopen(supervisor, tmp_path):
    _write_fake_cli(supervisor, "raise SystemExit(0)\n")
    limits = CodexExecPoolLimits(maxProcesses=1, maxTextProcesses=1, maxImageProcesses=1, maxQueuedJobs=4)
    private_root = tmp_path / "serial-private"
    bridge = QueueBridge(supervisor.executable, tmp_path / "settings", "fixture-token",
        source_root=supervisor.source_root, outputs_root=supervisor.outputs_root,
        private_root=private_root, pool_limits=limits)
    profile = bridge.exec_profile()
    assert profile["maxProcesses"] == profile["maxTextProcesses"] == profile["maxImageProcesses"] == 1
    assert profile == bridge.exec_supervisor().profile().model_dump(mode="json", by_alias=True)
    reopened = QueueBridge(supervisor.executable, tmp_path / "settings", "fixture-token",
        source_root=supervisor.source_root, outputs_root=supervisor.outputs_root, private_root=private_root)
    assert reopened.exec_profile() == profile
    assert not bridge.exec_supervisor()._workers and not reopened.exec_supervisor()._workers
    conflicting = QueueBridge(supervisor.executable, tmp_path / "settings", "fixture-token",
        source_root=supervisor.source_root, outputs_root=supervisor.outputs_root,
        private_root=private_root, pool_limits=CodexExecPoolLimits())
    with pytest.raises(ValueError, match="persisted pool limits cannot change"):
        conflicting.exec_profile()
