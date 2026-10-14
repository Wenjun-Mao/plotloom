"""One imported runner owner shared by its collection and shutdown regressions."""
import importlib.util
import json
from pathlib import Path
import sys

RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/testing/run_python_suite.py"
SPEC = importlib.util.spec_from_file_location("plotloom_python_suite", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def completion_proof(cases, **changes):
    from scripts.testing.python_suite_completion import COMPLETION_SCHEMA_VERSION, RUN_MARKER
    from scripts.testing.python_suite_schedule import native_case_fingerprint

    value = {
        "schema_version": COMPLETION_SCHEMA_VERSION, "complete": True,
        "exitstatus": 0, "files": len({case.split("::", 1)[0] for case in cases}),
        "case_count": len(cases), "native_case_ids_sha256": native_case_fingerprint(cases),
    }
    return RUN_MARKER + json.dumps(value | changes)
