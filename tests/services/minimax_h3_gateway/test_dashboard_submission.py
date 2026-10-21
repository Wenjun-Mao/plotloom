"""The console delegates to the existing API exactly once without browser keys."""
import itertools
import json

import pytest
import requests
from fastapi.testclient import TestClient
from plotloom_h3_gateway.dashboard.api import create_dashboard
from plotloom_h3_gateway.dashboard.submission import (
    GATEWAY_IMAGE_URL,
    MAX_BODY,
    GatewaySubmission,
    SubmissionError,
)

ID = "h3_" + "c" * 32
ORIGIN = {"Origin": "http://localhost:8091", "X-Dashboard-Request": "1", "Sec-Fetch-Site": "same-origin"}
FIELDS = {"prompt": "雨停了，出发吧。", "quality": 1, "resolution": "576x1024", "aspectPolicy": "reject_mismatch"}


class Reply:
    def __init__(self, status=202, value=None, raw=None):
        self.status_code = status
        self.body = raw if raw is not None else json.dumps(value or {"id": ID, "status": "queued"}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def iter_content(self, _):
        yield self.body


class Session:
    def __init__(self, reply=None):
        self.reply, self.calls = reply or Reply(), []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def client(tmp_path, reply=None):
    session = Session(reply)
    app = create_dashboard(tmp_path, submission=GatewaySubmission("secret-no-browser", session=session))
    return TestClient(app, base_url="http://localhost:8091"), session


def test_json_forwards_only_to_fixed_api_once_and_returns_no_secrets(tmp_path):
    c, s = client(tmp_path)
    data = {**FIELDS, "sourceUrl": "https://example.org/start.png", "endSourceUrl": "https://example.org/end.png"}
    response = c.post("/dashboard/api/generation", json=data, headers=ORIGIN)
    assert response.status_code == 202 and response.json() == {"id": ID, "status": "accepted"}
    url, sent = s.calls[0]
    assert len(s.calls) == 1 and url == GATEWAY_IMAGE_URL
    assert json.loads(sent["data"]) == data
    assert sent["headers"]["Authorization"] == "Bearer secret-no-browser"
    assert sent["allow_redirects"] is False and s.trust_env is False
    assert "secret" not in response.text and "Authorization" not in response.text
    assert not list(tmp_path.iterdir())  # no database, worker or local job record created


@pytest.mark.parametrize("quality,resolution", list(itertools.product([1, 2, 3, 8], [
    "832x480", "960x544", "1280x704", "576x1024", "608x1088", "704x1280",
])))
def test_supported_choices_with_multipart(tmp_path, quality, resolution):
    c, s = client(tmp_path)
    response = c.post("/dashboard/api/generation", headers=ORIGIN,
        data={**FIELDS, "quality": quality, "resolution": resolution},
        files={"image": ("start.png", b"first-bytes", "image/png"),
               "endImage": ("end.png", b"last-bytes", "image/png")})
    assert response.status_code == 202
    assert len(s.calls) == 1
    assert b"first-bytes" in s.calls[0][1]["data"] and b"last-bytes" in s.calls[0][1]["data"]


@pytest.mark.parametrize("patch", [{"quality": 9}, {"resolution": "1024x1024"}, {"durationSeconds": 16},
    {"durationSeconds": 4}, {"seed": -1}, {"seed": "no"}, {"profileId": "old"},
    {"idempotencyKey": "unused"}, {"image": "mixed"}, {"sourceUrl": "file:///etc/passwd"}])
def test_invalid_json_never_reaches_gateway(tmp_path, patch):
    c, s = client(tmp_path)
    response = c.post("/dashboard/api/generation", json={**FIELDS, "sourceUrl": "https://example.org/start.png", **patch}, headers=ORIGIN)
    assert response.status_code == 422 and not s.calls


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://evil.invalid", "X-Dashboard-Request": "1"},
    {"Origin": "http://localhost:8091"}, {**ORIGIN, "Sec-Fetch-Site": "same-site"},
    {**ORIGIN, "Sec-Fetch-Site": "cross-site"}, {**ORIGIN, "Origin": "https://gx10-1523.tail6040ad.ts.net"}])
def test_origin_checks_precede_submission(tmp_path, headers):
    c, s = client(tmp_path)
    assert c.post("/dashboard/api/generation", json=FIELDS, headers=headers).status_code == 403
    assert not s.calls


def test_missing_key_is_safe_read_only_mode(tmp_path):
    c = TestClient(create_dashboard(tmp_path), base_url="http://localhost:8091")
    assert c.get("/dashboard/api/generation").json() == {"enabled": False}
    assert c.post("/dashboard/api/generation", json=FIELDS, headers=ORIGIN).status_code == 503
    assert GatewaySubmission.from_key_file(None) is None


@pytest.mark.parametrize("files,data", [
    ({"endImage": ("end.png", b"last")}, FIELDS),
    ({"image": ("start.png", b"first")}, {**FIELDS, "sourceUrl": "https://example.org/start.png"}),
    ({"image": ("start.png", b"first"), "endImage": ("end.png", b"")}, FIELDS),
    ({"image": ("start.png", b"first")}, {**FIELDS, "idempotencyKey": "bad"}),
])
def test_invalid_multipart_never_reaches_gateway(tmp_path, files, data):
    c, s = client(tmp_path)
    assert c.post("/dashboard/api/generation", headers=ORIGIN, files=files, data=data).status_code == 422
    assert not s.calls


def test_oversize_request_bounded_before_dispatch(tmp_path):
    c, s = client(tmp_path)
    assert c.post("/dashboard/api/generation", content=b" " * 131073, headers={**ORIGIN, "Content-Type": "application/json"}).status_code == 413
    assert MAX_BODY < 41 * 1024 * 1024 and not s.calls


@pytest.mark.parametrize("reply", [requests.ReadTimeout("secret-no-browser"), requests.ConnectionError("secret-no-browser"),
    Reply(500, {"error": "private-error"}), Reply(302), Reply(200), Reply(raw=b"bad"),
    Reply(value={"id": "not-a-job"}), Reply(raw=b"x" * 65537)])
def test_uncertain_upstream_outcome_is_not_retried(tmp_path, reply):
    c, s = client(tmp_path, reply)
    result = c.post("/dashboard/api/generation", json={**FIELDS, "sourceUrl": "https://example.org/start.png"}, headers=ORIGIN)
    assert result.status_code == 502
    assert result.json() == {"error": "submission_outcome_unknown"}
    assert len(s.calls) == 1 and "secret" not in result.text


@pytest.mark.parametrize("status,code,expected", [(422, "input_aspect_mismatch", "input_aspect_mismatch"),
    (401, "secret-no-browser", "gateway_submission_unauthorized"), (422, "secret-no-browser", "gateway_request_rejected")])
def test_only_safe_rejections_are_exposed(tmp_path, status, code, expected):
    c, _ = client(tmp_path, Reply(status, {"error": code}))
    response = c.post("/dashboard/api/generation", json={**FIELDS, "sourceUrl": "https://example.org/start.png"}, headers=ORIGIN)
    assert response.json() == {"error": expected} and "secret" not in response.text


def test_key_file_is_not_part_of_browser_resources(tmp_path):
    key = tmp_path / "key"
    key.write_text("server-only\n")
    submit = GatewaySubmission.from_key_file(str(key))
    assert submit.key == "server-only"
    key.write_text("")
    with pytest.raises(RuntimeError):
        GatewaySubmission.from_key_file(str(key))
    with pytest.raises(SubmissionError):
        GatewaySubmission("key", session=Session(Reply(400, {"error": "unknown"}))).submit(b"{}", "application/json")


def test_full_unicode_prompt_and_max_seed_are_preserved(tmp_path):
    c, session = client(tmp_path)
    response = c.post("/dashboard/api/generation", headers=ORIGIN,
        data={**FIELDS, "prompt": "中" * 8000, "seed": "9223372036854775807"},
        files={"image": ("start.png", b"first")})
    assert response.status_code == 202
    assert ("中" * 8000).encode() in session.calls[0][1]["data"]
    assert b"9223372036854775807" in session.calls[0][1]["data"]


def test_dashboard_projection_preserves_seed_as_decimal_string(tmp_path):
    import sqlite3

    from plotloom_h3_gateway.dashboard.reader import DashboardReader
    from plotloom_h3_gateway.store import GatewayStore

    GatewayStore(tmp_path / "gateway.sqlite3")
    with sqlite3.connect(tmp_path / "gateway.sqlite3") as db:
        db.execute("""INSERT INTO jobs(id,backend,input_mode,quality,resolution,
            execution_snapshot_json,prompt,seed,requested_duration_seconds,frame_count,fps,status)
            VALUES (?,'h3_video','image',1,'576x1024','{}','test',?,5,124,24,'queued')""",
            (ID, 9223372036854775807))
    assert DashboardReader(tmp_path).detail(ID)["seed"] == "9223372036854775807"


def test_real_admission_with_disposable_db_never_starts_generation(tmp_path, monkeypatch):
    import sqlite3

    from dashboard_browser_fixture import create_fixture

    root = tmp_path / "data"
    video = tmp_path / "retained-fixture.mp4"
    video.write_bytes(b"playback fixture; never a new model result")
    monkeypatch.setenv("DASHBOARD_FIXTURE_ROOT", str(root))
    monkeypatch.setenv("DASHBOARD_FIXTURE_VIDEO", str(video))
    app = create_fixture()
    c = TestClient(app, base_url="http://localhost:8091")
    data = {**FIELDS, "seed": "9223372036854775807"}
    uploaded = c.post("/dashboard/api/generation", headers=ORIGIN, data=data,
        files={"image": ("start.png", (root / "start.png").read_bytes()),
               "endImage": ("end.png", (root / "start.png").read_bytes())})
    assert uploaded.status_code == 202
    linked = c.post("/dashboard/api/generation", headers=ORIGIN,
        json={**data, "sourceUrl": "https://fixture.invalid/start.png"})
    assert linked.status_code == 202
    unknown = c.post("/dashboard/api/generation", headers=ORIGIN,
        json={**data, "prompt": "fixture-unknown", "sourceUrl": "https://fixture.invalid/start.png"})
    assert unknown.json() == {"error": "submission_outcome_unknown"}
    assert app.state.fixture_transport.calls == 3
    with sqlite3.connect(root / "gateway.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 3
        assert db.execute("SELECT count(*) FROM job_frame_bindings").fetchone()[0] == 4
        assert set(db.execute("SELECT seed FROM jobs").fetchall()) == {(9223372036854775807,)}
