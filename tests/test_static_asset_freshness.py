from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.runtime import build_runtime_app


@pytest.mark.parametrize(
    ("filename", "url"),
    [("index.html", "/v2/"), ("workbench.js", "/v2/workbench.js"), ("workbench.css", "/v2/workbench.css")],
)
def test_stable_static_urls_require_revalidation_on_success_and_not_modified(
    tmp_path: Path, filename: str, url: str,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    asset = static / filename
    asset.write_text("build-1", encoding="utf-8")
    # Control validator timestamps; the contract cannot depend on test speed
    # or the filesystem's timestamp precision.
    os.utime(asset, (1_700_000_000, 1_700_000_000))
    settings = PlotloomSettings(
        repo_root=tmp_path, outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application", static_dir=static,
        text_auth_mode="none",
    )

    with TestClient(build_runtime_app(settings)) as client:
        initial = client.get(url)
        assert initial.status_code == 200
        assert initial.text == "build-1"
        assert initial.headers["cache-control"] == "no-cache"
        etag = initial.headers["etag"]
        modified = initial.headers["last-modified"]

        unchanged = client.get(url, headers={"If-None-Match": etag})
        assert unchanged.status_code == 304
        assert unchanged.content == b""
        assert unchanged.headers["etag"] == etag
        assert unchanged.headers["cache-control"] == "no-cache"
        unchanged_by_date = client.get(url, headers={"If-Modified-Since": modified})
        assert unchanged_by_date.status_code == 304
        assert unchanged_by_date.headers["cache-control"] == "no-cache"

        asset.write_text("build-2", encoding="utf-8")
        os.utime(asset, (1_700_000_002, 1_700_000_002))
        updated = client.get(url, headers={"If-None-Match": etag, "If-Modified-Since": modified})
        assert updated.status_code == 200
        assert updated.text == "build-2"
        assert updated.headers["etag"] != etag
        assert updated.headers["last-modified"] != modified
        assert updated.headers["cache-control"] == "no-cache"
        head = client.head(url)
        assert head.status_code == 200
        assert head.content == b""
        assert head.headers["cache-control"] == "no-cache"
