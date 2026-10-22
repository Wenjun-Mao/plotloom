"""Explicit bounded worker experiment using the unchanged full-suite owner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.testing.run_python_suite import run_python_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(2, 4, 8), required=True)
    arguments = parser.parse_args(argv)
    return run_python_suite(worker_count=arguments.workers)


if __name__ == "__main__":
    raise SystemExit(main())
