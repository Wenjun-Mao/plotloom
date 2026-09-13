"""Make the service-owned gateway package importable for its isolated tests."""
from __future__ import annotations

import sys
from pathlib import Path


# The repository deliberately rejects every untracked file under ``services``.
# Gateway tests import the service source directly, so disable transient .pyc
# output before that import rather than weakening the service admission rule.
sys.dont_write_bytecode = True
SERVICE_SOURCE = Path(__file__).resolve().parents[3] / "services" / "minimax_h3_gateway" / "src"
sys.path.insert(0, str(SERVICE_SOURCE))
