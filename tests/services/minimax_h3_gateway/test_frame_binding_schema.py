"""Historical H3 frame-binding migration; no provider or network calls."""

import hashlib
import sqlite3
from pathlib import Path

import pytest
from plotloom_h3_gateway import frame_binding_schema as schema
from plotloom_h3_gateway.store import GatewayStore


def _db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    return db


def _legacy(path: Path) -> None:
    GatewayStore(path)
    with _db(path) as db:
        db.execute('DROP TABLE job_frame_bindings')
        db.execute(schema.LEGACY_TABLE)
        db.execute(schema.ASSET_INDEX)
        db.execute("INSERT INTO assets (id,mime_type,width,height,sha256,path) VALUES ('a','image/png',832,480,'hash','/private/a')")
        db.execute("INSERT INTO assets (id,mime_type,width,height,sha256,path) VALUES ('b','image/png',832,480,'hash2','/private/b')")
        db.execute("""INSERT INTO jobs (id,input_mode,quality,resolution,execution_snapshot_json,prompt,seed,
                    requested_duration_seconds,frame_count,fps,status)
                    VALUES ('j','image',8,'832x480','{}','retained',9223372036854775807,12,294,24,'succeeded')""")
        db.execute("INSERT INTO job_frame_bindings VALUES ('j','start','a','start.png')")
        db.execute("INSERT INTO job_frame_bindings VALUES ('j','end','b','end.png')")
        db.execute("""INSERT INTO job_voice_bindings (job_id,source_sha256,prepared_sha256,source_size_bytes,
                    duration_ms,source_name,prepared_input_name) VALUES ('j','v1','v2',9223372036854775807,
                    1000,'audio.wav','prepared.wav')""")


def _fingerprint(db: sqlite3.Connection) -> dict[str, tuple[int, str]]:
    names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    result = {}
    for name in names:
        rows = db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
        result[name] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
    return result


def test_populated_legacy_migrates_losslessly_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / 'gateway.sqlite3'
    _legacy(path)
    with _db(path) as db:
        before = _fingerprint(db)
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='job_frame_bindings'").fetchone()[0] == schema.LEGACY_TABLE
    GatewayStore(path)
    with _db(path) as db:
        assert _fingerprint(db) == before
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='job_frame_bindings'").fetchone()[0] == schema.CURRENT_TABLE
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute("SELECT seed FROM jobs WHERE id='j'").fetchone()[0] == 9223372036854775807
        assert db.execute("SELECT source_size_bytes FROM job_voice_bindings WHERE job_id='j'").fetchone()[0] == 9223372036854775807
        db.execute("INSERT INTO job_frame_bindings VALUES ('j','source','b','source.png')")
        with pytest.raises(sqlite3.IntegrityError, match='CHECK'):
            db.execute("INSERT INTO job_frame_bindings VALUES ('j','other','b','bad.png')")
        with pytest.raises(sqlite3.IntegrityError, match='UNIQUE'):
            db.execute("INSERT INTO job_frame_bindings VALUES ('j','start','b','duplicate.png')")
        with pytest.raises(sqlite3.IntegrityError, match='FOREIGN KEY'):
            db.execute("INSERT INTO job_frame_bindings VALUES ('missing','start','b','orphan.png')")
        db.execute("""INSERT INTO jobs (id,input_mode,quality,resolution,execution_snapshot_json,prompt,seed,
                    requested_duration_seconds,frame_count,fps,status)
                    VALUES ('k','image',8,'832x480','{}','second',1,12,294,24,'queued')""")
        with pytest.raises(sqlite3.IntegrityError, match='FOREIGN KEY'):
            db.execute("INSERT INTO job_frame_bindings VALUES ('k','start','missing','orphan.png')")
    GatewayStore(path)
    with _db(path) as db:
        assert db.execute("SELECT role FROM job_frame_bindings ORDER BY role").fetchall() == [('end',), ('source',), ('start',)]
        assert db.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='job_frame_bindings' ORDER BY name").fetchall() == [
            ('job_frame_bindings_asset_idx',), ('sqlite_autoindex_job_frame_bindings_1',)]


def test_migration_failure_rolls_back_table_and_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / 'gateway.sqlite3'
    _legacy(path)
    with _db(path) as db:
        before = _fingerprint(db)
    monkeypatch.setattr(schema, 'CURRENT_TABLE', 'CREATE TABLE job_frame_bindings (bad TEXT)')
    with pytest.raises(sqlite3.OperationalError):
        GatewayStore(path)
    with _db(path) as db:
        assert _fingerprint(db) == before
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='job_frame_bindings'").fetchone()[0] == schema.LEGACY_TABLE
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


@pytest.mark.parametrize('mutate', [
    "CREATE INDEX unexpected_frame_idx ON job_frame_bindings(prepared_input_name)",
    "CREATE TABLE dependent (job_id TEXT, role TEXT, FOREIGN KEY(job_id,role) REFERENCES job_frame_bindings(job_id,role))",
    "CREATE TRIGGER frame_audit AFTER INSERT ON job_frame_bindings BEGIN SELECT 1; END",
])
def test_unknown_dependent_schema_refuses_unchanged(tmp_path: Path, mutate: str) -> None:
    path = tmp_path / 'gateway.sqlite3'
    _legacy(path)
    with _db(path) as db:
        db.execute(mutate)
        before = _fingerprint(db)
    with pytest.raises(RuntimeError, match='frame binding'):
        GatewayStore(path)
    with _db(path) as db:
        assert _fingerprint(db) == before
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='job_frame_bindings'").fetchone()[0] == schema.LEGACY_TABLE


def test_case_insensitive_incoming_fk_refuses_before_cascade(tmp_path: Path) -> None:
    path = tmp_path / 'gateway.sqlite3'
    _legacy(path)
    with _db(path) as db:
        db.execute('''CREATE TABLE dependent (job_id TEXT, role TEXT,
                   FOREIGN KEY(job_id,role) REFERENCES JOB_FRAME_BINDINGS(job_id,role) ON DELETE CASCADE)''')
        db.execute("INSERT INTO dependent VALUES ('j','start')")
        before = _fingerprint(db)
    with pytest.raises(RuntimeError, match='incoming references'):
        GatewayStore(path)
    with _db(path) as db:
        assert _fingerprint(db) == before
        assert db.execute('SELECT count(*) FROM dependent').fetchone()[0] == 1


def test_unknown_role_constraint_refuses_unchanged(tmp_path: Path) -> None:
    path = tmp_path / 'gateway.sqlite3'
    GatewayStore(path)
    with _db(path) as db:
        db.execute('DROP TABLE job_frame_bindings')
        db.execute(schema.LEGACY_TABLE.replace("'start', 'end'", "'start', 'end', 'other'"))
        before = _fingerprint(db)
    with pytest.raises(RuntimeError, match='unknown'):
        GatewayStore(path)
    with _db(path) as db:
        assert _fingerprint(db) == before
