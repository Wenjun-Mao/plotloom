"""HTTP surface for the F1A review contract."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.runtime import build_runtime_app


def _settings(tmp_path: Path) -> PlotloomSettings:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<main>Plotloom</main>", encoding="utf-8")
    return PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static,
        text_auth_mode="none",
    )


def test_source_outline_http_exposes_source_candidate_and_accepted_as_distinct_records(
    tmp_path: Path,
) -> None:
    app = build_runtime_app(_settings(tmp_path))
    with TestClient(app) as client:
        created = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert created.status_code == 201, created.text
        project_id = created.json()["id"]
        initial = client.get(f"/api/v2/projects/{project_id}/source-outline")
        assert initial.status_code == 200
        assert initial.json() == {
            "source": None, "candidate": None, "acceptedOutline": None,
            "outlineStatus": "missing",
        }
        material = {
            "kind": "existing_work", "title": "渡口的信",
            "text": "一位船夫必须在暴风雨前决定把最后一封信交给谁。",
            "attribution": "作者提供的测试材料",
            "rightsDeclaration": "作者声明用于测试的许可；不是法律确认。",
            "adaptationIntent": "保留选择，并允许互动后果。",
            "inventedAdditions": "可增加目击者。",
        }
        saved = client.put(
            f"/api/v2/projects/{project_id}/source-outline/source",
            json={"expectedSourceRevision": 0, "material": material},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["source"]["material"] == material

        prepared = client.post(f"/api/v2/projects/{project_id}/source-outline/candidates")
        assert prepared.status_code == 201, prepared.text
        candidate = prepared.json()
        assert candidate["status"] == "prepared"
        assert candidate["packagePath"].endswith("/package")
        assert "cannot accept" in candidate["assignment"]
        review = client.get(f"/api/v2/projects/{project_id}/source-outline").json()
        assert review["source"]["revision"] == 1
        assert review["candidate"]["jobId"] == candidate["jobId"]
        assert review["acceptedOutline"] is None
