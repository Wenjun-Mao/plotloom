"""Emit complete per-file pytest phase totals for the full-suite runner."""

from __future__ import annotations

import json
from collections import defaultdict

from scripts.testing.python_suite_completion import COMPLETION_SCHEMA_VERSION, RUN_MARKER
from scripts.testing.python_suite_schedule import native_case_fingerprint


class FilePhaseTotals:
    def __init__(self) -> None:
        self.phase_seconds: dict[str, dict[str, float]] = defaultdict(
            lambda: {"setup": 0.0, "call": 0.0, "teardown": 0.0}
        )
        self.case_ids: dict[str, set[str]] = defaultdict(set)
        self.collected_case_ids: tuple[str, ...] = ()

    def pytest_collection_finish(self, session) -> None:
        self.collected_case_ids = tuple(item.nodeid for item in session.items)

    def pytest_runtest_logreport(self, report) -> None:
        if report.when not in {"setup", "call", "teardown"}:
            return
        path = report.nodeid.split("::", 1)[0]
        self.phase_seconds[path][report.when] += float(report.duration)
        self.case_ids[path].add(report.nodeid)

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        observed_case_ids = set().union(*self.case_ids.values()) if self.case_ids else set()
        complete = (
            exitstatus == 0
            and bool(self.collected_case_ids)
            and len(self.collected_case_ids) == len(set(self.collected_case_ids))
            and observed_case_ids == set(self.collected_case_ids)
        )
        rows = self.case_ids if complete else {}
        print(
            # pytest's progress renderer can leave the current line open.
            # The machine-readable protocol always owns its full line.
            "\n" + RUN_MARKER
            + json.dumps(
                {
                    "schema_version": COMPLETION_SCHEMA_VERSION,
                    "complete": complete,
                    "exitstatus": int(exitstatus),
                    "files": len(rows),
                    "case_count": len(self.collected_case_ids),
                    "native_case_ids_sha256": native_case_fingerprint(self.collected_case_ids),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        for path in sorted(rows):
            phases = self.phase_seconds[path]
            row = {
                "path": path,
                "case_count": len(self.case_ids[path]),
                "setup_seconds": phases["setup"],
                "call_seconds": phases["call"],
                "teardown_seconds": phases["teardown"],
            }
            print(
                "PYTHON_SUITE_FILE_TIMING "
                + json.dumps(row, sort_keys=True, separators=(",", ":")),
                flush=True,
            )


def pytest_configure(config) -> None:
    config.pluginmanager.register(FilePhaseTotals(), "python-suite-file-phase-totals")
