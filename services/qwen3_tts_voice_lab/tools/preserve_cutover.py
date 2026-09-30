"""Explicit idle cutover backup and additive migration proof; no data resets."""

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

from plotloom_voice_lab.media import file_sha256
from plotloom_voice_lab.store import Store


def rows(database):
    result = {}
    with sqlite3.connect(database) as db:
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            columns = [column[1] for column in db.execute(f'PRAGMA table_info("{table}")')]
            result[table] = {'columns': columns, 'rows': db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--backup-root', required=True, type=Path)
    args = parser.parse_args()
    source, backup = args.data_root.resolve(), args.backup_root.resolve()
    if not source.is_dir() or backup.exists() or not backup.parent.is_relative_to(source.parent):
        raise ValueError('cutover.invalid_scope')
    database = source / 'voice_lab.sqlite3'
    with sqlite3.connect(database) as db:
        for table in ('generations', 'clone_trials'):
            if db.execute(f"SELECT count(*) FROM {table} WHERE status IN ('queued','running')").fetchone()[0]:
                raise ValueError('cutover.busy')
    before = rows(database)
    waves = {str(path.relative_to(source)): file_sha256(path) for path in source.rglob('*.wav')}
    shutil.copytree(source, backup)
    with sqlite3.connect(database) as db, sqlite3.connect(backup / 'voice_lab.sqlite3') as dest:
        db.backup(dest)
    proof = backup / 'migration-proof'; proof.mkdir()
    shutil.copy2(backup / 'voice_lab.sqlite3', proof / 'voice_lab.sqlite3')
    Store(proof)
    with sqlite3.connect(proof / 'voice_lab.sqlite3') as db:
        for table, value in before.items():
            columns = ','.join(f'"{column}"' for column in value['columns'])
            assert db.execute(f'SELECT {columns} FROM "{table}" ORDER BY rowid').fetchall() == value['rows']
    assert all(file_sha256(backup / path) == sha for path, sha in waves.items())
    (backup / 'preservation.json').write_text(json.dumps({'tableCounts': {t: len(v['rows']) for t, v in before.items()},
        'wavHashes': waves, 'migrationPreservesOriginalColumns': True}, indent=2) + '\n')
    print(json.dumps({'backup': str(backup), 'wavCount': len(waves), 'migrationPreserved': True}))


if __name__ == '__main__': main()
