"""Credential-shaped input must never enter archives, receipts or error echoes."""
from contextlib import closing

import pytest
from sqlalchemy import select

from plotloom.persistence.schema import PlayerExportRow
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from tests.video_storage_fixtures import FakeH3, _fixture_app


@pytest.mark.parametrize("extra", [
    {"intro": "Bearer synthetic-test-token"},
    {"endingCards": {"ending": {"title": "Bearer synthetic-test-token", "text": "public"}}},
    {"endingCards": {"ending": {"title": "public", "text": "Bearer synthetic-test-token"}}},
    {"nodeBindings": {"apiKey": "synthetic-test-token"}},
    {"slotBindings": {"opening": "Bearer synthetic-test-token"}},
    {"slotBindings": {"sk-syntheticCredential123": "shot"}},
    {"endingCards": {"sk-syntheticCredential123": {"title": "public", "text": "public"}}},
    {"unknownField": {"nested": [{"sk-syntheticCredential123": "value"}]}},
])
def test_private_presentation_refuses_without_artifact_inventory_or_input_echo(tmp_path, extra):
    storage, client = _fixture_app(tmp_path, FakeH3())
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project, home = store.manifest.project_id, store.home
    before = set((home / "assets").rglob("*"))
    response = client.post(f"/api/v2/projects/{project}/player-exports", json={"admissionId": "not-installed", "gameId": "privacy-fixture", **extra})
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "player_export_private_material"
    assert "synthetic-test-token" not in response.text
    assert "syntheticCredential123" not in response.text
    assert set((home / "assets").rglob("*")) == before
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        assert list(session.scalars(select(PlayerExportRow))) == []
