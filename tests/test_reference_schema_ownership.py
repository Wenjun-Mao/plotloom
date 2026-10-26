"""Reference declarations preserve the actual pre-extraction SQLite contract."""
import json
from pathlib import Path

from sqlalchemy import create_engine

from plotloom.persistence.schema import Base


def test_reference_schema_matches_pre_extraction_ddl_and_registration(tmp_path):
    baseline = json.loads((Path(__file__).parent / 'fixtures/reference_schema_baseline.json').read_text())
    assert list(Base.metadata.tables) == baseline['registrationOrder']
    engine = create_engine(f"sqlite:///{tmp_path / 'reference.sqlite3'}")
    Base.metadata.create_all(engine)
    names = {row[2] for row in baseline['ddl']}
    with engine.connect() as connection:
        actual = [list(row) for row in connection.exec_driver_sql(
            'SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name'
        ) if row[2] in names]
        assert actual == baseline['ddl']
        for name in names:
            assert connection.exec_driver_sql(f'PRAGMA foreign_key_check({name})').all() == []
    engine.dispose()
    reopened = create_engine(f"sqlite:///{tmp_path / 'reference.sqlite3'}")
    with reopened.connect() as connection:
        for name in names:
            assert connection.execute(Base.metadata.tables[name].select()).all() == []
    reopened.dispose()
