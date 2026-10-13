"""Emit complete per-file pytest phase totals for the full-suite runner."""

from __future__ import annotations

import json
from collections import defaultdict


class FilePhaseTotals:
    def __init__(self) -> None:
        self.phase_seconds: dict[str, dict[str, float]] = defaultdict(
            lambda: {"setup": 0.0, "call": 0.0, "teardown": 0.0}
        )
        self.case_ids: dict[str, set[str]] = defaultdict(set)
        self.collected_case_ids: set[str] = set()

    def pytest_collection_finish(self, session) -> None:
        self.collected_case_ids = {item.nodeid for item in session.items}

    def pytest_runtest_logreport(self, report) -> None:
        if report.when not in {"setup", "call", "teardown"}:
            return
        path = report.nodeid.split("::", 1)[0]
        self.phase_seconds[path][report.when] += float(report.duration)
        self.case_ids[path].add(report.nodeid)

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        observed_case_ids = set().union(*self.case_ids.values()) if self.case_ids else set()
        complete = exitstatus == 0 and observed_case_ids == self.collected_case_ids
        rows = self.case_ids if complete else {}
        print(
            "PYTHON_SUITE_TIMING_RUN "
            + json.dumps(
                {"complete": complete, "exitstatus": int(exitstatus), "files": len(rows)},
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
