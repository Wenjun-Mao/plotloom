#!/usr/bin/env python3
"""Select reproducible pass/fail audit candidates, not audit results."""
import argparse
import json
import random
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('batch', help='JSON array of {report, bundle} paths')
p.add_argument('--seed', required=True, type=int)
p.add_argument('--per-decision', type=int, default=1)
a = p.parse_args()
if a.per_decision < 0:
    p.error('--per-decision must be nonnegative')
from check import read, validate
base = Path(a.batch).resolve().parent
batch = read(a.batch)
groups = {'pass': [], 'fail': [], 'needs_review': []}
seen = set()
for entry in batch:
    report_path = (base / entry['report']).resolve()
    result = validate(read(report_path), read((base / entry['bundle']).resolve()))
    if result['caseId'] in seen:
        raise ValueError('duplicate case ID')
    seen.add(result['caseId'])
    groups[result['decision']].append({'caseId': result['caseId'], 'report': str(report_path)})
rng = random.Random(a.seed)
selected = {}
for decision in ('pass', 'fail'):
    group = sorted(groups[decision], key=lambda x: x['caseId'])
    selected[decision] = rng.sample(group, min(a.per_decision, len(group)))
print(json.dumps({'seed': a.seed, 'selected': selected, 'needsReview': groups['needs_review'], 'auditPerformed': False}, indent=2))
