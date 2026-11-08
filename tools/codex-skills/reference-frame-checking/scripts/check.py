#!/usr/bin/env python3
"""Prepare and validate source-bound still-image review cases without image extraction."""
import argparse
import hashlib
import json
from pathlib import Path

VERSION = '0.1.0'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_record(path, expected=None):
    path = Path(path).resolve(strict=True)
    value = digest(path)
    require(expected is None or value == expected, f'hash mismatch: {path}')
    return {'path': str(path), 'sha256': value}


def adapt(manifest_path, references):
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest = read(manifest_path)
    source_path = Path(manifest['sourceFile'])
    if not source_path.is_absolute():
        source_path = manifest_path.parent / source_path
    source = file_record(source_path, manifest['sourceSha256'])
    story = read(source['path'])
    segments = [s for e in story['episodes'] for s in e['segments']]
    segment_id = manifest.get('segmentId')
    matches = [s for s in segments if s['id'] == segment_id] if segment_id else segments
    require(len(matches) == 1, 'source segment missing or ambiguous')
    segment = matches[0]
    segment_id = segment['id']
    originals = [file_record(manifest_path), source]
    if 'promptFile' in manifest or 'promptSha256' in manifest:
        prompt = file_record(manifest_path.parent / manifest['promptFile'], manifest['promptSha256'])
        require(Path(prompt['path']).read_text(encoding='utf-8').strip() == segment['h3Prompt'].strip(), 'prompt differs from source')
        originals.append(prompt)
    images = manifest['orderedImages']
    cuts = segment['cuts']
    require(len(images) == len(cuts) and len(cuts) > 0, 'image/cut count mismatch')
    frames = []
    elapsed = 0.0
    for index, (image, cut) in enumerate(zip(images, cuts), 1):
        require(image['index'] == index, 'noncontiguous image indices')
        require(abs(image['atMs'] - round(elapsed * 1000)) <= 2, f'cut timing mismatch: {index}')
        require(isinstance(cut.get('frame'), str) and cut['frame'].strip(), f'missing frame expectation: {index}')
        frames.append({'id': f'frame:{index}', 'image': file_record(manifest_path.parent / image['file'], image['sha256']),
                       'atMs': image['atMs'], 'expected': cut['frame'],
                       'sourceCut': {k: cut[k] for k in ('shot', 'size', 'camera', 'cameraPosition', 'composition', 'focus', 'characters', 'props') if k in cut}})
        elapsed += cut['seconds']
    return {'schemaVersion': 1, 'caseId': segment_id,
            'sourceContext': {'blocking': segment.get('blocking', ''), 'note': segment.get('note', '')},
            'originals': originals, 'frames': frames,
            'references': [{'id': f'reference:{i}', 'image': file_record(p)} for i, p in enumerate(references, 1)]}


def prepare(case_path):
    case_path = Path(case_path).resolve(strict=True)
    case = read(case_path)
    require(case.get('schemaVersion') == 1 and isinstance(case.get('caseId'), str) and case['caseId'], 'invalid case identity')
    require(isinstance(case.get('sourceContext'), dict), 'missing source context')
    require(isinstance(case.get('originals'), list) and case['originals'], 'missing source originals')
    frames, refs = case.get('frames'), case.get('references')
    require(isinstance(frames, list) and frames and isinstance(refs, list), 'missing frames/references')
    ids = []
    for entry in frames + refs:
        require(isinstance(entry.get('id'), str) and entry['id'], 'missing evidence ID')
        ids.append(entry['id'])
        image = entry['image']
        file_record(image['path'], image['sha256'])
    require(len(set(ids)) == len(ids), 'duplicate evidence IDs')
    for frame in frames:
        require(isinstance(frame.get('expected'), str) and frame['expected'].strip(), 'missing expectation')
    for original in case['originals']:
        file_record(original['path'], original['sha256'])
    # No derivative extraction: bind structured case and actual bytes to tool and review rules.
    skill_dir = Path(__file__).resolve().parent.parent
    tool_files = [Path(__file__), skill_dir / 'SKILL.md', skill_dir / 'references/contracts.md', skill_dir / 'references/review-rules.md']
    binding = {'case': file_record(case_path), 'caseId': case['caseId'], 'skillVersion': VERSION,
               'toolHashes': {p.name: digest(p) for p in tool_files}, 'evidenceIds': ids}
    return {**binding, 'fingerprint': canonical(binding)}


def validate(report, bundle):
    require(bundle == prepare(bundle['case']['path']), 'stale bundle')
    case = read(bundle['case']['path'])
    require(report.get('schemaVersion') == 1 and report.get('caseId') == bundle['caseId'], 'report case mismatch')
    require(report.get('bundleFingerprint') == bundle['fingerprint'] and report.get('skillVersion') == VERSION, 'report binding mismatch')
    require(report.get('decision') in ('pass', 'fail', 'needs_review'), 'unsupported decision')
    require(isinstance(report.get('summary'), str) and report['summary'].strip(), 'missing summary')
    require(isinstance(report.get('reviewer'), dict) and report['reviewer'].get('model') and report['reviewer'].get('reasoning'), 'missing reviewer')
    viewed = report.get('evidenceViewed')
    require(isinstance(viewed, list) and len(viewed) == len(set(viewed)) and set(viewed) <= set(bundle['evidenceIds']), 'foreign or duplicate viewed evidence')
    findings = report.get('findings')
    require(isinstance(findings, list) and isinstance(report.get('limitations'), list), 'missing findings or limitations')
    for finding in findings:
        require(finding.get('severity') in ('material', 'minor', 'uncertain'), 'invalid severity')
        require(all(isinstance(finding.get(k), str) and finding[k].strip() for k in ('category', 'claim')), 'invalid finding')
        evidence = finding.get('evidenceIds')
        require(isinstance(evidence, list) and evidence and set(evidence) <= set(viewed), 'finding evidence not viewed')
    severities = {f['severity'] for f in findings}
    if report['decision'] == 'pass':
        require(not severities.intersection({'material', 'uncertain'}), 'pass with material or uncertain finding')
        require(set(viewed) == set(bundle['evidenceIds']), 'pass requires all supplied frames and references')
    if report['decision'] == 'fail':
        require('material' in severities, 'fail requires material finding')
    if report['decision'] == 'needs_review':
        require('material' not in severities, 'observed material failure requires fail')
    return {'valid': True, 'caseId': case['caseId'], 'decision': report['decision']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    a = sub.add_parser('adapt'); a.add_argument('manifest'); a.add_argument('--reference', action='append', default=[]); a.add_argument('--output', required=True)
    p = sub.add_parser('prepare'); p.add_argument('case'); p.add_argument('--output', required=True)
    v = sub.add_parser('validate'); v.add_argument('report'); v.add_argument('--bundle', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'adapt': write(args.output, adapt(args.manifest, args.reference))
        elif args.command == 'prepare': write(args.output, prepare(args.case))
        else: print(json.dumps(validate(read(args.report), read(args.bundle))))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f'error: {exc}\n')


if __name__ == '__main__': main()
