#!/usr/bin/env python3
"""Read-only adapter for the retained Shuohao production and manager helpers."""
import argparse
import json
from pathlib import Path
import sys

from progress import report, sha

PROJECT = Path(__file__).resolve().parents[4]
MANAGER = PROJECT / '.local/ref2va/manager'
sys.path.insert(0, str(MANAGER))
from assembly_preflight import current_authority, selected_clip  # noqa: E402


def binding(path):
    return {'file': str(path), 'sha256': sha(path)}


def choose_selections(ordered_ids, candidates, chosen, source):
    """Choose only explicit rows, or uniquely valid decisions without a snapshot."""
    errors, result = [], []
    position = {sid: i for i, sid in enumerate(ordered_ids)}
    if chosen is not None:
        rows = chosen['clips']
        ids = [row['segmentId'] for row in rows]
        if len(set(ids)) != len(ids) or any(s not in position for s in ids):
            raise ValueError('duplicate or unknown selection')
        if ids != sorted(ids, key=position.get):
            raise ValueError('selections out of source order')
        if (Path(chosen['storyboardFile']).resolve() != source.resolve() or
                chosen['storyboardSha256'] != sha(source)):
            return [], ['Selection snapshot references a different current source; historical only']
        for row in rows:
            sid = row['segmentId']
            matches = [(clip, review) for clip, review in candidates.get(sid, [])
                       if review.parent.resolve() == Path(row['packet']).resolve()
                       and sha(review) == row['reviewSha256']
                       and ('nativeSha256' not in row or clip['nativeSha256'] == row['nativeSha256'])]
            if len(matches) != 1:
                errors.append(f'{sid}: supplied selection failed current preflight or bindings')
                continue
            clip, review = matches[0]
            result.append({'segmentId': sid, 'media': binding(clip['file']), 'evidence': binding(review)})
    else:
        for sid in ordered_ids:
            valid = candidates.get(sid, [])
            if len(valid) == 1:
                clip, review = valid[0]
                result.append({'segmentId': sid, 'media': binding(clip['file']), 'evidence': binding(review)})
            elif len(valid) > 1:
                errors.append(f'{sid}: conflicting current selected reviews; no take chosen')
    return result, errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection', type=Path, help='explicit partial or full selection JSON')
    args = p.parse_args()
    source, story, authority = current_authority()
    production = source.parent
    ordered = [(e['ep'], s) for e in story['episodes'] for s in e['segments']]
    manifest = {'source': {**binding(source), 'episodes': [
        {'id': f"E{e['ep']:02}", 'segments': [s['id'] for s in e['segments']]}
        for e in story['episodes']]}, 'technical': [], 'selections': []}
    # Report all independently bound technical receipts; no take is chosen.
    for _, seg in ordered:
        sid = seg['id']
        for packet in sorted((production / 'attempts' / sid).glob('attempt-*')):
            try:
                receipt = packet / ('evidence/terminal-technical-receipt.json' if sid == 'E01-01' else 'evidence/technical-receipt.json')
                media = packet / 'output/original-native-av.mp4'
                data = json.loads(receipt.read_text())
                comparison = json.loads((packet / 'evidence/actual-request-comparison.json').read_text())
                packet_manifest = packet / 'manifest.json'
                if not (data['status'] == 'PASS' and data['postCount'] == 1 and
                        data['ffmpegDecodeExitCode'] == 0 and data['outputSha256'] == sha(media) and
                        data['outputBytes'] == media.stat().st_size and comparison['status'] == 'PASS' and
                        comparison['completeGraphEqual'] is True and
                        comparison['jobId'] == data['jobId'] and
                        comparison['comfyPromptId'] == data['comfyPromptId'] and
                        (sid == 'E01-01' or data['manifestSha256'] == sha(packet_manifest))):
                    continue
                manifest['technical'].append({'segmentId': sid, 'receipt': binding(receipt),
                                              'media': binding(media), 'status': 'PASS'})
            except (OSError, KeyError, ValueError, TypeError):
                continue
    selection_errors = []
    decisions = []
    candidates = {}
    # Each clip-review is an explicit decision; validate all candidates, never pick
    # an attempt by name or recency. Conflicting valid selections remain gaps.
    for ep, seg in ordered:
        sid = seg['id']
        valid = []
        for review in sorted((production / 'attempts' / sid).glob('attempt-*/clip-review.json')):
            try:
                value = json.loads(review.read_text())
                decision = value['decision']
                entry = {'segmentId': sid, 'review': str(review), 'decision': decision,
                         'currentSelectionPreflight': False}
                if decision == 'selected':
                    row = {'segmentId': sid, 'packet': str(review.parent), 'reviewSha256': sha(review)}
                    try:
                        clip = selected_clip(ep, seg, row, authority[sid])
                        entry['currentSelectionPreflight'] = True
                        valid.append((clip, review))
                    except (AssertionError, OSError, KeyError, ValueError, StopIteration) as exc:
                        entry['preflightError'] = str(exc)
                decisions.append(entry)
            except (OSError, KeyError, ValueError, TypeError) as exc:
                selection_errors.append(f'{review}: unreadable review: {exc}')
        candidates[sid] = valid
    chosen = json.loads(args.selection.read_text()) if args.selection else None
    manifest['selections'], errors = choose_selections(
        [s['id'] for _, s in ordered], candidates, chosen, source)
    selection_errors.extend(errors)
    result = report(manifest, PROJECT)
    result['selectionErrors'] = selection_errors
    result['decisions'] = decisions
    result['technicalScope'] = ('Retained receipt PASS, decoded output hash/size, and complete graph comparison; '
                                'not full current-source fidelity, review, or selection.')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
