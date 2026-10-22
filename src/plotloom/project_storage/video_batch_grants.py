"""Nonportable batch execution grants tied to one admitted store incarnation."""
from ..exceptions import InvalidTransitionError


class VideoBatchGrants:
    def __init__(self, application, *, initialize=True):
        self.application = application
        if not initialize:
            return
        with application._write() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS video_batch_grants (
                batch_id TEXT PRIMARY KEY, manifest_hash TEXT NOT NULL,
                project_id TEXT NOT NULL, home TEXT NOT NULL,
                database_device INTEGER NOT NULL, database_inode INTEGER NOT NULL)""")

    @staticmethod
    def identity(store, batch_id, manifest_hash):
        info = store.database_path.stat()
        return (batch_id, manifest_hash, store.manifest.project_id, str(store.home), info.st_dev, info.st_ino)

    def authorize(self, store, batch_id, manifest_hash):
        identity = self.identity(store, batch_id, manifest_hash)
        with self.application._write() as connection:
            prior = connection.execute("SELECT * FROM video_batch_grants WHERE batch_id=?", (batch_id,)).fetchone()
            if prior is not None and tuple(prior) != identity:
                raise InvalidTransitionError("batch belongs to a different store incarnation")
            connection.execute("INSERT OR IGNORE INTO video_batch_grants VALUES (?,?,?,?,?,?)", identity)

    def require(self, store, batch_id, manifest_hash):
        with self.application._read() as connection:
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='video_batch_grants'").fetchone() is None:
                raise InvalidTransitionError("batch has no execution grant on this installation")
            prior = connection.execute("SELECT * FROM video_batch_grants WHERE batch_id=?", (batch_id,)).fetchone()
        if prior is None or tuple(prior) != self.identity(store, batch_id, manifest_hash):
            raise InvalidTransitionError("copied/restored batch has no execution grant on this installation")
