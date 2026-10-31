"""Exact preserving admission for the standalone inventory table."""
from contextlib import closing
import sqlite3

from plotloom.persistence.codec import stable_hash
from plotloom.project_storage.schema_upgrade import classify_layout, logical_inventory, prior_schema_objects, upgrade_project
from plotloom.specialist_settings import SpecialistRegistry
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from tests.video_storage_fixtures import FakeH3, _fixture_app, _png


def test_exact_pre_player_layout_upgrades_without_changing_source_or_media(tmp_path):
    storage, client = _fixture_app(tmp_path, FakeH3())
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project, home = store.manifest.project_id, store.home
    asset = client.post(f"/api/v2/projects/{project}/managed-assets", files={"image": ("retained.png", _png(), "image/png")},
        data={"origin": "retained upgrade fixture", "rights": "unknown", "declared_additions_json": "[]"})
    assert asset.status_code == 201, asset.text
    with sqlite3.connect(home / "project.sqlite3") as connection:
        connection.execute("DROP TABLE v2_player_exports")
        assert classify_layout(connection) == "pre_player_export"
        before = logical_inventory(connection, prior_schema_objects("pre_player_export"))
    files = {str(path.relative_to(home)): path.read_bytes() for path in (home / "assets").rglob("*") if path.is_file()}
    receipt = upgrade_project(home, SpecialistRegistry(storage.application.root))
    assert receipt["changed"]
    with sqlite3.connect(home / "project.sqlite3") as connection:
        assert classify_layout(connection) == "current"
        for name, old in before.items():
            columns = ",".join(f'"{column}"' for column in old["columns"])
            rows = connection.execute(f'SELECT {columns} FROM "{name}"').fetchall()
            assert len(rows) == old["count"] and stable_hash(sorted(rows, key=stable_hash)) == old["hash"]
        assert connection.execute("SELECT COUNT(*) FROM v2_player_exports").fetchone()[0] == 0
    assert {str(path.relative_to(home)): path.read_bytes() for path in (home / "assets").rglob("*") if path.is_file()} == files
    with closing(storage.projects.open(project)) as reopened:
        assert reopened.manifest.project_id == project
