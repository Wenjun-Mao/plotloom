"""Passive, deletion-only metadata for the one supported prior layout."""
import json
import sqlite3
from contextlib import closing

from ..domain import ProjectBrief
from ..project_abandonment_contracts import PriorAbandonmentCandidate
from .format import (
    PROJECT_MANIFEST_FILENAME,
    ProjectStorageError,
    _read_json,
    parse_project_manifest,
)
from .operational_state import ProjectAccessLease
from .schema_upgrade import assert_prior_database, classify_layout
from .snapshot_files import _safe_regular


def prior_abandonment_candidates(registry, ledger):
    result = []
    for candidate in sorted(registry.outputs_root.iterdir()):
        if candidate.name.startswith(".") or candidate.is_symlink() or not candidate.is_dir():
            continue
        try:
            _safe_regular(candidate / PROJECT_MANIFEST_FILENAME, label="abandonment catalog manifest")
            manifest = parse_project_manifest(_read_json(candidate / PROJECT_MANIFEST_FILENAME))
            # Known-ID resolution counts every matching manifest, regardless of
            # layout; an unavailable duplicate must never confer safe identity.
            home = registry._project_home(manifest.project_id)
            if home.path != candidate.resolve() or ledger.current(manifest.project_id) is not None:
                continue
            with closing(ProjectAccessLease.acquire(candidate, mode="shared", create=False, passive=True)):
                database = candidate / manifest.database_path
                _safe_regular(database, label="abandonment catalog database")
                with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as connection:
                    connection.execute("PRAGMA query_only=ON")
                    connection.execute("PRAGMA trusted_schema=OFF")
                    connection.execute("BEGIN")
                    if classify_layout(connection) != "pre_continuation":
                        continue
                    assert_prior_database(connection, manifest.project_id, layout="pre_continuation")
                    revision, lifecycle, brief = connection.execute(
                        "SELECT revision,lifecycle_revision,brief FROM v2_projects WHERE id=?", (manifest.project_id,)).fetchone()
                    title = ProjectBrief.model_validate(json.loads(brief)).title
                    result.append(PriorAbandonmentCandidate(project_id=manifest.project_id, title=title,
                        project_revision=revision, lifecycle_revision=lifecycle))
        except (OSError, ValueError, sqlite3.Error, ProjectStorageError):
            # Unavailable metadata is not authority to open, upgrade or erase.
            continue
    return result
