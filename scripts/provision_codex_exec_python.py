"""Explicitly provision this checkout's checked-lock Codex Python validators."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "src"))

from plotloom.codex_exec_python_environment import provision_checked_python_environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True, help="exact physical versioned Python interpreter")
    parser.add_argument("--uv", type=Path, required=True, help="installed uv executable")
    args = parser.parse_args()
    environment = provision_checked_python_environment(SOURCE_ROOT, interpreter=args.python, uv=args.uv)
    print(json.dumps({"environment": str(environment.root), "identitySha256": environment.identity_hash}))


if __name__ == "__main__":
    main()
