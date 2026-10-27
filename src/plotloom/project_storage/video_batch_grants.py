"""Nonportable batch execution grants tied to one admitted store incarnation."""
from ..exceptions import InvalidTransitionError
from .database_identity import database_identity

TABLE = "runtime_execution_grants"


class VideoBatchGrants:
    def __init__(self, application, *, initialize=True):
        self.application = application
        if not initialize:
            return
        with application._write() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS runtime_execution_grants (
                batch_id TEXT PRIMARY KEY, manifest_hash TEXT NOT NULL,
                project_id TEXT NOT NULL, home TEXT NOT NULL,
                database_identity TEXT NOT NULL)""")

    @staticmethod
    def identity(store, batch_id, manifest_hash, *, create=False):
        return (batch_id, manifest_hash, store.manifest.project_id, str(store.home.resolve()),
                database_identity(store.database_path, create=create))

    def authorize(self, store, batch_id, manifest_hash):
        identity = self.identity(store, batch_id, manifest_hash, create=True)
        with self.application._write() as connection:
            prior = connection.execute("SELECT * FROM runtime_execution_grants WHERE batch_id=?", (batch_id,)).fetchone()
            if prior is not None and tuple(prior) != identity:
                raise InvalidTransitionError("batch belongs to a different store incarnation")
            connection.execute("INSERT OR IGNORE INTO runtime_execution_grants VALUES (?,?,?,?,?)", identity)

    def require(self, store, batch_id, manifest_hash):
        with self.application._read() as connection:
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone() is None:
                raise InvalidTransitionError("batch has no execution grant on this installation")
            prior = connection.execute("SELECT * FROM runtime_execution_grants WHERE batch_id=?", (batch_id,)).fetchone()
        try:
            identity = self.identity(store, batch_id, manifest_hash) if prior is not None else None
        except InvalidTransitionError as error:
            raise InvalidTransitionError("copied/restored batch has no execution grant on this installation") from error
        if prior is None or tuple(prior) != identity:
            raise InvalidTransitionError("copied/restored batch has no execution grant on this installation")
