#!/usr/bin/env python3
"""Deterministic source-ordered coverage with hash-bound evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bound(base, item):
    try:
        p = Path(item['file'])
        p = p if p.is_absolute() else base / p
        return p.is_file() and sha(p) == item['sha256']
    except (KeyError, TypeError, OSError):
        return False


def report(manifest, base):
    source = manifest['source']
    if not bound(base, source):
        raise ValueError('current source missing or changed')
    episodes = source['episodes']
    ids = [s for ep in episodes for s in ep['segments']]
    eps = [e['id'] for e in episodes]
    if len(set(ids)) != len(ids) or len(set(eps)) != len(eps):
        raise ValueError('duplicate source segment or episode')
    index = {sid: i for i, sid in enumerate(ids)}
    tech = {sid: [] for sid in ids}
    for t in manifest.get('technical', []):
        sid = t['segmentId']
        if sid not in index:
            raise ValueError('unknown technical segment')
        if t['status'] == 'PASS' and bound(base, t['receipt']) and bound(base, t['media']):
            tech[sid].append(t['receipt']['file'])
    selections = manifest.get('selections', [])
    selected_ids = [r['segmentId'] for r in selections]
    if len(set(selected_ids)) != len(selected_ids) or any(s not in index for s in selected_ids):
        raise ValueError('duplicate or unknown selection')
    if selected_ids != sorted(selected_ids, key=index.get):
        raise ValueError('selections out of source order')
    selected = {r['segmentId']: bound(base, r['media']) and bound(base, r['evidence'])
                for r in selections}
    results = []
    for ep in episodes:
        segments = ep['segments']
        rows = [{'segmentId': s, 'technicalAttemptCount': len(tech[s]),
                 'explicitSelectionCurrent': selected.get(s, False)} for s in segments]
        results.append({'episodeId': ep['id'], 'segments': rows,
                        'technicalCovered': sum(bool(tech[s]) for s in segments),
                        'technicalGaps': [s for s in segments if not tech[s]],
                        'selectedCovered': sum(selected.get(s, False) for s in segments),
                        'selectionGaps': [s for s in segments if not selected.get(s, False)]})
    exports = []
    for e in manifest.get('exports', []):
        matches = [ep for ep in episodes if ep['id'] == e['episodeId']]
        if len(matches) != 1:
            raise ValueError('unknown export episode')
        selection_path = Path(e['selection']['file'])
        selection_path = selection_path if selection_path.is_absolute() else base / selection_path
        try:
            frozen_rows = json.loads(selection_path.read_text())['selections']
        except (OSError, ValueError, KeyError, TypeError):
            frozen_rows = None
        current_rows = [r for r in selections if r['segmentId'] in e['segments']]
        valid = (frozen_rows == current_rows and
                 e['sourceSha256'] == source['sha256'] and
                 e['selectionSha256'] == e['selection']['sha256'] and
                 e['segments'] == matches[0]['segments'] and
                 all(selected.get(s, False) for s in e['segments']) and
                 all(bound(base, b) for b in [e['selection'], e['receipt'], e['media'], *e['proofs']]))
        exports.append({'episodeId': e['episodeId'], 'bindingsCurrent': valid,
                        'qualification': 'bindings only; receipt semantics require adapter verification'})
    return {'sourceSha256': source['sha256'], 'episodes': results, 'exports': exports,
            'limits': 'Technical evidence is not review or creative acceptance; exports require proof semantics.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    args = p.parse_args()
    data = json.loads(args.manifest.read_text())
    print(json.dumps(report(data, args.manifest.resolve().parent), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
