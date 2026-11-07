"""Exact, lossless upgrade of the gateway's historical frame-role constraint."""

import sqlite3

PREVIOUS_TABLE = """CREATE TABLE job_frame_bindings (
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('start', 'end', 'source')),
  asset_id TEXT NOT NULL REFERENCES assets(id), prepared_input_name TEXT NOT NULL,
  PRIMARY KEY(job_id, role)
)"""
CURRENT_TABLE = PREVIOUS_TABLE.replace(
    "'start', 'end', 'source'",
    "'start', 'end', 'source', " + ", ".join(f"'reference_{index}'" for index in range(1, 10)),
)
LEGACY_TABLE = PREVIOUS_TABLE.replace("'end', 'source'", "'end'")
FRESH_TABLE = CURRENT_TABLE.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1)
ASSET_INDEX = "CREATE INDEX job_frame_bindings_asset_idx ON job_frame_bindings(asset_id)"
_COLUMNS = "job_id, role, asset_id, prepared_input_name"


def align_frame_binding_schema(connection: sqlite3.Connection) -> None:
    """Upgrade only the exact known legacy table; refuse unknown storage shapes."""

    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND lower(name)='job_frame_bindings'"
    ).fetchone()
    if row is None:
        return  # Fresh database: Store creates CURRENT_TABLE below.
    ddl = row[0]
    if ddl in (CURRENT_TABLE, FRESH_TABLE):
        return
    supported_previous = (LEGACY_TABLE, PREVIOUS_TABLE,
                          PREVIOUS_TABLE.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1))
    if ddl not in supported_previous:
        raise RuntimeError("gateway frame binding schema is unknown; migration refused")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("gateway frame binding migration requires foreign keys")

    # A table rename rewrites inbound references; never silently rewrite another
    # owner's schema, including a view or trigger that names this table.
    objects = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type IN ('table','index','view','trigger')"
    ).fetchall()
    if any(name.lower() == '__legacy_job_frame_bindings' for _, name, _, _ in objects):
        raise RuntimeError("gateway frame binding migration scratch name is occupied")
    for kind, name, table, sql in objects:
        if kind == 'table' and name.lower() != 'job_frame_bindings' and any(
            fk[2].lower() == 'job_frame_bindings'
            for fk in connection.execute(f'PRAGMA foreign_key_list("{name}")')
        ):
            raise RuntimeError("gateway frame binding schema has incoming references")
        if kind in ('view', 'trigger') and sql and 'job_frame_bindings' in sql.lower():
            raise RuntimeError("gateway frame binding schema has dependent SQL objects")
    indexes = {(kind, name, sql) for kind, name, table, sql in objects
               if table == 'job_frame_bindings' and kind in ('index', 'trigger')}
    if indexes != {('index', 'sqlite_autoindex_job_frame_bindings_1', None),
                   ('index', 'job_frame_bindings_asset_idx', ASSET_INDEX)}:
        raise RuntimeError("gateway frame binding schema has unexpected indexes or triggers")
    if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise RuntimeError("gateway frame binding migration requires valid foreign keys")

    connection.execute('SAVEPOINT frame_binding_schema')
    try:
        before = connection.execute('SELECT count(*) FROM job_frame_bindings').fetchone()[0]
        connection.execute('ALTER TABLE job_frame_bindings RENAME TO __legacy_job_frame_bindings')
        connection.execute(CURRENT_TABLE)
        connection.execute(
            f'INSERT INTO job_frame_bindings ({_COLUMNS}) '
            f'SELECT {_COLUMNS} FROM __legacy_job_frame_bindings'
        )
        after = connection.execute('SELECT count(*) FROM job_frame_bindings').fetchone()[0]
        if before != after or connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise RuntimeError("gateway frame binding migration failed integrity checks")
        connection.execute('DROP TABLE __legacy_job_frame_bindings')
        connection.execute(ASSET_INDEX)
        connection.execute('RELEASE frame_binding_schema')
    except BaseException:
        connection.execute('ROLLBACK TO frame_binding_schema')
        connection.execute('RELEASE frame_binding_schema')
        raise
