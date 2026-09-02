from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


class SchemaMigrator:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.script_location = Path(__file__).resolve().parent / "alembic"

    def _config(self) -> Config:
        config = Config()
        config.set_main_option("script_location", str(self.script_location))
        config.set_main_option("sqlalchemy.url", self.database_url.replace("%", "%%"))
        return config

    def upgrade(self) -> Path | None:
        config = self._config()
        scripts = ScriptDirectory.from_config(config)
        head_revision = scripts.get_current_head()
        database_path = sqlite_database_path(self.database_url)
        if database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)

        current_revision: str | None = None
        if database_path is not None and database_path.exists() and database_path.stat().st_size:
            probe = create_engine(self.database_url)
            try:
                with probe.connect() as connection:
                    current_revision = MigrationContext.configure(connection).get_current_revision()
            finally:
                probe.dispose()

        backup_path: Path | None = None
        if (
            database_path is not None
            and database_path.exists()
            and current_revision is not None
            and current_revision != head_revision
        ):
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = database_path.with_name(
                f"{database_path.name}.bak-{current_revision}-to-{head_revision}-{timestamp}"
            )
            with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as destination:
                source.backup(destination)

        command.upgrade(config, "head")
        return backup_path
