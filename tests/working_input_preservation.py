"""Exact fixture-only logical rows and immutable files for read admission tests."""
import hashlib
import sqlite3
from pathlib import Path


def preservation_inventory(root: Path):
    result = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(("-wal", "-shm")):
            continue
        if path.suffix in {".sqlite3", ".db"}:
            with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
                tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                result[str(path.relative_to(root))] = {table: sorted(connection.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr) for table in tables}
        else:
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
