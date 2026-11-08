#!/usr/bin/env python3
"""Prepare immutable, content-addressed review evidence or extract audit detail."""
import argparse
import bisect
import json
import os
from pathlib import Path
import shutil
import tempfile

from common import digest, extract, number, pinned, probe, read, run, sha, source, verify_bundle, write


def validate(case_path):
    case_path = case_path.resolve()
    c = read(case_path)
    base = case_path.parent
    if c.get('schemaVersion') != 1 or not isinstance(c.get('caseId'), str) or not c['caseId']:
        raise ValueError('invalid case schema or ID')
    if not isinstance(c.get('worldState'), str) or not c['worldState'].strip():
        raise ValueError('worldState required')
    req = c.get('requirements')
    if not isinstance(req, dict) or any(type(req.get(k)) is not bool for k in ('speech', 'perceptualAudio')):
        raise ValueError('requirements must have boolean speech and perceptualAudio')
    video = source(base, c.get('video'))
    video_sha = sha(video)
    meta = probe(video)
    shots = c.get('shots')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots required')
    refs, seen, end = [], set(), 0.0
    for s in shots:
        sid = s.get('id')
        if not isinstance(sid, str) or not sid or sid in seen or ':' in sid:
            raise ValueError('shot IDs must be nonempty, unique, and exclude colon')
        seen.add(sid)
        start, stop = number(s.get('startSeconds'), 'shot start'), number(s.get('endSeconds'), 'shot end')
        if abs(start-end) > 0.001 or stop <= start or stop > meta['durationSeconds'] + 0.001:
            raise ValueError('shots must be contiguous, ordered and in bounds')
        end = stop
        if not isinstance(s.get('expected'), str) or not s['expected'].strip():
            raise ValueError('shot expected text required')
        if not isinstance(s.get('references'), list) or not isinstance(s.get('dialogue'), list):
            raise ValueError('references and dialogue must be arrays')
        for i, name in enumerate(s['references'], 1):
            p = source(base, name)
            refs.append((f'reference:{sid}:{i}', p, sha(p), sid))
        for d in s['dialogue']:
            if not isinstance(d, dict) or d.get('mode') not in ('public', 'private') or any(not isinstance(d.get(k), str) or not d[k].strip() for k in ('speaker', 'text')):
                raise ValueError('invalid dialogue')
    if abs(end-meta['durationSeconds']) > 0.05:
        raise ValueError('shots must cover full clip including final hold')
    optional = {}
    for name in ('technicalReceipt', 'asr', 'inspection'):
        if name in c:
            p = pinned(base, c[name]); data = read(p)
            optional[name] = (p, data)
            if name == 'technicalReceipt' and (data.get('outputSha256') != video_sha or data.get('status') != 'PASS' or data.get('ffmpegDecodeExitCode') != 0):
                raise ValueError('technical receipt does not prove full decode for source')
            if name in ('asr', 'inspection') and data.get('sourceSha256') != video_sha:
                raise ValueError(f'{name} source mismatch')
    if 'asr' in optional:
        segments = optional['asr'][1].get('segments')
        if not isinstance(segments, list):
            raise ValueError('ASR segments required')
        for seg in segments:
            a, b = number(seg.get('startSeconds', seg.get('start')), 'ASR start'), number(seg.get('endSeconds', seg.get('end')), 'ASR end')
            if a < 0 or b < a or b > meta['durationSeconds'] + 0.001 or not isinstance(seg.get('text'), str):
                raise ValueError('invalid ASR segment')
    inspection = []
    if 'inspection' in optional:
        ip, desc = optional['inspection']
        pages = desc.get('pages')
        if not isinstance(desc.get('overview'), (dict, str)) or not isinstance(pages, list) or not pages:
            raise ValueError('inspection requires overview and pages')
        for eid, entry in [('overview', desc['overview'])] + [(f'page:{i}', p) for i, p in enumerate(pages)]:
            if eid == 'overview' and isinstance(entry, str):
                p = source(ip.parent, entry)
                inspection.append((eid, p, sha(p), []))
                continue
            if not isinstance(entry, dict) or not isinstance(entry.get('frameIndices'), list) or not entry['frameIndices']:
                raise ValueError('inspection image requires frame indices')
            indices = entry['frameIndices']
            if any(type(x) is not int or x < 0 or x >= len(meta['frameTimes']) for x in indices):
                raise ValueError('inspection frame out of bounds')
            p = source(ip.parent, entry.get('file'))
            inspection.append((eid, p, sha(p), indices))
        covered = set(x for _, _, _, indices in inspection for x in indices)
        for s in shots:
            if not any(s['startSeconds'] <= meta['frameTimes'][x] < s['endSeconds'] for x in covered):
                raise ValueError('inspection does not cover every shot')
    script_dir = Path(__file__).resolve().parent
    code = {name: sha(script_dir/name) for name in ('prepare_review.py', 'common.py')}
    versions = {name: run([name, '-version']).decode(errors='replace').splitlines()[0] for name in ('ffmpeg', 'ffprobe')}
    inputs = {'case': (case_path, sha(case_path)), 'video': (video, video_sha)}
    inputs.update({eid: (p, h) for eid, p, h, _ in refs})
    inputs.update({name: (p, sha(p)) for name, (p, _) in optional.items()})
    inputs.update({f'inspection:{eid}': (p, h) for eid, p, h, _ in inspection})
    sources = {name: {'path': str(p), 'sha256': h} for name, (p, h) in inputs.items()}
    manifest = {'case': sha(case_path), 'video': video_sha, 'sources': sources,
                'references': [(a, h) for a, _, h, _ in refs],
                'optional': {k: sha(v[0]) for k, v in optional.items()},
                'inspectionImages': [(a, h) for a, _, h, _ in inspection], 'code': code, 'toolVersions': versions}
    return c, video, meta, refs, optional, inspection, manifest


def nearest(times, target, lo, hi):
    candidates = [i for i, t in enumerate(times) if lo <= t < hi]
    if not candidates:
        raise ValueError('shot contains no native frames')
    return min(candidates, key=lambda i: abs(times[i]-target))


def sheet(images, out):
    args = ['ffmpeg', '-v', 'error']
    for image in images:
        args += ['-i', str(image)]
    filters = ''.join(f'[{i}:v]scale=320:200:force_original_aspect_ratio=decrease,pad=320:200:(ow-iw)/2:(oh-ih)/2[v{i}];' for i in range(len(images)))
    filters += ''.join(f'[v{i}]' for i in range(len(images))) + f'xstack=inputs={len(images)}:layout=' + '|'.join(f'{i%4}*320_{i//4}*200' for i in range(len(images))) + '[out]'
    if len(images) == 1:
        filters = '[0:v]scale=320:200:force_original_aspect_ratio=decrease,pad=320:200:(ow-iw)/2:(oh-ih)/2[out]'
    run(args + ['-filter_complex', filters, '-map', '[out]', '-frames:v', '1', '-y', str(out)])


def prepare(case_path, out):
    c, video, meta, refs, optional, inspection, manifest = validate(case_path)
    # Validate all frame selections before creating any output.
    anchors = []
    for shot in c['shots']:
        a, b = shot['startSeconds'], shot['endSeconds']
        candidates = [i for i, t in enumerate(meta['frameTimes']) if a <= t < b]
        if not candidates:
            raise ValueError('shot contains no native frames')
        for target in (a, (a+b)/2, b):
            anchors.append((shot['id'], nearest(meta['frameTimes'], target, a, b)))
    dense_indices = []
    for shot in c['shots']:
        a, b = shot['startSeconds'], shot['endSeconds']
        count = max(1, int((b - a) / 0.5) + 1)
        dense_indices.extend(nearest(meta['frameTimes'], min(a + n * 0.5, b), a, b) for n in range(count))
    dense_indices = list(dict.fromkeys(dense_indices))
    cache_key = digest(manifest)
    out = Path(out).resolve()
    all_inputs = [video, Path(case_path).resolve()] + [x[1] for x in refs] + [x[0] for x in optional.values()] + [x[1] for x in inspection]
    if any(p.resolve().is_relative_to(out) for p in all_inputs):
        raise ValueError('output/cache directory must be separate from inputs')
    final = out / cache_key
    if final.exists():
        bundle = verify_bundle(final)
        if bundle.get('cacheKey') != cache_key or digest(bundle.get('inputManifest')) != digest(manifest):
            raise ValueError('cache manifest mismatch')
        return final, True
    out.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.prepare-', dir=out))
    try:
        shutil.copyfile(case_path, stage/'case.json')
        evidence = []
        def copy_evidence(eid, p, kind, expected_hash, **fields):
            name = f'e{len(evidence):04d}{p.suffix.lower()}'
            shutil.copyfile(p, stage/name)
            actual = sha(stage/name)
            if actual != expected_hash: raise ValueError('input changed during preparation')
            evidence.append(dict(id=eid, file=name, sha256=actual, kind=kind, **fields))
        for eid, p, expected, sid in refs:
            copy_evidence(eid, p, 'reference', expected, shotId=sid)
        if 'asr' in optional:
            copy_evidence('asr', optional['asr'][0], 'blind_asr', manifest['optional']['asr'])
        if 'technicalReceipt' in optional:
            copy_evidence('technical-receipt', optional['technicalReceipt'][0], 'technical_receipt', manifest['optional']['technicalReceipt'])
            technical = {'status': 'PASS', 'decode': 'reused_pinned_receipt'}
        else:
            run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video), '-map', '0', '-f', 'null', '-'])
            technical = {'status': 'PASS', 'decode': 'fresh_full_decode'}
        frame_files = []
        for i, (sid, idx) in enumerate(anchors):
            p = stage / f'anchor-{i}.png'; extract(video, idx, p); frame_files.append(p)
            evidence.append(dict(id=f'anchor:{i}', file=p.name, sha256=sha(p), kind='native_anchor', shotId=sid, frameIndex=idx, timeSeconds=meta['frameTimes'][idx]))
        if inspection:
            for eid, p, expected, indices in inspection:
                copy_evidence(eid, p, 'uniform_inspection', expected, frameIndices=indices)
        else:
            # A half-second grid yields denser motion coverage than shot anchors.
            dense_files = []
            for i, index in enumerate(dense_indices):
                p = stage/f'.dense-{i}.png'; extract(video, index, p); dense_files.append(p)
            for j in range(0, len(dense_files), 12):
                p = stage/f'page-{j//12}.png'; sheet(dense_files[j:j+12], p)
                evidence.append(dict(id=f'page:{j//12}', file=p.name, sha256=sha(p), kind='contact_sheet', frameIndices=dense_indices[j:j+12]))
            overview_indices = list(range(1, len(frame_files), 3))[:12]
            p = stage/'overview.png'; sheet([frame_files[i] for i in overview_indices], p)
            evidence.append(dict(id='overview', file=p.name, sha256=sha(p), kind='contact_sheet', frameIndices=[anchors[i][1] for i in overview_indices]))
            for p in dense_files: p.unlink()
        b = {'schemaVersion': 1, 'cacheKey': cache_key, 'inputManifest': manifest,
             'caseId': c['caseId'], 'caseSnapshotSha256': sha(stage/'case.json'), 'videoSha256': manifest['video'],
             'video': {**{k:v for k,v in meta.items() if k != 'frameTimes'}, 'frameCount': len(meta['frameTimes'])}, 'technical': technical,
             'asrStatus': 'provided' if 'asr' in optional else 'missing', 'requirements': c['requirements'], 'evidence': evidence}
        if sha(video) != manifest['video'] or sha(stage/'case.json') != manifest['case'] or any(sha(item[0]) != manifest['optional'][name] for name, item in optional.items()):
            raise ValueError('input changed during preparation')
        if any(sha(Path(item['path'])) != item['sha256'] for item in manifest['sources'].values()):
            raise ValueError('input changed during preparation')
        b['fingerprint'] = digest(b)
        write(stage/'bundle.json', b)
        os.rename(stage, final)
        return final, False
    finally:
        if stage.exists(): shutil.rmtree(stage)


def detail(bundle_dir, video_path, frame, out):
    b = verify_bundle(bundle_dir); video = Path(video_path).resolve()
    if not video.is_file() or sha(video) != b['videoSha256']:
        raise ValueError('detail source hash mismatch')
    meta = probe(video)
    if frame < 0 or frame >= len(meta['frameTimes']):
        raise ValueError('detail frame out of bounds')
    out = Path(out).resolve()
    if video.is_relative_to(out) or Path(bundle_dir).resolve().is_relative_to(out) or out.is_relative_to(Path(bundle_dir).resolve()):
        raise ValueError('detail output must be separate from source and bundle')
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f'{b["fingerprint"]}-frame-{frame}'
    if dest.exists():
        raise ValueError('detail already exists; use a fresh output namespace')
    stage = Path(tempfile.mkdtemp(prefix='.detail-', dir=out))
    try:
        p = stage/'frame.png'; extract(video, frame, p)
        record = {'schemaVersion': 1, 'bundleFingerprint': b['fingerprint'], 'sourceSha256': b['videoSha256'],
                  'id': f'detail:{frame}', 'file': 'frame.png', 'sha256': sha(p), 'kind': 'detail',
                  'frameIndex': frame, 'timeSeconds': meta['frameTimes'][frame]}
        write(stage/'detail.json', record); os.rename(stage, dest)
        return dest
    finally:
        if stage.exists(): shutil.rmtree(stage)


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('case'); prep.add_argument('--output', required=True)
    det = sub.add_parser('detail'); det.add_argument('bundle'); det.add_argument('--video', required=True); det.add_argument('--frame', type=int, required=True); det.add_argument('--output', required=True)
    a = p.parse_args()
    try:
        if a.command == 'prepare':
            path, hit = prepare(Path(a.case), a.output); print(json.dumps({'bundle': str(path), 'cacheHit': hit}))
        else: print(json.dumps({'detail': str(detail(a.bundle, a.video, a.frame, a.output))}))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as e:
        p.exit(2, f'error: {e}\n')

if __name__ == '__main__': main()
