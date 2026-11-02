"""Rebuild the V3 standalone game from the immutable delivered V2 package."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

V2_SHA256 = "ac4744740e1b8d6fc329d622267c8bad19bf7efc047e889460c05f2b757b3bda"
DEFAULT_SOURCE = Path.home() / "Downloads/plotloom-the-last-projection-v2/the-last-projection-v2.zip"
DEFAULT_OUTPUT = Path.home() / "Downloads/plotloom-the-last-projection-v3"
DEFAULT_ZIP = Path.home() / "Downloads/plotloom-the-last-projection-v3.zip"
STORY_RE = re.compile(rb'(<script id="story" type="application/json">)(.*?)(</script>)', re.S)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(source: Path, output: Path, static: Path, zip_path: Path) -> dict:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    zip_path = zip_path.expanduser().resolve()
    if source.is_relative_to(output) or output == source.parent or output.is_relative_to(source.parent):
        raise ValueError("V3 output must be separate from the retained V2 delivery")
    if zip_path == source or zip_path.is_relative_to(source.parent) or zip_path.is_relative_to(output) or zip_path == output:
        raise ValueError("V3 ZIP must be separate from both the retained V2 source and output folder")
    archive_bytes = source.read_bytes()
    if digest(archive_bytes) != V2_SHA256:
        raise ValueError("V2 source package hash does not match the approved immutable input")
    if output.exists():
        shutil.rmtree(output)
    game = output / "game"
    game.mkdir(parents=True)
    for asset in ("player.js", "player.css"):
        candidate = static / asset
        if not candidate.is_file():
            raise FileNotFoundError(f"deterministic player asset is missing: {candidate}")
        shutil.copyfile(candidate, game / asset)

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
        (game / "index.html").write_bytes(html)
        (game / "favicon.svg").write_bytes(v2_archive.read("favicon.svg"))
        media_names = sorted({clip["src"] for node in story["nodes"] for clip in node["clips"]})
        media_manifest = {}
        for name in media_names:
            if not name.startswith("media/") or ".." in Path(name).parts:
                raise ValueError(f"unexpected media path in V2 story: {name}")
            data = v2_archive.read(name)
            media_manifest[name] = digest(data)
            dest = game / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        original_story = json.loads(match.group(2))
        if v2_story_id != original_story["gameId"]:
            raise ValueError("V2 game identity changed while building V3")

    readme = """放映室最后一夜 · V3\n\n开始\n- 双击「开始游玩.html」可从本地文件打开。\n- 推荐双击「启动本地版.command」，在浏览器打开 http://127.0.0.1:18765/。保持打开的 Terminal 窗口运行服务；结束游玩时按 Control-C。\n- 选择「继续」可恢复进度；物证册只显示已遇见的线索，交接簿可回到已归档路线的选择。\n- 右上角「声音」控制影片原有的混合声音。字幕和浏览器原生播放控件可用。\n\n游戏文件夹里的媒体须与 index.html 放在一起。V3 使用独立存档，不会改动 V2 的游玩记录。\n"""
    (output / "游玩说明.txt").write_text(readme, encoding="utf-8")
    (output / "开始游玩.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=game/index.html"><title>放映室最后一夜 · V3</title>正在打开游戏…', encoding="utf-8")
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
    launcher_path = output / "启动本地版.command"
    launcher_path.write_text(launcher, encoding="utf-8")
    launcher_path.chmod(0o755)
    manifest = {"format": 1, "gameId": story["gameId"], "storyRevision": story["storyRevision"],
                "v2GameId": v2_story_id, "v2ZipSha256": V2_SHA256, "media": media_manifest}
    (output / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for file in sorted(output.rglob("*")):
            if not file.is_file() or file.name in {"server.log", "server.pid"}:
                continue
            relative = Path(output.name) / file.relative_to(output)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 11, 2, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            mode = 0o100755 if file.name == "启动本地版.command" else 0o100644
            info.external_attr = mode << 16
            archive.writestr(info, file.read_bytes())
    manifest["packageZipSha256"] = digest(zip_path.read_bytes())
    return manifest


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
