"""Keep the retirement coverage inventory tied to its historical baseline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_retained_runtime_coverage_inventory_is_complete_and_current() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/retained_runtime_coverage_inventory.py",
            "--check",
            "--require-verified-entry",
            "tests/backend_core/test_pipeline.py::test_storyboard_audio_timing_uses_exact_frozen_repair_fact",
            "--require-verified-entry",
            "tests/backend_core/test_pipeline.py::test_cue_order_fact_rejects_rebound_membership_before_dispatch",
            "--require-verified-entry",
            "tests/backend_core/test_work_unit_persistence.py::test_duplicate_producer_artifacts_are_rejected_before_they_can_be_sealed",
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
