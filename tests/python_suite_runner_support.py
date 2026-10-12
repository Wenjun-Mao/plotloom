"""One imported runner owner shared by its collection and shutdown regressions."""
import importlib.util
from pathlib import Path
import sys

RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/testing/run_python_suite.py"
SPEC = importlib.util.spec_from_file_location("plotloom_python_suite", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)
