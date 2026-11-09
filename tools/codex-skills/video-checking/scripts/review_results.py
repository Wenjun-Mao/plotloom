#!/usr/bin/env python3
"""Validate source-bound reviews and select a reproducible audit sample."""
import argparse
import json
from pathlib import Path
import random

from common import contained, number, probe, read, sha, verify_bundle

SKILL_VERSION = '0.1.3'


def validate(review_path, bundle_path, detail_dirs=()):
    review_path = Path(review_path).resolve(); root = Path(bundle_path).resolve()
    b = verify_bundle(root); r = read(review_path)
    if r.get('schemaVersion') != 1 or r.get('caseId') != b['caseId'] or r.get('bundleFingerprint') != b['fingerprint'] or r.get('skillVersion') != SKILL_VERSION:
        raise ValueError('review identity or skill version mismatch')
    reviewer = r.get('reviewer')
    if not isinstance(reviewer, dict) or any(not isinstance(reviewer.get(k), str) or not reviewer[k].strip() for k in ('model', 'reasoning')):
        raise ValueError('reviewer model and reasoning required')
    if r.get('decision') not in ('pass', 'fail', 'needs_review') or not isinstance(r.get('summary'), str) or not r['summary'].strip():
        raise ValueError('decision and summary required')
    if not isinstance(r.get('limitations'), list) or any(not isinstance(x, str) for x in r['limitations']):
        raise ValueError('limitations must be a list of strings')
    evidence = {e['id']: e for e in b['evidence']}
    frame_times = None
    if detail_dirs or r['decision'] == 'pass':
        frame_times = probe(b['inputManifest']['sources']['video']['path'])['frameTimes']
        if len(frame_times) != b['video']['frameCount']:
            raise ValueError('source frame count changed')
    for path in detail_dirs:
        path = Path(path).resolve(); d = read(path/'detail.json')
        if d.get('schemaVersion') != 1 or d.get('bundleFingerprint') != b['fingerprint'] or d.get('sourceSha256') != b['videoSha256']:
            raise ValueError('foreign detail evidence')
        if type(d.get('frameIndex')) is not int or not 0 <= d['frameIndex'] < b['video']['frameCount'] or d.get('id') != f'detail:{d["frameIndex"]}':
            raise ValueError('invalid detail identity')
        if sha(contained(path, d.get('file'))) != d.get('sha256'):
            raise ValueError('corrupt detail evidence')
        if d['id'] in evidence:
            raise ValueError('duplicate evidence ID')
        t = number(d.get('timeSeconds'), 'detail time')
        if abs(t - frame_times[d['frameIndex']]) > 0.000001:
            raise ValueError('detail time does not match native frame timestamp')
        evidence[d['id']] = d
    viewed = r.get('evidenceViewed')
    if not isinstance(viewed, list) or not viewed or any(not isinstance(x, str) or x not in evidence for x in viewed):
        raise ValueError('missing or foreign viewed evidence')
    findings = r.get('findings')
    if not isinstance(findings, list): raise ValueError('findings must be a list')
    for f in findings:
        if not isinstance(f, dict) or f.get('severity') not in ('material', 'minor', 'uncertain') or any(not isinstance(f.get(k), str) or not f[k].strip() for k in ('category', 'claim')):
            raise ValueError('invalid finding')
        start, end = number(f.get('startSeconds'), 'finding start'), number(f.get('endSeconds'), 'finding end')
        ids = f.get('evidenceIds')
        if start < 0 or end < start or end > b['video']['durationSeconds'] + 0.001:
            raise ValueError('finding time out of bounds')
        if not isinstance(ids, list) or not ids or any(x not in viewed for x in ids):
            raise ValueError('finding evidence must be present and viewed')
    if r['decision'] == 'pass' and any(f['severity'] in ('material', 'uncertain') for f in findings):
        raise ValueError('pass cannot contain material or uncertain findings')
    if r['decision'] == 'fail' and not any(f['severity'] == 'material' for f in findings):
        raise ValueError('fail requires a supported material finding')
    if r['decision'] == 'pass':
        case = read(root/'case.json')
        references = {e['id'] for e in b['evidence'] if e['kind'] == 'reference'}
        if not references.issubset(viewed):
            raise ValueError('pass requires all supplied references viewed')
        covered = set()
        for eid in viewed:
            e = evidence[eid]
            if e.get('kind') not in ('native_anchor', 'contact_sheet', 'uniform_inspection', 'detail'):
                continue
            indices = e.get('frameIndices', [])
            if 'frameIndex' in e: indices = [e['frameIndex']]
            for index in indices:
                if type(index) is not int or not 0 <= index < len(frame_times):
                    raise ValueError('visual evidence frame out of bounds')
                t = frame_times[index]
                covered.update(s['id'] for s in case['shots'] if s['startSeconds'] <= t < s['endSeconds'])
        if covered != {s['id'] for s in case['shots']}:
            raise ValueError('pass requires viewed visual evidence covering every shot')
    speech = r.get('speech')
    if not isinstance(speech, dict) or speech.get('status') not in ('represented', 'uncertain', 'not_assessed', 'not_required') or not isinstance(speech.get('notes'), str):
        raise ValueError('invalid speech assessment')
    if b['requirements']['speech']:
        if speech['status'] == 'represented' and ('asr' not in viewed or b['asrStatus'] != 'provided'):
            raise ValueError('represented speech requires viewed source-bound ASR')
        if speech['status'] != 'represented' and r['decision'] == 'pass':
            raise ValueError('unconfirmed required speech requires needs_review')
    elif speech['status'] == 'not_required':
        pass
    # Perceptual audio needs explicit evidence. v1 has no listening-evidence record type.
    if b['requirements']['perceptualAudio'] and r['decision'] == 'pass':
        raise ValueError('required perceptual audio is unconfirmed in v1; needs_review')
    return {'caseId': b['caseId'], 'bundleFingerprint': b['fingerprint'], 'skillVersion': r['skillVersion'],
            'reviewSha256': sha(review_path), 'decision': r['decision'], 'review': str(review_path), 'bundle': str(root)}


def batch(manifest_path, seed, per_decision):
    path = Path(manifest_path).resolve(); manifest = read(path)
    if not isinstance(manifest, list) or not manifest:
        raise ValueError('batch manifest must be a nonempty array')
    results = []
    for item in manifest:
        if not isinstance(item, dict) or not isinstance(item.get('review'), str) or not isinstance(item.get('bundle'), str) or not isinstance(item.get('details', []), list):
            raise ValueError('invalid batch entry')
        if type(item.get('highRisk', False)) is not bool:
            raise ValueError('highRisk must be boolean')
        result = validate(path.parent/item['review'], path.parent/item['bundle'], [path.parent/p for p in item.get('details', [])])
        result['highRisk'] = item.get('highRisk', False)
        results.append(result)
    if len({(x['caseId'], x['bundleFingerprint'], x['reviewSha256']) for x in results}) != len(results):
        raise ValueError('duplicate batch review')
    rng = random.Random(seed)
    selected = []
    for decision in ('pass', 'fail'):
        pool = sorted((x for x in results if x['decision'] == decision), key=lambda x: (x['caseId'], x['reviewSha256']))
        selected.extend(rng.sample(pool, min(per_decision, len(pool))))
    selected.extend(sorted((x for x in results if x['decision'] == 'needs_review'), key=lambda x: (x['caseId'], x['reviewSha256'])))
    chosen = {x['reviewSha256'] for x in selected}
    selected.extend(sorted((x for x in results if x['highRisk'] and x['reviewSha256'] not in chosen), key=lambda x: (x['caseId'], x['reviewSha256'])))
    return {'schemaVersion': 1, 'seed': seed, 'perDecision': per_decision,
            'counts': {d: sum(r['decision'] == d for r in results) for d in ('pass', 'fail', 'needs_review')},
            'reviews': results, 'selectedForAudit': selected, 'auditStatus': 'selection_only'}


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='command', required=True)
    v = sub.add_parser('validate'); v.add_argument('review'); v.add_argument('--bundle', required=True); v.add_argument('--detail', action='append', default=[])
    b = sub.add_parser('batch'); b.add_argument('manifest'); b.add_argument('--seed', required=True); b.add_argument('--per-decision', type=int, default=1)
    a = p.parse_args()
    try:
        if a.command == 'validate': result = validate(a.review, a.bundle, a.detail)
        else:
            if a.per_decision < 1: raise ValueError('per-decision must be at least 1')
            result = batch(a.manifest, a.seed, a.per_decision)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as e:
        p.exit(2, f'error: {e}\n')

if __name__ == '__main__': main()
