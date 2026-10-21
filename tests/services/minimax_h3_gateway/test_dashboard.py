"""The viewer reads live state and original bytes, never dispatches or migrates."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from plotloom_h3_gateway.dashboard.api import create_dashboard
from plotloom_h3_gateway.dashboard.reader import DashboardReader, ReadError
from plotloom_h3_gateway.store import GatewayStore

JOB = "h3_" + "a" * 32
IMAGE = "img_" + "b" * 32
CONTENT = b"original-video-fixture-0123456789"


class Health:
    def get(self):
        return {"status": "ok", "observedAt": "2026-10-20T12:00:00+00:00"}


def add_job(root, job_id=JOB, *, backend="h3_video", status="succeeded", seed=42):
    name = "2026-10-20T00-00-00Z_" + job_id + (".mp4" if backend == "h3_video" else ".png")
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    (outputs / name).write_bytes(CONTENT)
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("""INSERT INTO jobs
            (id,backend,input_mode,quality,resolution,execution_snapshot_json,aspect_policy,prompt,seed,
             requested_duration_seconds,frame_count,fps,status,managed_output_name,output_sha256,
             output_size_bytes,output_expires_at,generation_submitted_at_ms,generation_completed_at_ms)
            VALUES (?,?, 'image',8,'576x1024',?,'cover_center_crop',?, ?,15,362,24,?,?,?,?,
                    datetime('now','+1 day'),1000,5000)""",
            (job_id, backend, json.dumps({"quality": 8, "generationContractVersion": 6,
             "privatePath": "/secret/file", "secret": "never-public"}),
             "<script>window.bad=true</script> private audition", seed, status, name,
             hashlib.sha256(CONTENT).hexdigest(), len(CONTENT)))
        db.execute("UPDATE jobs SET output_mime_type=? WHERE id=?",
                   ("video/mp4" if backend == "h3_video" else "image/png", job_id))
    return outputs / name


@pytest.fixture
def installation(tmp_path):
    root = tmp_path / "data"
    GatewayStore(root / "gateway.sqlite3")
    media = add_job(root)
    app = create_dashboard(root, health=Health())
    return root, media, TestClient(app, base_url="http://localhost")


def test_reads_do_not_initialize_or_write(installation, monkeypatch):
    root, _, client = installation
    before = (root / "gateway.sqlite3").read_bytes()
    monkeypatch.setattr(GatewayStore, "__init__", lambda *_: pytest.fail("viewer must not initialize"))
    for path in ("/dashboard/", "/dashboard/api/overview", "/dashboard/api/jobs",
                 f"/dashboard/api/jobs/{JOB}", f"/dashboard/media/{JOB}"):
        assert client.get(path).status_code == 200
    assert (root / "gateway.sqlite3").read_bytes() == before
    with client.app.state.reader.connection() as db, pytest.raises(sqlite3.OperationalError):
        db.execute("DELETE FROM jobs")


def test_all_routes_are_read_only_and_do_not_publish_api(installation):
    _, _, client = installation
    assert client.post("/dashboard/api/jobs").status_code == 405
    assert client.post(f"/dashboard/media/{JOB}").status_code == 405
    for path in ("/v1/video-jobs/from-image", "/docs", "/openapi.json", "/dashboard/assets/reader.py"):
        assert client.get(path).status_code == 404
    assert client.get("/dashboard", follow_redirects=False).headers["location"] == "/dashboard/"
    assert client.get("/dashboard/api/jobs", headers={"Host": "attacker.invalid"}).status_code == 400
    assert client.get(f"/dashboard/media/{JOB}", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_light_list_excludes_prompts_paths_and_secrets(installation):
    _, _, client = installation
    response = client.get("/dashboard/api/jobs")
    row = response.json()["jobs"][0]
    assert row["requestedDurationSeconds"] == 15
    assert row["expectedDurationSeconds"] == pytest.approx(362 / 24)
    assert row["generationElapsedMs"] == 4000
    assert row["output"] == "available"
    for value in ("private audition", "privatePath", "never-public", "managed_output_name", "grant_id"):
        assert value not in response.text
    detail = client.get(f"/dashboard/api/jobs/{JOB}")
    assert detail.json()["frozenSettings"] == {"generationContractVersion": 6, "quality": 8}
    assert "never-public" not in detail.text
    prompt = client.get(f"/dashboard/api/jobs/{JOB}/prompt")
    assert prompt.json()["prompt"].startswith("<script>")
    assert prompt.headers["content-type"].startswith("application/json")


def test_pagination_filters_and_literal_search(installation):
    root, _, client = installation
    add_job(root, IMAGE, backend="qwen_image", seed=7)
    first = client.get("/dashboard/api/jobs?limit=1").json()
    second = client.get("/dashboard/api/jobs", params={"limit": 1, "cursor": first["nextCursor"]}).json()
    assert len({first["jobs"][0]["id"], second["jobs"][0]["id"]}) == 2
    assert second["nextCursor"] is None
    assert client.get("/dashboard/api/jobs?backend=qwen_image").json()["jobs"][0]["id"] == IMAGE
    assert client.get("/dashboard/api/jobs", params={"search": "%_' OR 1=1 --"}).json()["jobs"] == []
    for params in ({"cursor": "invalid"}, {"limit": 101}, {"backend": "other"}, {"status": "other"}):
        assert client.get("/dashboard/api/jobs", params=params).status_code == 422


def test_queue_positions_include_voice_hold_and_unknown_is_not_live_time(installation):
    root, _, client = installation
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("UPDATE jobs SET status='outcome_unknown',generation_completed_at_ms=NULL")
        for owner, kind, job, state, error in (
            ("voice_lab", "voice_take", "vt-example", "active", "lane.remote_unknown"),
            ("gateway", "h3_video", JOB, "queued", None),
        ):
            db.execute("INSERT INTO generation_lane(owner,job_kind,job_id,binding_hash,state,error_code) VALUES (?,?,?,'binding',?,?)",
                       (owner, kind, job, state, error))
    value = client.get("/dashboard/api/overview").json()
    assert value["active"] == 1 and value["queued"] == 1
    assert value["queue"][0]["owner"] == "voice_lab"
    assert value["queue"][1]["queueAhead"] == 1
    assert value["queue"][0]["error"] == "lane.remote_unknown"
    assert client.get(f"/dashboard/api/jobs/{JOB}").json()["generationElapsedMs"] is None


def test_new_commits_are_visible_in_delete_and_wal_modes(installation):
    root, _, client = installation
    with sqlite3.connect(root / "gateway.sqlite3") as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE jobs SET seed=91")
        writer.commit()
        assert client.get(f"/dashboard/api/jobs/{JOB}").json()["seed"] == "91"
        writer.execute("UPDATE jobs SET seed=92")
        writer.commit()
        assert client.get(f"/dashboard/api/jobs/{JOB}").json()["seed"] == "92"


def test_missing_database_or_schema_does_not_create_or_initialize(tmp_path):
    missing = tmp_path / "missing"
    reader = DashboardReader(missing)
    with pytest.raises(ReadError):
        reader.overview()
    assert not missing.exists()
    root = tmp_path / "incomplete"
    root.mkdir()
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("CREATE TABLE jobs(id TEXT)")
    client = TestClient(create_dashboard(root, health=Health()), base_url="http://localhost")
    assert client.get("/dashboard/api/overview").json()["error"] == "dashboard_schema_unavailable"
    assert client.get("/dashboard/api/jobs").status_code == 503


@pytest.mark.parametrize("value,expected", [("bytes=0-4",CONTENT[:5]), ("bytes=5-",CONTENT[5:]), ("bytes=-4",CONTENT[-4:])])
def test_ranges_and_head_preserve_exact_bytes(installation, value, expected):
    _, _, client = installation
    response = client.get(f"/dashboard/media/{JOB}", headers={"Range": value})
    assert response.status_code == 206 and response.content == expected
    assert response.headers["cache-control"] == "no-store"
    head = client.head(f"/dashboard/media/{JOB}", headers={"Range": value})
    assert head.status_code == 206 and head.content == b""
    assert int(head.headers["content-length"]) == len(expected)


@pytest.mark.parametrize("value", ["bytes=9999-", "bytes=4-1", "bytes=-0", "bytes=0-1,3-4", "bytes=a-b"])
def test_invalid_ranges(installation, value):
    _, _, client = installation
    r = client.get(f"/dashboard/media/{JOB}", headers={"Range": value})
    assert r.status_code == 416 and r.headers["content-range"] == f"bytes */{len(CONTENT)}"


def test_download_and_if_range(installation):
    _, media, client = installation
    r = client.get(f"/dashboard/media/{JOB}?download=true")
    assert r.content == CONTENT and media.name in r.headers["content-disposition"]
    assert r.headers["content-disposition"].startswith("attachment")
    assert client.get(f"/dashboard/media/{JOB}", headers={"Range": "bytes=1-2", "If-Range": '"different"'}).content == CONTENT
    image_root = client.app.state.reader.root
    add_job(image_root, IMAGE, backend="qwen_image")
    assert client.get(f"/dashboard/media/{IMAGE}").headers["content-type"] == "image/png"


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_expiry_is_checked_even_if_bytes_remain(installation, method):
    root, media, client = installation
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("UPDATE jobs SET output_expires_at=datetime('now','-1 second')")
    assert media.exists()
    response = client.request(method, f"/dashboard/media/{JOB}", headers={"Range": "bytes=0-1"})
    assert response.status_code == 410
    assert client.get(f"/dashboard/api/jobs/{JOB}").json()["output"] == "expired"


def test_missing_symlink_traversal_and_size_corruption_fail_closed(installation, tmp_path):
    root, media, client = installation
    media.unlink()
    assert client.get(f"/dashboard/media/{JOB}").status_code == 410
    foreign = tmp_path / "foreign.mp4"
    foreign.write_bytes(CONTENT)
    media.symlink_to(foreign)
    assert client.get(f"/dashboard/media/{JOB}").status_code == 410
    media.unlink()
    media.write_bytes(b"changed")
    assert client.get(f"/dashboard/media/{JOB}").status_code == 410
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("UPDATE jobs SET managed_output_name='../foreign.mp4'")
    assert client.get(f"/dashboard/media/{JOB}").status_code == 410


@pytest.mark.parametrize("mime", [None, "text/html", "image/png"])
def test_invalid_video_mime_fails_closed_for_every_media_method(installation, mime):
    root, _, client = installation
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        db.execute("UPDATE jobs SET output_mime_type=?", (mime,))
    for method in ("GET", "HEAD"):
        assert client.request(method, f"/dashboard/media/{JOB}", headers={"Range": "bytes=0-1"}).status_code == 410
    assert client.get(f"/dashboard/api/jobs/{JOB}").json()["output"] == "unavailable"


def test_locked_database_is_explicit_and_read_does_not_take_writer_ownership(installation):
    root, _, client = installation
    with sqlite3.connect(root / "gateway.sqlite3") as writer:
        writer.execute("BEGIN EXCLUSIVE")
        response = client.get("/dashboard/api/jobs")
        assert response.status_code == 503
        assert response.json()["error"] == "dashboard_database_busy"


def test_output_cleanup_between_listing_and_open_is_safe(installation, monkeypatch):
    _, media, client = installation
    reader = client.app.state.reader
    original = reader.availability

    def remove_after_check(row):
        result = original(row)
        media.unlink(missing_ok=True)
        return result

    monkeypatch.setattr(reader, "availability", remove_after_check)
    assert client.get(f"/dashboard/media/{JOB}").status_code == 410


def test_html_static_and_startup_do_not_request_credentials(installation):
    _, _, client = installation
    html = client.get("/dashboard/")
    assert "生成任务" in html.text and "password" not in html.text.lower()
    js = client.get("/dashboard/assets/dashboard.js")
    assert js.status_code == 200
    assert "innerHTML" not in js.text and "localStorage" not in js.text
    assert "Authorization" not in js.text and "autoplay" not in html.text
    assert "default-src 'self'" in html.headers["content-security-policy"]
    compose = Path("services/minimax_h3_gateway/dashboard-compose.yml").read_text()
    assert "read_only: true" in compose and "env_file" not in compose
    assert "docker.sock" not in compose and "gpus:" not in compose
