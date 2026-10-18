"""Freeze the exact immediate-prior layout while preserving all retained rows."""
import sqlite3

from plotloom.project_storage.schema_upgrade import (
    classify_layout,
    prior_schema_objects,
)


def retain_pre_continuation_layout(home):
    prior = prior_schema_objects("pre_continuation")
    run_sql = next(sql for kind, name, _, sql in prior if kind == "table" and name == "v2_autopilot_runs")
    with sqlite3.connect(home / "project.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE v2_autopilot_inheritance")
        connection.execute("DROP INDEX ix_v2_autopilot_root")
        columns = [row[1] for row in connection.execute("PRAGMA table_info(v2_autopilot_runs)") if row[1] != "predecessor_run_id"]
        projection = ",".join(f'"{name}"' for name in columns)
        connection.execute(f"CREATE TEMP TABLE retained_runs AS SELECT {projection} FROM v2_autopilot_runs")
        connection.execute("DROP TABLE v2_autopilot_runs")
        connection.execute(run_sql)
        connection.execute(f"INSERT INTO v2_autopilot_runs ({projection}) SELECT {projection} FROM retained_runs")
        connection.execute("DROP TABLE retained_runs")
        connection.commit()
        assert classify_layout(connection) == "pre_continuation"
