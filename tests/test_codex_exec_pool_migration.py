"""Pool-state DDL changes preserve retained rows and unrelated constraints."""
import importlib

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateTable

from plotloom.persistence.schema.project_autopilot import AutopilotExecAttemptRow

migration = importlib.import_module("plotloom.alembic.versions.0029_codex_exec_pool_states")


def test_0030_upgrade_preserves_0029_rows_and_removes_only_single_run_constraint():
    from plotloom.project_storage.schema_upgrade import prior_schema_objects
    next_migration = importlib.import_module("plotloom.alembic.versions.0030_autopilot_continuation")
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            for kind, _name, _, sql in prior_schema_objects("pre_continuation"):
                if kind == "table":
                    connection.exec_driver_sql(sql)
            connection.exec_driver_sql("INSERT INTO v2_autopilot_runs VALUES ('run','project',2,1,1,'brief','{\"retained\":\"policy\"}','hash','cancelled','source',NULL,'closure',NULL,NULL,NULL,NULL,'2026-10-16','2026-10-16')")
            before = connection.exec_driver_sql("SELECT * FROM v2_autopilot_runs").fetchall()
            columns = [column["name"] for column in sa.inspect(connection).get_columns("v2_autopilot_runs")]
            with Operations.context(MigrationContext.configure(connection)):
                next_migration.upgrade()
                next_migration.upgrade()
            assert connection.exec_driver_sql("SELECT " + ",".join(columns) + " FROM v2_autopilot_runs").fetchall() == before
            assert connection.exec_driver_sql("SELECT predecessor_run_id FROM v2_autopilot_runs").scalar() is None
            assert "v2_autopilot_inheritance" in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()


def _database(*, serial):
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE v2_autopilot_runs (id TEXT,project_id TEXT, UNIQUE(id,project_id))")
        ddl = str(CreateTable(AutopilotExecAttemptRow.__table__).compile(dialect=sqlite.dialect()))
        if serial:
            ddl = ddl.replace(migration.CURRENT_STATES, migration.SERIAL_STATES).replace(f"CONSTRAINT {migration.STATE_CONSTRAINT} ", "")
        connection.exec_driver_sql(ddl)
        connection.exec_driver_sql("""INSERT INTO v2_autopilot_exec_attempts VALUES
            ('attempt','run','project','outline','ch_aaaaaaaaaaaaaaaaaaaa','text','outcome_unknown',
            'none',0,7,'{"retained":"exact attempt bytes"}','{"retained":"exact receipt bytes"}',
            '2026-10-14','2026-10-14')""")
    return engine


@pytest.mark.parametrize("serial", [True, False])
def test_pool_state_upgrade_preserves_exact_rows_and_is_idempotent(serial):
    engine = _database(serial=serial)
    try:
        with engine.begin() as connection:
            before = connection.exec_driver_sql("SELECT * FROM v2_autopilot_exec_attempts").fetchall()
            original_guards = {str(check["sqltext"]) for check in sa.inspect(connection).get_check_constraints(migration.TABLE) if not check["sqltext"].startswith("state IN")}
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()
            assert connection.exec_driver_sql("SELECT * FROM v2_autopilot_exec_attempts").fetchall() == before
            checks = sa.inspect(connection).get_check_constraints(migration.TABLE)
            assert {check["sqltext"] for check in checks if not check["sqltext"].startswith("state IN")} == original_guards
            assert any(check["name"] == migration.STATE_CONSTRAINT and check["sqltext"] == migration.CURRENT_STATES for check in checks)
            connection.exec_driver_sql("UPDATE v2_autopilot_exec_attempts SET state='queued'")
            connection.exec_driver_sql("UPDATE v2_autopilot_exec_attempts SET state='validating'")
            with pytest.raises(sa.exc.IntegrityError):
                connection.exec_driver_sql("UPDATE v2_autopilot_exec_attempts SET domain='other'")
    finally:
        engine.dispose()


def test_pool_state_downgrade_refuses_retained_new_state():
    engine = _database(serial=False)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("UPDATE v2_autopilot_exec_attempts SET state='queued'")
            before = connection.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name=?", (migration.TABLE,)).scalar_one()
            with Operations.context(MigrationContext.configure(connection)), pytest.raises(RuntimeError, match="retained queued or validating"):
                migration.downgrade()
            assert connection.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name=?", (migration.TABLE,)).scalar_one() == before
    finally:
        engine.dispose()
