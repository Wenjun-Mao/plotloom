import json
import zipfile
from pathlib import Path

import pytest

from scripts.prototypes.last_projection_v3 import build as build_module


def _story_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_dir = tmp_path / "v2-source"
    source_dir.mkdir()
    source = source_dir / "source.zip"
    story = {
        "format": 1,
        "gameId": "the-last-projection-v2",
        "storyRevision": "test-revision",
        "assetVersion": "test-assets",
        "title": "V2 title",
        "intro": "V2 intro",
        "start": "opening",
        "nodes": [{"id": "opening", "title": "Opening", "clips": [{"src": "media/clip.mp4"}], "edges": []}],
    }
    html = ('<!doctype html><title>放映室最后一夜 · V2</title>'
            '<script id="story" type="application/json">' + json.dumps(story) + '</script>').encode()
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("index.html", html)
        archive.writestr("favicon.svg", b"<svg></svg>")
        archive.writestr("media/clip.mp4", b"retained clip bytes")
    monkeypatch.setattr(build_module, "V2_SHA256", build_module.digest(source.read_bytes()))
    return source


def _prior_manifest() -> dict:
    return {"format": 1, "gameId": "the-last-projection-v3", "storyRevision": "old-revision",
            "v2GameId": "the-last-projection-v2", "v2ZipSha256": build_module.V2_SHA256,
            "media": {"media/clip.mp4": "old-hash"}}


def _existing_v3_zip(path: Path, output_name: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{output_name}/build-manifest.json", json.dumps(_prior_manifest()))


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_missing_static_assets_leave_prior_folder_zip_and_unknown_files_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _story_archive(tmp_path, monkeypatch)
    output = tmp_path / "v3"
    output.mkdir()
    (output / "build-manifest.json").write_text(json.dumps(_prior_manifest()), encoding="utf-8")
    (output / "director-sentinel.txt").write_text("keep this unrelated file", encoding="utf-8")
    (output / "game").mkdir()
    (output / "game" / "previous-player.js").write_bytes(b"previous usable player")
    zip_path = tmp_path / "v3.zip"
    _existing_v3_zip(zip_path, output.name)
    before_folder, before_zip = _snapshot_tree(output), zip_path.read_bytes()

    with pytest.raises(FileNotFoundError, match="deterministic player asset is missing"):
        build_module.build(source, output, tmp_path / "missing-static", zip_path)

    assert _snapshot_tree(output) == before_folder
    assert zip_path.read_bytes() == before_zip


def test_unrecognized_nonempty_folder_is_refused_without_deleting_its_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _story_archive(tmp_path, monkeypatch)
    output = tmp_path / "v3"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("unrelated user data", encoding="utf-8")
    with pytest.raises(ValueError, match="unrecognized nonempty output folder"):
        build_module.build(source, output, tmp_path / "missing-static", tmp_path / "v3.zip")
    assert sentinel.read_text(encoding="utf-8") == "unrelated user data"


def test_arbitrary_existing_zip_is_refused_and_left_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _story_archive(tmp_path, monkeypatch)
    output = tmp_path / "v3"
    output.mkdir()
    (output / "build-manifest.json").write_text(json.dumps(_prior_manifest()), encoding="utf-8")
    sentinel = output / "director-sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    zip_path = tmp_path / "v3.zip"
    zip_path.write_bytes(b"an unrelated ZIP destination")

    with pytest.raises(ValueError, match="unrecognized ZIP destination"):
        build_module.build(source, output, tmp_path / "missing-static", zip_path)

    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert zip_path.read_bytes() == b"an unrelated ZIP destination"


def test_normal_rebuild_updates_v3_artifacts_and_preserves_unknown_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _story_archive(tmp_path, monkeypatch)
    static = tmp_path / "static"
    static.mkdir()
    (static / "player.js").write_bytes(b"current player js")
    (static / "player.css").write_bytes(b"current player css")
    output = tmp_path / "v3"
    output.mkdir()
    (output / "build-manifest.json").write_text(json.dumps(_prior_manifest()), encoding="utf-8")
    (output / "game").mkdir()
    (output / "game" / "player.js").write_bytes(b"old player js")
    sentinel = output / "director-sentinel.txt"
    sentinel.write_text("keep across rebuild", encoding="utf-8")
    zip_path = tmp_path / "v3.zip"
    _existing_v3_zip(zip_path, output.name)

    result = build_module.build(source, output, static, zip_path)

    assert sentinel.read_text(encoding="utf-8") == "keep across rebuild"
    assert (output / "game" / "player.js").read_bytes() == b"current player js"
    assert json.loads((output / "build-manifest.json").read_text(encoding="utf-8"))["format"] == 1
    assert result["gameId"] == "the-last-projection-v3"
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.read("v3/game/player.js") == b"current player js"
        assert archive.read("v3/game/media/clip.mp4") == b"retained clip bytes"
        assert json.loads(archive.read("v3/build-manifest.json"))["format"] == 1
        assert "v3/director-sentinel.txt" not in archive.namelist()


def test_failed_zip_promotion_rolls_back_the_folder_and_preserves_old_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _story_archive(tmp_path, monkeypatch)
    static = tmp_path / "static"
    static.mkdir()
    (static / "player.js").write_bytes(b"current player js")
    (static / "player.css").write_bytes(b"current player css")
    output = tmp_path / "v3"
    output.mkdir()
    (output / "build-manifest.json").write_text(json.dumps(_prior_manifest()), encoding="utf-8")
    (output / "director-sentinel.txt").write_bytes(b"keep exactly")
    (output / "game").mkdir()
    (output / "game" / "player.js").write_bytes(b"old player js")
    zip_path = tmp_path / "v3.zip"
    _existing_v3_zip(zip_path, output.name)
    before_folder, before_zip = _snapshot_tree(output), zip_path.read_bytes()

    original_replace = build_module.os.replace
    failed = False

    def fail_zip_promotion_once(source_path, destination_path):
        nonlocal failed
        if Path(destination_path) == zip_path and not failed:
            failed = True
            raise OSError("simulated atomic ZIP promotion refusal")
        return original_replace(source_path, destination_path)

    monkeypatch.setattr(build_module.os, "replace", fail_zip_promotion_once)
    with pytest.raises(OSError, match="simulated atomic ZIP promotion refusal"):
        build_module.build(source, output, static, zip_path)

    assert failed
    assert _snapshot_tree(output) == before_folder
    assert zip_path.read_bytes() == before_zip
