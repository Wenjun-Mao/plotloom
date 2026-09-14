from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..schema import SchemaMigrator, sqlite_database_path
from .schema import Base

class RepositoryDatabase:
    """Engine and session construction with the established SQLite configuration."""
    def __init__(self, database_url: str, *, create_schema: bool, schema_tables: list[Any], schema_scope: str, sqlite_busy_timeout_ms: int) -> None:
        engine_options: dict[str, Any] = {"future": True}
        database_path = sqlite_database_path(database_url)
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
        elif database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            if create_schema and schema_scope == "full":
                SchemaMigrator(database_url).upgrade()
        self.engine = create_engine(database_url, **engine_options)
        if database_url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={sqlite_busy_timeout_ms}")
                cursor.close()
            if database_path is not None:
                with self.engine.connect() as connection:
                    current_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
                    if str(current_mode).lower() != "wal":
                        connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar_one()
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)
        self.write_lock = RLock()
        if create_schema and (database_path is None or schema_scope == "project"):
            Base.metadata.create_all(self.engine, tables=schema_tables)

    def close(self) -> None:
        self.engine.dispose()
