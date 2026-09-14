"""Keep the retirement coverage inventory tied to its historical baseline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_retained_runtime_coverage_inventory_is_complete_and_current() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/retained_runtime_coverage_inventory.py", "--check"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
