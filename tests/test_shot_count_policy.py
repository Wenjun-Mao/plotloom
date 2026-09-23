from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage


def test_new_project_defaults_to_persisted_advisory_even_when_api_omits_policy(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    client = TestClient(create_project_folder_authoring_app(storage))
    brief = FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True, exclude={"shot_count_policy"})
    response = client.post("/api/v2/projects", json={"brief": brief})
    assert response.status_code == 201, response.text
    assert response.json()["brief"]["shotCountPolicy"] == "advisory"
    assert client.get(f"/api/v2/projects/{response.json()['id']}").json()["brief"]["shotCountPolicy"] == "advisory"


def test_opening_legacy_missing_policy_keeps_strict_without_rewriting_brief(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, database = store.manifest.project_id, store.home / "project.sqlite3"
    store.close()
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT brief, revision FROM v2_projects WHERE id = ?", (project_id,)).fetchone()
        assert row is not None
        brief = json.loads(row[0])
        brief.pop("shot_count_policy")
        legacy_json = json.dumps(brief, ensure_ascii=False)
        connection.execute("UPDATE v2_projects SET brief = ? WHERE id = ?", (legacy_json, project_id))

    reopened = storage.projects.open(project_id)
    try:
        assert reopened.project().brief.shot_count_policy == "strict"
        assert reopened.project().revision == row[1]
    finally:
        reopened.close()
    with sqlite3.connect(database) as connection:
        persisted = connection.execute("SELECT brief, revision FROM v2_projects WHERE id = ?", (project_id,)).fetchone()
    assert persisted == (legacy_json, row[1])
