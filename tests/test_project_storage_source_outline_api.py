"""HTTP surface for the F1A review contract."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_source_outline import register_project_folder_source_outline_routes
from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.runtime import build_runtime_app


def test_outline_report_script_isolation() -> None:
    report = "<button>明细表</button><script>document.title='report'</script>"

    class ReportStore:
        def outline_candidate_report(self, job_id: str) -> str:
            assert job_id == "candidate"
            return report

    @contextmanager
    def opened(project_id: str):
        assert project_id == "project"
        yield ReportStore()

    app = FastAPI()
    register_project_folder_source_outline_routes(app, opened)
    with TestClient(app) as client:
        response = client.get("/api/v2/projects/project/source-outline/candidates/candidate/report")
    assert response.status_code == 200
    assert response.text == report
    directives = {item.strip() for item in response.headers["content-security-policy"].split(";") if item.strip()}
    assert directives == {
        "sandbox allow-scripts", "default-src 'none'", "script-src 'unsafe-inline'",
        "style-src 'unsafe-inline'", "img-src data:", "connect-src 'none'",
        "form-action 'none'", "base-uri 'none'", "frame-src 'none'",
        "object-src 'none'", "frame-ancestors 'self'",
    }
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


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
            "outlineStatus": "missing", "acceptedSectionMap": None,
            "sectionMapStatus": "missing", "sectionMapStaleReasons": [], "graphAdmission": None,
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
        assert "不要替我接受大纲，不要修改已确认内容或项目状态" in candidate["assignment"]
        assert f"{candidate['packagePath']}/COPY_ASSIGNMENT.txt" in candidate["assignment"]
        package = Path(candidate["packagePath"])
        before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in package.rglob("*") if path.is_file()}
        assignment_url = f"/api/v2/projects/{project_id}/source-outline/candidates/{candidate['jobId']}/assignment"
        recovered = client.get(assignment_url)
        assert recovered.status_code == 200, recovered.text
        for field in candidate.keys() - {"createdAt"}:
            assert recovered.json()[field] == candidate[field]
        assert before == {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in package.rglob("*") if path.is_file()}
        review = client.get(f"/api/v2/projects/{project_id}/source-outline").json()
        assert review["source"]["revision"] == 1
        assert review["candidate"]["jobId"] == candidate["jobId"]
        assert review["acceptedOutline"] is None
        (package / "COPY_ASSIGNMENT.txt").unlink()
        assert client.get(assignment_url).status_code == 409
        assert not (package / "COPY_ASSIGNMENT.txt").exists()


def test_source_outline_cancel_is_durable_and_unblocks_a_closed_project(tmp_path: Path) -> None:
    app = build_runtime_app(_settings(tmp_path))
    material = {
        "kind": "synopsis", "title": "取消测试",
        "text": "一个准备中的 handoff 必须由作者显式取消。",
        "attribution": "测试作者",
        "rightsDeclaration": "仅测试；不构成法律确认。",
        "adaptationIntent": "保留取消的明确边界。",
        "inventedAdditions": None,
    }
    with TestClient(app) as client:
        first = client.post("/api/v2/projects", json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)})
        second = client.post("/api/v2/projects", json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)})
        assert first.status_code == second.status_code == 201
        project_id = first.json()["id"]
        other_id = second.json()["id"]
        saved = client.put(f"/api/v2/projects/{project_id}/source-outline/source", json={"expectedSourceRevision": 0, "material": material})
        assert saved.status_code == 200, saved.text
        prepared = client.post(f"/api/v2/projects/{project_id}/source-outline/candidates")
        assert prepared.status_code == 201, prepared.text
        job_id = prepared.json()["jobId"]
        assert client.get(f"/api/v2/projects/{other_id}/source-outline/candidates/{job_id}/assignment").status_code == 404

        assert client.post(f"/api/v2/projects/{project_id}/close").json()["code"] == "project_busy"
        assert client.post(f"/api/v2/projects/{project_id}/snapshots").json()["code"] == "project_busy"
        assert client.post(f"/api/v2/projects/{other_id}/source-outline/candidates/{job_id}/cancel").status_code == 404

        cancelled = client.post(f"/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["candidate"]["status"] == "cancelled"
        assert client.get(f"/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/assignment").status_code == 409
        assert client.post(f"/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/refresh").json()["code"] == "delivery_cancelled"
        assert client.post(f"/api/v2/projects/{project_id}/close").status_code == 200
        closed_write = client.put(f"/api/v2/projects/{project_id}/source-outline/source", json={"expectedSourceRevision": 1, "material": material})
        assert closed_write.status_code == 409
        assert closed_write.json()["code"] == "project_closed"


def test_source_without_declarations_saves_and_handoff_does_not_invent_claims(tmp_path: Path) -> None:
    app = build_runtime_app(_settings(tmp_path))
    with TestClient(app) as client:
        created = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert created.status_code == 201, created.text
        project_id = created.json()["id"]
        material = {
            "kind": "synopsis",
            "title": "雨停以后",
            "text": "雨刚停，林遥在车站檐下选择海堤或旧街。",
            "adaptationIntent": "保留两个明确的结局。",
        }
        saved = client.put(
            f"/api/v2/projects/{project_id}/source-outline/source",
            json={"expectedSourceRevision": 0, "material": material},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["source"]["material"] == {
            **material, "attribution": None, "rightsDeclaration": None,
            "inventedAdditions": None,
        }
        prepared = client.post(f"/api/v2/projects/{project_id}/source-outline/candidates")
        assert prepared.status_code == 201, prepared.text
        request = json.loads((Path(prepared.json()["packagePath"]) / "request.json").read_text(encoding="utf-8"))
        assert request["source"]["attribution"] is None
        assert request["source"]["rightsDeclaration"] is None
        assert "without inventing missing claims" in request["creativeBrief"]

        cancelled = client.post(
            f"/api/v2/projects/{project_id}/source-outline/candidates/{prepared.json()['jobId']}/cancel"
        )
        assert cancelled.status_code == 200, cancelled.text
        revised = client.put(
            f"/api/v2/projects/{project_id}/source-outline/source",
            json={"expectedSourceRevision": 1, "material": {**material, "text": "作者修订了来源正文。"}},
        )
        assert revised.status_code == 200, revised.text
        assert revised.json()["source"]["material"]["attribution"] is None
        assert revised.json()["source"]["material"]["rightsDeclaration"] is None
