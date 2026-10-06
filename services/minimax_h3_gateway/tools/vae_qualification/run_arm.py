"""One cold arm: component proof then three sole, serial generation submissions."""
from __future__ import annotations

import argparse
import copy
import fcntl
import importlib.util
import json
import time
from pathlib import Path

import requests
from contract import (
    ARMS,
    AUDIO,
    CASE_IDS,
    claim,
    digest,
    fingerprint,
    graph_for,
    save,
    validate_observations,
)


def rows(path: Path, offset: int) -> list[dict]:
    with path.open() as stream:
        stream.seek(offset)
        return [json.loads(line) for line in stream if line.strip()]


def require_idle(session, url):
    queue = session.get(url + '/queue', timeout=10)
    queue.raise_for_status()
    if queue.json().get('queue_running') or queue.json().get('queue_pending'):
        raise RuntimeError('Comfy queue not empty; no interleaving')


def submit_once(session, url, graph, item, persist, deadline_seconds=1800):
    require_idle(session, url)
    item['state'] = 'outcome_unknown'
    persist()  # Written BEFORE the only POST; an HTTP exception never retries.
    started = time.monotonic()
    response = session.post(url + '/prompt', json={'prompt': graph}, timeout=30)
    if response.status_code != 200:
        item.update(state='request_rejected', httpStatus=response.status_code)
        persist()
        raise RuntimeError('Comfy admission rejected; no replacement')
    item.update(state='accepted', promptId=response.json()['prompt_id'])
    persist()
    while time.monotonic() - started < deadline_seconds:
        response = session.get(url + '/history/' + item['promptId'], timeout=15)
        response.raise_for_status()
        record = response.json().get(item['promptId'])
        if record and record.get('status', {}).get('status_str') == 'error':
            item.update(state='execution_failed', history=record)
            persist()
            raise RuntimeError('Known execution failure; no replay')
        if record and record.get('status', {}).get('completed'):
            item.update(state='execution_completed', elapsedMs=round((time.monotonic() - started) * 1000))
            persist()
            return record
        time.sleep(3)
    item['state'] = 'outcome_unknown'
    persist()
    raise RuntimeError('Completion deadline; preserve active runtime until reconciled')


def inspect_media(path):
    import subprocess
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,nb_frames,r_frame_rate,sample_rate',
        '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0',
                    '-map', '0:a:0', '-f', 'null', '-'], check=True, capture_output=True)
    return json.loads(result.stdout)


def run(root: Path, arm: str, url: str):
    with (root / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(root, arm, url)


def run_locked(root: Path, arm: str, url: str):
    path = root / 'receipt.json'
    if not path.exists():
        raise RuntimeError('Director must freeze receipt before arm execution')
    receipt = json.loads(path.read_text())
    if receipt['status'] != 'running':
        raise RuntimeError('Experiment stopped; refuse every new GPU request')
    if arm in receipt['smokes'] or any(x['arm'] == arm for x in receipt['calls']):
        raise RuntimeError('Arm already entered; refuse replay')
    frozen = json.loads((root / 'cases.json').read_text())
    if fingerprint(frozen) != receipt['casesSha256']:
        raise RuntimeError('Cases changed after freeze')
    if digest(root / 'memory_trace.py') != receipt['memoryObserverSha256']:
        raise RuntimeError('Memory observer changed after freeze')
    if tuple(x['id'] for x in frozen['cases']) != CASE_IDS:
        raise RuntimeError('Case order changed')
    for asset in frozen['assets']:
        if digest(Path(asset['path'])) != asset['sha256']:
            raise RuntimeError('Frozen asset changed')
    events = root / f'{arm}-events.jsonl'
    startup = rows(events, 0)
    observer = [x for x in startup if x['kind'] == 'observer']
    if len(observer) != 1 or observer[0]['fp16Accumulation'] != ARMS[arm]['fast']:
        raise RuntimeError('Runtime precision flag/observer mismatch')
    # Reuse the existing CPU-only host-memory observer without a CUDA context.
    spec = importlib.util.spec_from_file_location('memory_trace', root / 'memory_trace.py')
    memory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(memory)
    persist = lambda: save(path, receipt)
    session = requests.Session()
    try:
        smoke = {'state': 'outcome_unknown'}
        receipt['smokes'][arm] = smoke
        persist()
        graph = {
            'video': {'class_type': 'QualificationVideoVAELoader', 'inputs': {
                'vae_name': ARMS[arm]['checkpoint'], 'precision': ARMS[arm]['dtype']}},
            'audio': {'class_type': 'VAELoader', 'inputs': {'vae_name': AUDIO}},
            'smoke': {'class_type': 'QualificationVAESmoke',
                      'inputs': {'video': ['video', 0], 'audio': ['audio', 0]}},
        }
        offset = events.stat().st_size
        record = submit_once(session, url, graph, smoke, persist)
        smoke['observations'] = rows(events, offset)
        validate_observations(smoke['observations'], arm, smoke=True)
        smoke.update(state='passed', history=record)
        persist()
        print(json.dumps({'arm': arm, 'componentSmoke': 'passed'}), flush=True)
        # Clear component-loaded objects before the first full clip. No prompt
        # cache hit may substitute for a measured encode/decode or denoising run.
        session.post(url + '/free', json={'unload_models': True, 'free_memory': True}, timeout=30).raise_for_status()
        for case in frozen['cases']:
            item = claim(receipt, arm, case['id'])
            graph = graph_for(case, arm)
            item['graphSha256'] = fingerprint(graph)
            save(root / f'{arm}_{case["id"]}-graph.json', graph)
            offset = events.stat().st_size
            with memory.MemoryTrace(root / f'{arm}_{case["id"]}-memory.jsonl') as trace:
                trace.mark(phase='generation', case=case['id'], arm=arm)
                record = submit_once(session, url, graph, item, persist)
                item['observations'] = rows(events, offset)
                validate_observations(item['observations'], arm, smoke=False)
                cached = {node for kind, data in record['status'].get('messages', [])
                          if kind == 'execution_cached' for node in data.get('nodes', [])}
                required = {'105:14', '105:104', '105:10', '105:23'}
                if case['id'] == 'voice':
                    required.add('voice_first_frame_guide')
                if cached & required:
                    raise RuntimeError('Required generation nodes cached')
                item['cachedNodeIds'] = sorted(cached)
                save(root / f'{arm}_{case["id"]}-history.json', record)
                outputs = [entry for output in record['outputs'].values()
                           for entry in output.get('images', []) if entry['filename'].endswith('.mp4')]
                if len(outputs) != 1:
                    raise RuntimeError('Expected exactly one MP4')
                output = outputs[0]
                media = root / f'output-{arm}' / output['subfolder'] / output['filename']
                if not media.resolve().is_relative_to((root / f'output-{arm}').resolve()):
                    raise RuntimeError('Output path outside isolated mount')
                details = inspect_media(media)
                video = next(x for x in details['streams'] if x['codec_type'] == 'video')
                audio = next(x for x in details['streams'] if x['codec_type'] == 'audio')
                if (video['width'], video['height'], int(video['nb_frames'])) != (case['width'], case['height'], 124):
                    raise RuntimeError('Geometry/frame mismatch')
                if audio['codec_name'] != 'aac' or not 5 <= float(details['format']['duration']) < 5.3:
                    raise RuntimeError('Audio/duration mismatch')
                item.update(state='passed', outputPath=str(media), outputSha256=digest(media),
                            media=details, fullDecode='passed')
            item['hostMemory'] = copy.deepcopy(trace.summary)
            persist()
            print(json.dumps({'arm': arm, 'case': case['id'], 'state': item['state'],
                              'elapsedMs': item['elapsedMs']}), flush=True)
    except BaseException as error:
        receipt.update(status='stopped', errorType=type(error).__name__, error=str(error))
        persist()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--arm', required=True, choices=ARMS)
    parser.add_argument('--url', default='http://127.0.0.1:8193')
    args = parser.parse_args()
    run(args.root, args.arm, args.url)
