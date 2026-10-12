"""Explicit, idle, preserving transition from the single frozen prior layout."""
from importlib.resources import files
import json
from pathlib import Path
import sqlite3

from ..persistence.codec import stable_hash
from .current_schema import assert_current_review_bindings, expected_project_schema_objects, schema_objects
from .format import PROJECT_MANIFEST_FILENAME, ProjectStorageError, ProjectStorageCorruptionError, _read_json, parse_project_manifest
from .operational_state import ProjectAccessLease, ProjectBusyError
from .snapshot_files import _safe_directory, _safe_regular

PRIOR_LAYOUT_HASH = "ea9facef83198e8b5abdd8693923f51add1376c0b416041dbfa245b92011b825"


def prior_schema_objects():
    """Packaged immutable authority; never inferred by subtracting new tables."""
    raw = files("plotloom.project_storage").joinpath("schema_layouts/pre_autopilot.json").read_text(encoding="utf-8")
    objects = tuple(tuple(item) for item in json.loads(raw))
    if stable_hash(objects) != PRIOR_LAYOUT_HASH:
        raise ProjectStorageCorruptionError("frozen prior schema authority is corrupt")
    return objects


def classify_layout(connection):
    actual = schema_objects(connection)
    if actual == expected_project_schema_objects():
        return "current"
    return "prior" if actual == prior_schema_objects() else "unsupported"


def inventory_layouts(outputs_root: Path):
    """Raw manifest inventory includes unavailable folders; never calls discover."""
    root = _safe_directory(outputs_root, label="upgrade inventory root")
    result = []
    for home in sorted(root.iterdir()):
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        if home.name.startswith("."):
            continue
        item = {"folder": home.name, "layout": "unmanaged"}
        if not home.is_symlink() and home.is_dir() and manifest_path.exists():
            try:
                _safe_regular(manifest_path, label="upgrade manifest")
                manifest = parse_project_manifest(_read_json(manifest_path))
                database = home / manifest.database_path
                _safe_regular(database, label="upgrade database")
                connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
                try:
                    connection.execute("PRAGMA query_only=ON")
                    connection.execute("PRAGMA trusted_schema=OFF")
                    item.update(projectId=manifest.project_id, layout=classify_layout(connection))
                finally:
                    connection.close()
            except (ValueError, OSError, sqlite3.Error, ProjectStorageError) as error:
                item.update(layout="error", reason=str(error))
        result.append(item)
    return result


def logical_inventory(connection, objects):
    result = {}
    for kind, name, _table, _sql in objects:
        if kind != "table":
            continue
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')]
        rows = list(connection.execute(f'SELECT {",".join(chr(34)+column+chr(34) for column in columns)} FROM "{name}"'))
        result[name] = {"columns": columns, "count": len(rows), "hash": stable_hash(sorted(rows, key=stable_hash))}
    return result


def assert_prior_database(connection, project_id):
    if schema_objects(connection) != prior_schema_objects():
        raise ProjectStorageCorruptionError("explicit upgrade requires the exact immediate-prior layout")
    assert_current_review_bindings(connection)
    assert_integrity_identity(connection, project_id)


def assert_integrity_identity(connection, project_id):
    if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"] or list(connection.execute("PRAGMA foreign_key_check")):
        raise ProjectStorageCorruptionError("upgrade database integrity or foreign keys failed")
    if list(connection.execute("SELECT id FROM v2_projects")) != [(project_id,)]:
        raise ProjectStorageCorruptionError("upgrade database project identity changed")
    states = list(connection.execute("SELECT project_id, state FROM v2_project_operational_states"))
    if len(states) != 1 or states[0][0] != project_id or states[0][1] not in {"open", "closed"}:
        raise ProjectStorageCorruptionError("upgrade operational identity is invalid")


def assert_idle_prior(connection):
    for table, column, states in (
        ("v2_generation_runs", "status", "'queued','running','cancel_requested'"),
        ("v2_media_tasks", "status", "'queued','running'"),
        ("v2_video_jobs", "state", "'prepared','dispatching','submitted','retrieve_needed','outcome_unknown'"),
        ("v2_image_jobs", "state", "'prepared','exported'"),
        ("v2_character_reference_proposals", "state", "'prepared','exported'"),
        ("v2_art_reference_proposals", "state", "'prepared','exported'"),
        ("v2_production_bridge_intent_jobs", "status", "'queued','dispatched','outcome_unknown'"),
        *((table, "status", "'prepared'") for table in ("v2_source_outline_candidates", "v2_cast_candidates", "v2_art_candidates", "v2_script_candidates", "v2_storyboard_review_candidates")),
    ):
        if connection.execute(f'SELECT 1 FROM "{table}" WHERE "{column}" IN ({states}) LIMIT 1').fetchone():
            raise ProjectBusyError(f"upgrade refuses unresolved work in {table}")
    if connection.execute("SELECT 1 FROM v2_production_bridge_intent_jobs WHERE transport='codex_native' AND status='cancelled' AND dispatched_at IS NOT NULL AND response_evidence IS NULL LIMIT 1").fetchone():
        raise ProjectBusyError("upgrade refuses an unresolved cancelled native publication")


def upgrade_database(connection, project_id, *, after_ddl=None, require_idle=True):
    """Transactional DDL, including the exclusive image-unit authority union."""
    from ..domain import contains_secret_value
    from .recovery_validation import _contains_forbidden_database_setting
    layout = classify_layout(connection)
    if layout == "current":
        assert_integrity_identity(connection, project_id)
        return {"layout": "current", "changed": False}
    assert_prior_database(connection, project_id)
    if require_idle:
        assert_idle_prior(connection)
    before = logical_inventory(connection, prior_schema_objects())
    for name, inventory in before.items():
        for row in connection.execute(f'SELECT * FROM "{name}"'):
            for value in row:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                    if contains_secret_value(value) or _contains_forbidden_database_setting(value):
                        raise ProjectStorageCorruptionError("upgrade refuses forbidden secret material")
    current = expected_project_schema_objects()
    prior_names = {item[1] for item in prior_schema_objects()}
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        # Recheck under the write lock, so a stale preflight cannot admit a
        # concurrent layout/state/content change.
        assert_prior_database(connection, project_id)
        if require_idle:
            assert_idle_prior(connection)
        if logical_inventory(connection, prior_schema_objects()) != before:
            raise ProjectStorageCorruptionError("upgrade inputs changed before write admission")
        for kind, name, _table, sql in current:
            if kind == "table" and name not in prior_names:
                connection.execute(sql)
        unit_columns = before["v2_production_units"]["columns"]
        projection = ",".join(f'"{column}"' for column in unit_columns)
        connection.execute("CREATE TEMP TABLE autopilot_unit_transfer AS SELECT * FROM v2_production_units")
        connection.execute("DROP TABLE v2_production_units")
        connection.execute(next(sql for kind, name, _, sql in current if kind == "table" and name == "v2_production_units"))
        connection.execute(f"INSERT INTO v2_production_units ({projection}) SELECT {projection} FROM autopilot_unit_transfer")
        connection.execute("DROP TABLE autopilot_unit_transfer")
        existing = {item[1] for item in schema_objects(connection)}
        for kind, name, _table, sql in current:
            if kind == "index" and name not in existing:
                connection.execute(sql)
        if after_ddl:
            after_ddl(connection)
        if schema_objects(connection) != current:
            raise ProjectStorageCorruptionError("upgrade did not establish the exact current layout")
        assert_integrity_identity(connection, project_id)
        # Compare the old column projection rather than interpreting new NULL
        # authority columns as changes to retained human decisions.
        after = {}
        for name, inventory in before.items():
            columns = inventory["columns"]
            rows = list(connection.execute(f'SELECT {",".join(chr(34)+column+chr(34) for column in columns)} FROM "{name}"'))
            after[name] = {"columns": columns, "count": len(rows), "hash": stable_hash(sorted(rows, key=stable_hash))}
        if after != before:
            raise ProjectStorageCorruptionError("upgrade changed retained project rows")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
    return {"layout": "current", "changed": True, "priorLayoutHash": PRIOR_LAYOUT_HASH,
            "currentLayoutHash": stable_hash(current), "retainedRowsHash": stable_hash(before)}


def upgrade_project(home: Path, registry, *, after_ddl=None):
    """Named operator boundary; caller supplies the installation native owner."""
    home = _safe_directory(home, label="upgrade project home")
    lease = ProjectAccessLease.acquire(home, mode="exclusive")
    try:
        with registry.idle_guard():
            manifest_path = home / PROJECT_MANIFEST_FILENAME
            _safe_regular(manifest_path, label="upgrade manifest")
            manifest = parse_project_manifest(_read_json(manifest_path))
            database = home / manifest.database_path
            _safe_regular(database, label="upgrade database")
            with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as admitted:
                admitted.execute("PRAGMA trusted_schema=OFF")
                layout = classify_layout(admitted)
                if layout == "prior":
                    assert_prior_database(admitted, manifest.project_id)
                elif layout == "current":
                    assert_integrity_identity(admitted, manifest.project_id)
                else:
                    raise ProjectStorageCorruptionError("explicit upgrade requires the exact immediate-prior layout")
            from .recovery_validation import payload_paths, payload_inventory, assert_payload_inventory
            from .recovery_validation import assert_database_contract
            assert_database_contract(database, manifest, allow_previous=True)
            from .snapshot_files import _assert_exchange_file_is_secret_free
            from .recovery_validation import referenced_asset_paths
            inventory = payload_inventory(home, payload_paths(home, database))
            for relative in inventory:
                if relative.parts[:1] in {("runs",), ("outputs",)}:
                    _assert_exchange_file_is_secret_free(home.joinpath(*relative.parts))
            for relative in referenced_asset_paths(database):
                if inventory[relative].content_hash != relative.name:
                    raise ProjectStorageCorruptionError("upgrade retained asset bytes changed")
            connection = sqlite3.connect(database)
            try:
                connection.execute("PRAGMA trusted_schema=OFF")
                def admitted_ddl(owned):
                    if after_ddl:
                        after_ddl(owned)
                    # Check every admitted file before committing schema mutation.
                    # The database itself has intentionally changed inside this transaction.
                    assert_payload_inventory(home, {path: item for path, item in inventory.items() if path.as_posix() != manifest.database_path})
                return upgrade_database(connection, manifest.project_id, after_ddl=admitted_ddl)
            finally:
                connection.close()
    finally:
        lease.close()
