"""Current-schema admission refuses retired layouts without migrating data."""

from contextlib import closing
from pathlib import Path
import json
import sqlite3

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import (
    ProjectClosedError,
    ProjectFolderStorage,
    ProjectStorageCorruptionError,
    ProjectStore,
)
from plotloom.project_storage.current_schema import assert_current_project_database
from plotloom.project_storage.recovery_validation import assert_database_contract
from plotloom.authored_route_timing import route_budget_hash
from tests.test_project_storage_art import _binding


def _project(tmp_path: Path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    home, database, manifest = store.home, store.database_path, store.manifest
    store.close()
    return storage, home, database, manifest


@pytest.mark.parametrize(
    "retired_object",
    [
        "v2_source_graph_identities",
        "v2_shot_presentations",
        "v2_video_candidate_selections",
        "v2_art_reference_proposals",
        "v2_character_imported_appearances",
        "v2_art_reference_decisions",
        "v2_production_bridge_admissions",
        "v2_production_bridge_intent_jobs",
        "v2_video_segments",
        "v2_video_end_frame_decisions",
        "v2_creative_handoff_execution_pins",
        "publication_phase",
    ],
)
@pytest.mark.parametrize("closed", [False, True])
def test_retired_schema_is_rejected_without_database_or_manifest_mutation(
    tmp_path: Path, retired_object: str, closed: bool
) -> None:
    storage, home, database, manifest = _project(tmp_path)
    if closed:
        storage.projects.close_project(manifest.project_id)
    with sqlite3.connect(database) as connection:
        if retired_object == "publication_phase":
            connection.execute(
                "ALTER TABLE v2_character_reference_proposal_deliveries DROP COLUMN publication_phase"
            )
        else:
            connection.execute(f'DROP TABLE "{retired_object}"')
    original_database = database.read_bytes()
    manifest_path = home / "project.json"
    original_manifest = manifest_path.read_bytes()
    operations = [
        lambda: ProjectStore.open(home),
        lambda: ProjectStore.open(home, read_only=True),
        lambda: storage.projects.open(manifest.project_id),
        lambda: storage.projects.inspect(manifest.project_id),
        lambda: storage.projects.reopen_project(manifest.project_id),
        lambda: assert_database_contract(database, manifest),
    ]
    for operation in operations:
        with pytest.raises(ProjectStorageCorruptionError, match="schema"):
            operation()
        assert database.read_bytes() == original_database
        assert manifest_path.read_bytes() == original_manifest
    assert storage.projects.discover() == []
    assert database.read_bytes() == original_database
    assert manifest_path.read_bytes() == original_manifest


@pytest.mark.parametrize(
    "mutation",
    [
        "CREATE TABLE unexpected (id TEXT)",
        "CREATE VIEW unexpected AS SELECT id FROM v2_projects",
        "CREATE TRIGGER unexpected AFTER UPDATE ON v2_projects BEGIN SELECT 1; END",
        "ALTER TABLE v2_projects ADD COLUMN unexpected TEXT",
    ],
)
def test_unknown_schema_objects_are_rejected(tmp_path: Path, mutation: str) -> None:
    _storage, home, database, _manifest = _project(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(mutation)
    with pytest.raises(ProjectStorageCorruptionError, match="schema"):
        ProjectStore.open(home)


def test_current_schema_identity_must_match_manifest(tmp_path: Path) -> None:
    _storage, home, database, _manifest = _project(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE v2_project_operational_states SET project_id = 'wrong-project'"
        )
    with pytest.raises(ProjectStorageCorruptionError, match="identity"):
        ProjectStore.open(home)


def test_schema_admission_reads_committed_wal_schema(tmp_path: Path) -> None:
    _storage, home, database, manifest = _project(tmp_path)
    with closing(sqlite3.connect(database)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        original_database = database.read_bytes()
        writer.execute("DROP TABLE v2_source_graph_identities")
        writer.commit()
        assert database.read_bytes() == original_database
        with pytest.raises(ProjectStorageCorruptionError, match="schema"):
            assert_current_project_database(database, manifest.project_id)
        with pytest.raises(ProjectStorageCorruptionError, match="schema"):
            ProjectStore.open(home)
        assert database.read_bytes() == original_database


def test_current_schema_open_observes_closed_state_in_committed_wal(
    tmp_path: Path,
) -> None:
    storage, _home, database, manifest = _project(tmp_path)
    with closing(sqlite3.connect(database)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        writer.execute("UPDATE v2_project_operational_states SET state = 'closed'")
        writer.commit()
        assert_current_project_database(database, manifest.project_id)
        with pytest.raises(ProjectClosedError):
            storage.projects.open(manifest.project_id)
        with closing(storage.projects.inspect(manifest.project_id)) as inspected:
            assert inspected.repository.operational_state()[0] == "closed"


@pytest.mark.parametrize("stage", ["script", "storyboard_review"])
@pytest.mark.parametrize("kind", ["candidates", "revisions"])
@pytest.mark.parametrize("closed", [False, True])
def test_obsolete_review_json_rejected_before_open_or_recovery_mutation(
    tmp_path: Path, stage: str, kind: str, closed: bool,
) -> None:
    storage, home, database, manifest = _project(tmp_path)
    if closed:
        storage.projects.close_project(manifest.project_id)
    raw = _binding().model_dump(mode="json", by_alias=True)
    bindings = [{"sectionId": node, "episode": i + 1} for i, node in enumerate(raw["sectionIds"])]
    routes = [["opening", "ending-a"], ["opening", "ending-b"]]
    raw.update(artRevision=1, artContentHash="f" * 64,
               targetPlaythroughSeconds=15, sectionBindings=bindings,
               completeRouteSectionIds=routes, routeOnlySectionIds=[],
               routeBudgetHash=route_budget_hash(target_seconds=15, section_bindings=bindings,
                                                 routes=routes, route_only_ids=[]))
    payload_column = "script" if stage == "script" else "storyboard"
    if stage == "storyboard_review":
        raw.update(scriptRevision=1, scriptContentHash="a" * 64,
                   reviewMinCutSeconds=2, reviewMaxCutSeconds=8, reviewMaxSegmentSeconds=15)
    values = {"project_id": manifest.project_id, "binding": json.dumps(raw), payload_column: "{}"}
    if kind == "candidates":
        values.update(job_id="ch_" + "z" * 32, request="{}", status="cancelled",
                      created_at="2026-10-08T00:00:00",
                      **{f"expected_{'script' if stage == 'script' else 'review'}_revision": 0})
    else:
        values.update(id="review-fixture", revision=1, candidate_job_id="ch_" + "z" * 32,
                      content_hash="b" * 64, accepted_at="2026-10-08T00:00:00")
    table = f"v2_{stage}_{kind}"
    with sqlite3.connect(database) as connection:
        connection.execute(f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join('?' for _ in values)})",
                           tuple(values.values()))
    # The current contract admits even closed folders; the JSON change alone
    # must trigger refusal, not the presence of review rows or operational state.
    assert_current_project_database(database, manifest.project_id)
    assert_database_contract(database, manifest)
    raw.pop("routeBudgetHash")
    raw.update(timingAllocationHash="c" * 64, sectionDurationCaps=[])
    with sqlite3.connect(database) as connection:
        connection.execute(f"UPDATE {table} SET binding = ?", (json.dumps(raw),))
    original = database.read_bytes()
    manifest_bytes = (home / "project.json").read_bytes()
    for operation in (
        lambda: ProjectStore.open(home),
        lambda: ProjectStore.open(home, read_only=True),
        lambda: storage.projects.open(manifest.project_id),
        lambda: storage.projects.inspect(manifest.project_id),
        lambda: storage.projects.reopen_project(manifest.project_id),
        lambda: assert_database_contract(database, manifest),
    ):
        with pytest.raises(ProjectStorageCorruptionError, match="review contract.*explicit.*reset"):
            operation()
        assert database.read_bytes() == original
        assert (home / "project.json").read_bytes() == manifest_bytes
    assert storage.projects.discover() == []
