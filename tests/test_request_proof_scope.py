"""Request-local SQL facts invalidate on writes, external commits and rollback."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from plotloom.project_storage.proof_scope import proof_scope, sql_scalar


def test_sql_scalar_is_local_and_invalidates_on_each_snapshot_change(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'proof.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE facts (value INTEGER)"))
        connection.execute(text("INSERT INTO facts VALUES (1)"))
    reads = []
    with Session(engine) as session:
        def value():
            reads.append(True)
            return session.scalar(text("SELECT value FROM facts"))
        with proof_scope():
            assert sql_scalar(session, "facts", "one", value) == 1
            assert sql_scalar(session, "facts", "one", value) == 1 and len(reads) == 1
            session.execute(text("UPDATE facts SET value=2"))
            assert sql_scalar(session, "facts", "one", value) == 2 and len(reads) == 2
            session.rollback()
            assert sql_scalar(session, "facts", "one", value) == 1 and len(reads) == 3
            with session.begin_nested() as nested:
                session.execute(text("UPDATE facts SET value=3"))
                assert sql_scalar(session, "facts", "one", value) == 3
                nested.rollback()
            assert sql_scalar(session, "facts", "one", value) == 1
            session.commit()
            with engine.begin() as other:
                other.execute(text("UPDATE facts SET value=4"))
            assert sql_scalar(session, "facts", "one", value) == 4
        with proof_scope():
            before = len(reads)
            assert sql_scalar(session, "facts", "one", value) == 4 and len(reads) == before + 1
    engine.dispose()
