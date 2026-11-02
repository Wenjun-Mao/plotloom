"""Rebuild the V3 standalone game from the immutable delivered V2 package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

V2_SHA256 = "ac4744740e1b8d6fc329d622267c8bad19bf7efc047e889460c05f2b757b3bda"
DEFAULT_SOURCE = Path.home() / "Downloads/plotloom-the-last-projection-v2/the-last-projection-v2.zip"
DEFAULT_OUTPUT = Path.home() / "Downloads/plotloom-the-last-projection-v3"
DEFAULT_ZIP = Path.home() / "Downloads/plotloom-the-last-projection-v3.zip"
STORY_RE = re.compile(rb'(<script id="story" type="application/json">)(.*?)(</script>)', re.S)
OWNED_ROOT_FILES = {"build-manifest.json", "游玩说明.txt", "开始游玩.html", "启动本地版.command"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_v3_manifest(value: object) -> bool:
    return isinstance(value, dict) and value.get("format") == 1 \
        and value.get("gameId") == "the-last-projection-v3" \
        and value.get("v2ZipSha256") == V2_SHA256 \
        and isinstance(value.get("media"), dict)


def _read_output_manifest(output: Path) -> dict | None:
    if not output.exists():
        return None
    if output.is_symlink() or not output.is_dir():
        raise ValueError(f"refusing to replace a non-directory V3 output: {output}")
    marker = output / "build-manifest.json"
    if marker.is_symlink():
        raise ValueError(f"refusing a symlinked V3 ownership marker: {marker}")
    if not marker.is_file():
        if any(output.iterdir()):
            raise ValueError(f"refusing to overwrite an unrecognized nonempty output folder: {output}")
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"refusing to overwrite an unreadable V3 ownership marker: {marker}") from error
    if not _is_v3_manifest(value):
        raise ValueError(f"refusing to overwrite a folder not owned by this V3 builder: {output}")
    return value


def _validate_existing_zip(zip_path: Path, output_name: str) -> None:
    if not zip_path.exists():
        return
    if zip_path.is_symlink() or not zip_path.is_file():
        raise ValueError(f"refusing to overwrite a non-file V3 ZIP destination: {zip_path}")
    marker_name = f"{output_name}/build-manifest.json"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            marker = json.loads(archive.read(marker_name))
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"refusing to overwrite an unrecognized ZIP destination: {zip_path}") from error
    if not _is_v3_manifest(marker):
        raise ValueError(f"refusing to overwrite a ZIP not owned by this V3 builder: {zip_path}")


def _safe_media_paths(story: dict) -> list[str]:
    names = sorted({clip["src"] for node in story["nodes"] for clip in node["clips"]})
    for name in names:
        path = Path(name)
        if not name.startswith("media/") or path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unexpected media path in V2 story: {name}")
    return names


def _stage_game(source: Path, static: Path, game: Path) -> dict:
    static_assets = {}
    for asset in ("player.js", "player.css"):
        candidate = static / asset
        if not candidate.is_file():
            raise FileNotFoundError(f"deterministic player asset is missing: {candidate}")
        static_assets[asset] = candidate.read_bytes()

    archive_bytes = source.read_bytes()
    if digest(archive_bytes) != V2_SHA256:
        raise ValueError("V2 source package hash does not match the approved immutable input")
    with zipfile.ZipFile(source) as v2_archive:
        raw_html = v2_archive.read("index.html")
        match = STORY_RE.search(raw_html)
        if not match:
            raise ValueError("V2 package does not contain its expected public story payload")
        story = json.loads(match.group(2))
        v2_story_id = story["gameId"]
        story["gameId"] = "the-last-projection-v3"
        story["title"] = "放映室最后一夜"
        story["intro"] = "明早八点，旧影院就要交接。看完这一夜留下的画面，记下你亲眼看见、亲耳听到的事。"
        story_json = json.dumps(story, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        html = raw_html[:match.start(2)] + story_json + raw_html[match.end(2):]
        html = html.replace("放映室最后一夜 · V2".encode(), "放映室最后一夜 · V3".encode())
        names = _safe_media_paths(story)
        media_manifest = {}
        media_bytes = {}
        for name in names:
            data = v2_archive.read(name)
            media_manifest[name] = digest(data)
            media_bytes[name] = data
        favicon = v2_archive.read("favicon.svg")
        original_story = json.loads(match.group(2))
        if v2_story_id != original_story["gameId"]:
            raise ValueError("V2 game identity changed while building V3")

    game.mkdir(parents=True)
    (game / "index.html").write_bytes(html)
    (game / "favicon.svg").write_bytes(favicon)
    for asset, data in static_assets.items():
        (game / asset).write_bytes(data)
    for name, data in media_bytes.items():
        destination = game / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return {"format": 1, "gameId": story["gameId"], "storyRevision": story["storyRevision"],
            "v2GameId": v2_story_id, "v2ZipSha256": V2_SHA256, "media": media_manifest}


def _stage_delivery(root: Path, manifest: dict) -> None:
    readme = """放映室最后一夜 · V3

开始
- 双击「开始游玩.html」可从本地文件打开。
- 推荐双击「启动本地版.command」，在浏览器打开 http://127.0.0.1:18765/。保持打开的 Terminal 窗口运行服务；结束游玩时按 Control-C。
- 选择「继续」可恢复进度；物证册只显示已遇见的线索，交接簿可回到已归档路线的选择。
- 右上角「声音」控制影片原有的混合声音。字幕和浏览器原生播放控件可用。

游戏文件夹里的媒体须与 index.html 放在一起。V3 使用独立存档，不会改动 V2 的游玩记录。
"""
    (root / "游玩说明.txt").write_text(readme, encoding="utf-8")
    (root / "开始游玩.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=game/index.html"><title>放映室最后一夜 · V3</title>正在打开游戏…',
        encoding="utf-8")
    launcher = '''#!/bin/zsh
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/game"
PORT=18765
cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    trap - INT TERM HUP EXIT
    /bin/kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    /bin/rm -f "$ROOT/server.pid"
  fi
}
trap cleanup INT TERM HUP EXIT
if ! /usr/bin/curl -fsS "http://127.0.0.1:${PORT}/index.html" 2>/dev/null | /usr/bin/grep -q 'the-last-projection-v3'; then
  /usr/bin/python3 -m http.server "$PORT" --bind 127.0.0.1 > "$ROOT/server.log" 2>&1 < /dev/null &
  SERVER_PID=$!
  echo "$SERVER_PID" > "$ROOT/server.pid"
  for _ in {1..40}; do
    if /usr/bin/curl -fsS "http://127.0.0.1:${PORT}/index.html" 2>/dev/null | /usr/bin/grep -q 'the-last-projection-v3'; then break; fi
    sleep 0.25
  done
fi
/usr/bin/curl -fsS "http://127.0.0.1:${PORT}/index.html" 2>/dev/null | /usr/bin/grep -q 'the-last-projection-v3' || { print -u2 "V3 server did not start on 127.0.0.1:${PORT}; see $ROOT/server.log"; exit 1; }
/usr/bin/open "http://127.0.0.1:${PORT}/"
if [[ -n "${SERVER_PID:-}" ]]; then wait "$SERVER_PID"; fi
'''
    launcher_path = root / "启动本地版.command"
    launcher_path.write_text(launcher, encoding="utf-8")
    launcher_path.chmod(0o755)
    manifest_path = root / "build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_zip(zip_path: Path, root: Path, output_name: str) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for file in sorted(root.rglob("*")):
            if not file.is_file() or file.name in {"server.log", "server.pid"}:
                continue
            relative = Path(output_name) / file.relative_to(root)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 11, 2, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            mode = 0o100755 if file.name == "启动本地版.command" else 0o100644
            info.external_attr = mode << 16
            archive.writestr(info, file.read_bytes())


def _owned_target_paths(candidate_root: Path, candidate_files: list[Path]) -> list[Path]:
    return [path.relative_to(candidate_root) for path in candidate_files]


def _ensure_existing_owned_paths_safe(output: Path, paths: list[Path]) -> None:
    if not output.exists():
        return
    for relative in paths:
        cursor = output
        for part in relative.parts[:-1]:
            cursor = cursor / part
            if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
                raise ValueError(f"refusing to write through a non-directory V3 path: {cursor}")
        target = output / relative
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"refusing to replace an unexpected V3 artifact path: {target}")


def _prepare_merged_output(output: Path, candidate: Path, merged: Path) -> list[Path]:
    if output.exists():
        shutil.copytree(output, merged, symlinks=True, copy_function=shutil.copy2)
    else:
        merged.mkdir()
    candidate_files = sorted(path for path in candidate.rglob("*") if path.is_file())
    relative_paths = _owned_target_paths(candidate, candidate_files)
    _ensure_existing_owned_paths_safe(output, relative_paths)
    for source in candidate_files:
        relative = source.relative_to(candidate)
        destination = merged / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return relative_paths


def _promote(output: Path, merged: Path, zip_path: Path, staged_zip: Path,
             output_backup: Path, failed_output: Path) -> None:
    had_output = output.exists()
    if had_output:
        os.replace(output, output_backup)
    try:
        os.replace(merged, output)
        os.replace(staged_zip, zip_path)
    except BaseException:
        if output.exists():
            os.replace(output, failed_output)
            shutil.rmtree(failed_output, ignore_errors=True)
        if had_output and output_backup.exists():
            os.replace(output_backup, output)
        raise


def build(source: Path, output: Path, static: Path, zip_path: Path) -> dict:
    source = source.expanduser().resolve()
    requested_output = output.expanduser()
    requested_zip = zip_path.expanduser()
    if requested_output.is_symlink() or requested_zip.is_symlink():
        raise ValueError("V3 output folder and ZIP cannot be symlinks")
    output = requested_output.resolve()
    zip_path = requested_zip.resolve()
    if source.is_relative_to(output) or output == source.parent or output.is_relative_to(source.parent):
        raise ValueError("V3 output must be separate from the retained V2 delivery")
    if zip_path == source or zip_path.is_relative_to(source.parent) or zip_path.is_relative_to(output) or zip_path == output:
        raise ValueError("V3 ZIP must be separate from both the retained V2 source and output folder")

    _read_output_manifest(output)
    _validate_existing_zip(zip_path, output.name)
    # Input/dependency errors are resolved before staging or changing either target.
    for asset in ("player.js", "player.css"):
        if not (static / asset).is_file():
            raise FileNotFoundError(f"deterministic player asset is missing: {static / asset}")

    output.parent.mkdir(parents=True, exist_ok=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="last-projection-v3-stage-", dir=output.parent, ignore_cleanup_errors=True) as output_tmp, \
            tempfile.TemporaryDirectory(prefix="last-projection-v3-zip-", dir=zip_path.parent, ignore_cleanup_errors=True) as zip_tmp:
        output_tmp = Path(output_tmp)
        zip_tmp = Path(zip_tmp)
        candidate = output_tmp / "candidate"
        candidate.mkdir()
        manifest = _stage_game(source, static, candidate / "game")
        _stage_delivery(candidate, manifest)
        staged_zip = zip_tmp / "candidate.zip"
        _write_zip(staged_zip, candidate, output.name)
        zip_sha256 = digest(staged_zip.read_bytes())

        merged = output_tmp / "merged"
        _prepare_merged_output(output, candidate, merged)
        backup = output_tmp / "prior-output"
        failed = output_tmp / "failed-output"
        _promote(output, merged, zip_path, staged_zip, backup, failed)
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)

    return {**manifest, "packageZipSha256": zip_sha256}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--static", type=Path, default=Path(__file__).resolve().parents[3] / "src/plotloom/player_static")
    args = parser.parse_args()
    manifest = build(args.source, args.output, args.static, args.zip)
    print(json.dumps({"output": str(args.output.resolve()), "gameId": manifest["gameId"],
                      "package": str(args.zip.resolve()), "packageZipSha256": manifest["packageZipSha256"],
                      "mediaFiles": len(manifest["media"]), "v2ZipSha256": manifest["v2ZipSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
