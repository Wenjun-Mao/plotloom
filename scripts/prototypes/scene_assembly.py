"""Immutable prototype assembly over explicit, hash-bound full source takes."""
from __future__ import annotations

import copy
import hashlib
import json
from html import escape
from io import BytesIO
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def probe(path: Path) -> dict:
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, check=True)
    data = json.loads(result.stdout)
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    if not any(s['codec_type'] == 'audio' for s in data['streams']):
        raise ValueError('source take must retain native audio')
    fps = video['avg_frame_rate']
    if fps != '24/1' or video.get('nb_frames') is None:
        raise ValueError('prototype requires exact 24 fps source frame counts')
    return {'frames': int(video['nb_frames']), 'durationUnits': round(int(video['nb_frames']) * 1000 / 24),
            'width': video['width'], 'height': video['height'], 'fps': fps}


ASSEMBLY_RECIPE = {'version': 1, 'fps': 24, 'canvas': '832x480 contain-pad',
                   'video': 'libx264 veryfast crf18', 'audio': 'aac 160k 48000Hz',
                   'timeline': 'all source frames; audio pad/trim to exact video frame clock; concat A/V'}


def assemble(source: dict, bindings: dict, cache: Path, static: Path) -> tuple[bytes, dict]:
    """Build before publication. No project selections or publication pointer change."""
    cache.mkdir(parents=True, exist_ok=True)
    story = copy.deepcopy(source)
    story['storyRevision'] = digest(encoded(source))
    files, media, scenes = {}, {}, {}
    slots = {c['slot'] for n in source['nodes'] for c in n['clips']}
    if slots != set(bindings):
        raise ValueError('bindings must cover exactly the authored logical slots')
    for slot in sorted(slots):
        binding = bindings[slot]
        path = Path(binding['path'])
        content = path.read_bytes()
        if digest(content) != binding['sha256']:
            raise ValueError('source bytes changed: ' + slot)
        facts = probe(path)
        if facts != binding['probe']:
            raise ValueError('source probe changed: ' + slot)
        media[slot] = binding | {'fullTake': True}
        files[f"takes/{binding['sha256']}.mp4"] = content
    for node in story['nodes']:
        if not node['clips']:
            continue
        components = node['clips']
        identity = digest(encoded({'recipe': ASSEMBLY_RECIPE, 'inputs': [media[c['slot']]['sha256'] for c in components]}))
        output = cache / (identity + '.mp4')
        if not output.exists():
            args, filters, joins = ['ffmpeg', '-nostdin', '-v', 'error', '-y'], [], []
            for i, c in enumerate(components):
                item = media[c['slot']]
                args += ['-i', item['path']]
                duration = item['probe']['frames'] / 24
                filters += [f'[{i}:v]fps=24,scale=832:480:force_original_aspect_ratio=decrease,pad=832:480:(ow-iw)/2:(oh-ih)/2,setsar=1,setpts=PTS-STARTPTS[v{i}]',
                            f'[{i}:a]aresample=48000,apad,atrim=duration={duration:.9f},asetpts=PTS-STARTPTS[a{i}]']
                joins += [f'[v{i}][a{i}]']
            filters += [''.join(joins) + f'concat=n={len(components)}:v=1:a=1[v][a]']
            with TemporaryDirectory(dir=cache) as temp:
                staged = Path(temp) / 'scene.mp4'
                subprocess.run(args + ['-filter_complex', ';'.join(filters), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(staged)], check=True, capture_output=True)
                if probe(staged)['frames'] != sum(media[c['slot']]['probe']['frames'] for c in components):
                    raise ValueError('assembled scene lost source video frames')
                staged.replace(output)
        content = output.read_bytes()
        filename = f'media/{digest(content)}.mp4'
        files[filename] = content
        segments, frame = [], 0
        for c in components:
            frames = media[c['slot']]['probe']['frames']
            segments.append(c | {'start': frame / 24, 'durationUnits': round(frames * 1000 / 24)})
            frame += frames
        node['clips'] = [{'slot': components[0]['slot'], 'src': filename, 'durationUnits': round(frame * 1000 / 24),
                          'dialogue': [], 'visibleText': [], 'segments': segments}]
        scenes[node['id']] = {'path': filename, 'sha256': digest(content), 'frames': frame, 'segments': segments}
    story['assetVersion'] = digest(encoded({slot: media[slot]['sha256'] for slot in sorted(media)}))
    for name in ('player.js', 'player.css'):
        files[name] = (static / name).read_bytes()
    files['favicon.svg'] = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="5" fill="#17201c"/><path d="M12 8l13 8-13 8z" fill="#d8b77f"/></svg>'
    embedded = encoded(story).decode().replace('<', '\\u003c').replace('&', '\\u0026')
    files['index.html'] = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'self\'; media-src \'self\'; img-src \'self\'; connect-src \'none\'; base-uri \'none\'">'
        f'<title>{escape(story["title"])}</title><link rel="icon" href="favicon.svg"><link rel="stylesheet" href="player.css"><main id="game"></main>'
        f'<script id="story" type="application/json">{embedded}</script><script src="player.js" defer></script></html>').encode()
    files['README.txt'] = '完整解压后打开 index.html。继续与声音设置保存在当前浏览器/地址；在同一地址打开更新版可保留进度。无需 Plotloom 或互联网。\n'.encode()
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    archive = output.getvalue()
    return archive, {'deliveryPath': 'immutable-export-prototype-assembly', 'story': story, 'source': source,
                     'assemblyRecipe': ASSEMBLY_RECIPE, 'ffmpegVersion': subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True).stdout.decode().splitlines()[0],
                     'bindings': media, 'scenes': scenes, 'files': {n: digest(c) for n, c in sorted(files.items())}, 'archiveHash': digest(archive)}
