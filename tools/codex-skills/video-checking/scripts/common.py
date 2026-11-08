"""Small, local-only primitives shared by video review commands."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f)


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        raise ValueError(f'{args[0]} failed ({p.returncode}): {p.stderr.decode(errors="replace")[-1500:]}')
    return p.stdout


def source(base, value):
    if not isinstance(value, str) or not value:
        raise ValueError('expected a nonempty path')
    p = Path(os.path.abspath(base / value))
    if not p.is_file():
        raise ValueError(f'input file missing: {p}')
    return p


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def pinned(base, item):
    if not isinstance(item, dict):
        raise ValueError('pin must be an object')
    p = source(base, item.get('file'))
    if item.get('sha256') != sha(p):
        raise ValueError(f'input hash mismatch: {p}')
    return p


def probe(video):
    raw = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams',
               '-show_format', '-show_frames', '-show_entries',
               'stream=width,height,avg_frame_rate:format=duration:frame=best_effort_timestamp_time',
               '-of', 'json', str(video)])
    data = json.loads(raw)
    streams = data.get('streams', [])
    if len(streams) != 1:
        raise ValueError('video must have a video stream')
    frames = [number(float(f['best_effort_timestamp_time']), 'frame timestamp')
              for f in data.get('frames', []) if 'best_effort_timestamp_time' in f]
    duration = number(float(data['format']['duration']), 'duration')
    if not frames or duration <= 0 or any(b < a for a, b in zip(frames, frames[1:])):
        raise ValueError('video has no ordered timestamped frames or duration')
    return {'durationSeconds': duration, 'width': streams[0]['width'],
            'height': streams[0]['height'], 'frameTimes': frames,
            'frameRate': streams[0].get('avg_frame_rate')}


def extract(video, index, output):
    run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf', f'select=eq(n\\,{index})',
         '-fps_mode', 'passthrough', '-frames:v', '1', '-y', str(output)])
    if not Path(output).is_file() or not Path(output).stat().st_size:
        raise ValueError('frame extraction produced no image')


def contained(root, relative):
    if not isinstance(relative, str):
        raise ValueError('evidence file must be a path')
    p = (root / relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError(f'unsafe or missing evidence file: {relative}')
    return p


def verify_bundle(root):
    root = Path(root).resolve()
    b = read(root / 'bundle.json')
    if b.get('schemaVersion') != 1 or not isinstance(b.get('evidence'), list):
        raise ValueError('invalid bundle')
    manifest = b.get('inputManifest')
    if not isinstance(manifest, dict) or digest(manifest) != b.get('cacheKey'):
        raise ValueError('invalid cache key')
    if digest({k: v for k, v in b.items() if k != 'fingerprint'}) != b.get('fingerprint'):
        raise ValueError('invalid bundle fingerprint')
    sources = manifest.get('sources')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('missing original source pins')
    for name, entry in sources.items():
        if not isinstance(entry, dict) or not Path(entry.get('path', '')).is_absolute():
            raise ValueError(f'invalid source pin: {name}')
        if sha(Path(entry['path'])) != entry.get('sha256'):
            raise ValueError(f'original source changed: {name}')
    ids = set()
    for e in b['evidence']:
        if e.get('id') in ids or not e.get('id'):
            raise ValueError('duplicate or missing evidence ID')
        ids.add(e['id'])
        if sha(contained(root, e.get('file'))) != e.get('sha256'):
            raise ValueError(f'corrupt bundle evidence: {e.get("id")}')
    if (b.get('caseSnapshotSha256') != manifest.get('case') or
            b.get('videoSha256') != manifest.get('video') or
            sources.get('case', {}).get('sha256') != manifest.get('case') or
            sources.get('video', {}).get('sha256') != manifest.get('video')):
        raise ValueError('bundle sources disagree with manifest')
    if sha(contained(root, 'case.json')) != b.get('caseSnapshotSha256'):
        raise ValueError('corrupt case snapshot')
    case = read(root / 'case.json')
    if case.get('caseId') != b.get('caseId') or case.get('requirements') != b.get('requirements'):
        raise ValueError('bundle metadata disagrees with case')
    return b
