"""Build an offline review from retained clips; never submit generation work."""
from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path

from contract import ARMS, CASE_IDS, digest, fingerprint, graph_for, save

LABELS = {
    'A': 'Current BF16',
    'B': 'FP16 control',
    'C': 'FP16 + fast accumulation',
    'D': 'INT8 + fast accumulation',
}


def summarize(item: dict) -> dict:
    """Keep timing scopes explicit; UMA memory views are never added together."""
    observations = item['observations']
    timing = {}
    for kind in ('video', 'audio'):
        for operation in ('encode', 'decode'):
            stages = [row for row in observations if row.get('kind') == 'stage'
                      and row['vaeKind'] == kind and row['operation'] == operation]
            outer = [row for row in observations if row.get('kind') == 'outer_stage'
                     and row['vaeKind'] == kind and row['operation'] == operation]
            timing[f'{kind}_{operation}'] = {
                'calls': len(stages),
                'innerCudaMs': sum(row['cudaElapsedMs'] for row in stages),
                'outerWallMs': sum(row['synchronizedWallMs'] for row in outer),
            }
        timing[f'{kind}_modelManagementMs'] = sum(
            row['wallMs'] for row in observations if row.get('kind') == 'model_management'
            and row['vaeKind'] == kind)
    kernels = {}
    for row in observations:
        if row.get('kind') == 'kernel':
            key = f"{row['vaeKind']}:{row['kernel']}"
            kernels[key] = kernels.get(key, 0) + row['count']
    return {'arm': item['arm'], 'caseId': item['caseId'], 'state': item['state'],
            'submitToObservedCompletionMs': item['elapsedMs'],
            'timing': timing, 'kernels': kernels,
            'hostMemory': item['hostMemory'], 'outputSha256': item['outputSha256'],
            'graphSha256': item['graphSha256'], 'fullDecode': item['fullDecode'],
            'media': item['media']}


def build(root: Path) -> dict:
    receipt = json.loads((root / 'receipt.json').read_text())
    frozen = json.loads((root / 'cases.json').read_text())
    if fingerprint(frozen) != receipt['casesSha256']:
        raise ValueError('Frozen cases changed')
    expected = [(arm, name) for arm in ARMS for name in CASE_IDS]
    if [(row['arm'], row['caseId']) for row in receipt['calls']] != expected:
        raise ValueError('Expected exactly twelve ordered cells')
    if set(receipt['smokes']) != set(ARMS) or any(
            value['state'] != 'passed' for value in receipt['smokes'].values()):
        raise ValueError('Component proofs incomplete')
    cases = {case['id']: case for case in frozen['cases']}
    for asset in frozen['assets']:
        original = Path(asset['path'])
        if original.parent.name == 'input' and digest(root / 'input' / original.name) != asset['sha256']:
            raise ValueError('Copied frozen input changed')
    summary = []
    for item in receipt['calls']:
        if item['state'] != 'passed' or item['fullDecode'] != 'passed':
            raise ValueError('Full generation or decode incomplete')
        if item['graphSha256'] != fingerprint(graph_for(cases[item['caseId']], item['arm'])):
            raise ValueError('Executed graph differs from frozen arm')
        clip = root / f"{item['arm']}_{item['caseId']}.mp4"
        if digest(clip) != item['outputSha256']:
            raise ValueError('Copied clip changed')
        prefix = root / f"{item['arm']}_{item['caseId']}_%02d.jpg"
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(clip), '-vf',
            'select=eq(n\\,12)+eq(n\\,60)+eq(n\\,108),scale=512:-1',
            '-fps_mode', 'passthrough', '-q:v', '3', str(prefix)], check=True)
        summary.append(summarize(item))
    report = {'status': 'technical_comparison_ready_owner_review_pending',
              'casesSha256': receipt['casesSha256'], 'fullGenerationAttempts': 12,
              'precursorReceipt': receipt['precursorReceipt'], 'results': summary,
              'limitations': 'One run per cell; fresh process and component smoke per arm. '
                  'Landscape is the first full clip, later clips warm; disk/library caches retained. '
                  'Observer overhead identical; CUDA stage time is not pure kernel time. '
                  'Host MemAvailable and process RSS overlap on UMA; sampled values are not exact GPU peaks.'}
    save(root / 'comparison.json', report)
    (root / 'index.html').write_text(render(frozen, report), encoding='utf-8')
    return report


def render(frozen: dict, report: dict) -> str:
    def esc(value):
        return html.escape(str(value), quote=True)

    values = {(row['arm'], row['caseId']): row for row in report['results']}
    blocks = []
    for case in frozen['cases']:
        cards = []
        for arm in ARMS:
            item = values[(arm, case['id'])]
            memory = item['hostMemory']
            encode = item['timing']['video_encode']['outerWallMs'] / 1000
            decode = item['timing']['video_decode']['outerWallMs'] / 1000
            available = memory['minAvailableKiB'] / 1024**2
            samples = ''.join(f'<img src="{arm}_{case["id"]}_{number:02d}.jpg" '
                              f'alt="Frame {frame}">'
                              for number, frame in enumerate((12, 60, 108), start=1))
            cards.append(f'''<article><h3>{arm} · {esc(LABELS[arm])}</h3>
<video controls preload="metadata" src="{arm}_{case['id']}.mp4"></video>
<p>Total {item['submitToObservedCompletionMs']/1000:.1f}s · video VAE encode {encode:.2f}s / decode {decode:.2f}s<br>
Minimum host available {available:.1f} GiB</p><div class="frames">{samples}</div></article>''')
        blocks.append(f'''<section><h2>{esc(case['id'])} · {case['width']}×{case['height']}</h2>
<p>Expected dialogue: {esc(case['dialogue'])}</p>
<details><summary>Frozen first frame</summary><img class="reference" src="input/{case['id']}.png" alt="Frozen {esc(case['id'])} input"></details>
<div class="grid">{''.join(cards)}</div></section>''')
    headers = '<tr><th>Case / arm</th><th>Total s</th><th>VAE encode s</th><th>VAE decode s</th><th>Host available GiB</th></tr>'
    rows = ''.join(f'''<tr><td>{esc(row['caseId'])} / {row['arm']}</td>
<td>{row['submitToObservedCompletionMs']/1000:.1f}</td>
<td>{row['timing']['video_encode']['outerWallMs']/1000:.2f}</td>
<td>{row['timing']['video_decode']['outerWallMs']/1000:.2f}</td>
<td>{row['hostMemory']['minAvailableKiB']/1024**2:.1f}</td></tr>'''
                   for row in report['results'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>H3 VAE comparison</title>
<style>body{{background:#0b1118;color:#e7edf4;font:16px system-ui;max-width:1700px;margin:auto;padding:24px}}
h1,h2{{color:#e9b757}}p{{line-height:1.6}}section{{margin:40px 0}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}}
article{{background:#111d28;border:1px solid #304253;border-radius:12px;padding:12px}}h3{{font-size:16px}}
video{{width:100%;height:350px;background:#000;object-fit:contain}}.reference{{max-width:100%;max-height:400px}}
.frames{{display:flex;gap:4px}}.frames img{{width:32%;object-fit:contain}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #304253;text-align:left}}
@media(max-width:1100px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>H3 video VAE comparison</h1><p>Same frozen inputs, seeds and sampling; video precision/checkpoint only.
Audio remains BF16. 124 frames at 24 fps. No production adoption yet.</p>
<p>Compare intended words, identity, lip-sync, subtitles, shaking/drift and seams. Play one video at a time.</p>
{''.join(blocks)}<h2>Measured timings</h2><table>{headers}{rows}</table>
<p>{esc(report['limitations'])} VAE values above are synchronized outer wall time, including model management.</p>
<p><a href="comparison.json">Detailed timing / kernel / memory summary</a></p></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.root)
    print(json.dumps({'status': result['status'], 'clipCount': len(result['results'])}))
