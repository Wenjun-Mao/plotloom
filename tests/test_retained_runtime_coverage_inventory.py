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
            "--require-verified-source",
            "tests/backend_core/test_pipeline.py",
            "--require-verified-source",
            "tests/backend_core/test_work_unit_persistence.py",
            "--require-verified-source",
            "tests/backend_core/test_exact_work_unit_repair_integration.py",
            "--require-verified-source",
            "tests/backend_core/test_m15_attempt_lineage.py",
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
