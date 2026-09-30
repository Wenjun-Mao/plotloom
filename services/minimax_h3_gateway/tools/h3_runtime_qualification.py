#!/usr/bin/env python3
"""Five-call, no-replay Spark runtime qualification; private experiment evidence."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import threading
import time
from pathlib import Path

import requests
from h3_prompt_robustness_study import PROMPTS, RECIPES, render_workflow
from PIL import Image, ImageOps

ROOT = Path('/home/wjmao/services/spark-comfyui')
EXPERIMENT = 'h3-runtime-038-2026-09-30'
WORK = ROOT / 'experiments' / EXPERIMENT
INPUT = ROOT / 'data/input'
OUTPUT = ROOT / 'data/output'
TEMPLATE = Path('/home/wjmao/services/plotloom-h3-gateway/source/services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json')
BASE_COMMIT = 'd43a5fa20c8547ff42d13232f589a06536c42b97'
NEXT_COMMIT = '6b747c0428c343e1417219641db93a4fb7cb69ae'


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def save(path: Path, value: dict) -> None:
    staging = path.with_suffix('.tmp')
    staging.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    staging.replace(path)


def graph_hash(graph: dict) -> str:
    normalized = copy.deepcopy(graph)
    normalized['92']['inputs']['filename_prefix'] = '__OUTPUT_ONLY__'
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def freeze() -> None:
    if (WORK / 'cases.json').exists():
        raise RuntimeError('Frozen cases already exist; refuse to overwrite')
    target = INPUT / 'experiments' / EXPERIMENT
    target.mkdir(parents=True, exist_ok=True)
    landscape = INPUT / '2026-09-18T03-34-33Z_h3_97c452ef25714d4ba32ce3362fae12ff_start.png'
    portrait = INPUT / 'experiments/h3-cross-geometry-2026-09-20/dialogue_portrait_v1_704x1280.png'
    with Image.open(landscape) as image:
        ImageOps.fit(image.convert('RGB'), (1280, 704), method=Image.Resampling.LANCZOS).save(target / 'landscape.png')
    with Image.open(portrait) as image:
        if image.size != (704, 1280):
            raise RuntimeError('Portrait reference geometry mismatch')
        image.save(target / 'portrait.png')
    template = json.loads(TEMPLATE.read_text())['prompt']
    cases = []
    for name, width, height in [('landscape', 1280, 704), ('portrait', 704, 1280)]:
        graph = render_workflow(template, recipe=RECIPES[1],
            prompt=PROMPTS['audio_only_visual_no_text_v1'], seed=20260930,
            input_name=f'experiments/{EXPERIMENT}/{name}.png', output_prefix='__OUTPUT__',
            width=width, height=height, frame_count=124)
        cases.append({'id': name, 'graph': graph, 'graphSha256': graph_hash(graph),
            'width': width, 'height': height, 'inputSha256': digest(target / f'{name}.png')})
    spec = importlib.util.spec_from_file_location('reviewed_ref2va', ROOT / 'experiments/h3-ref2va-portrait-2026-09-26/operator.py')
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    for path, expected in [(operator.MODEL, operator.MODEL_SHA256),
                           (operator.INPUT_DIR / operator.SCENES['c1_portrait']['image'], operator.IMAGE_SHA256),
                           (operator.INPUT_DIR / operator.VOICE, operator.VOICE_SHA256)]:
        if digest(path) != expected:
            raise RuntimeError(f'Reviewed reference hash mismatch: {path.name}')
    graph = operator.graph_for('c1_portrait', operator.prompt_for('c1_portrait'))
    cases.append({'id': 'voice', 'graph': graph, 'graphSha256': graph_hash(graph),
                  'width': 576, 'height': 1024})
    save(WORK / 'cases.json', {'caseCount': 3, 'templateSha256': digest(TEMPLATE),
        'landscapeSourceSha256': digest(landscape), 'landscapePreparation': 'center fit once, 832x480 to 1280x704',
        'portraitSourceSha256': digest(portrait), 'cases': cases})
    print('Frozen two quality-1 cases and one reviewed Ref2VA case', flush=True)


def memory_sample(pid: int) -> dict:
    fields = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in {'MemAvailable', 'MemFree', 'Cached'}:
            fields[key + 'KiB'] = int(value.split()[0])
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith(('VmRSS:', 'VmHWM:')):
                key, value = line.split(':', 1)
                fields[key + 'KiB'] = int(value.split()[0])
    except FileNotFoundError:
        fields['processMissing'] = True
    return fields


def comfy_pid() -> int:
    listing = subprocess.check_output(['docker', 'top', 'spark-comfyui', '-eo', 'pid,args'], text=True)
    matches = [int(line.split(maxsplit=1)[0]) for line in listing.splitlines()[1:]
               if 'main.py' in line.split(maxsplit=1)[1].split()]
    if len(matches) != 1:
        raise RuntimeError('Cannot identify the one ComfyUI process for memory sampling')
    return matches[0]


def sample_memory(pid: int, samples: list[dict], stop: threading.Event) -> None:
    while not stop.is_set():
        samples.append(memory_sample(pid))
        stop.wait(1)


def inspect_media(path: Path) -> dict:
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,nb_frames,r_frame_rate,sample_rate',
        '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0',
        '-map', '0:a:0', '-f', 'null', '-'], check=True, capture_output=True)
    return json.loads(result.stdout)


def runtime_mounts(phase: str, *, candidate_user: Path | None = None) -> list[dict]:
    expected = str(ROOT / 'data/user') if phase == 'baseline' else str(candidate_user or WORK / 'candidate-user')
    if phase == 'candidate' and expected == str(ROOT / 'data/user'):
        raise RuntimeError('Candidate user directory cannot be the production baseline directory')
    details = json.loads(subprocess.check_output(['docker', 'inspect', 'spark-comfyui'], text=True))[0]
    bindings = {item['Destination']: item['Source'] for item in details['Mounts']}
    if bindings.get('/opt/ComfyUI/user') != expected:
        raise RuntimeError('Unexpected Comfy user mount; production metadata must remain isolated')
    if bindings.get('/opt/ComfyUI/models') != '/home/wjmao/models/comfyui-h3':
        raise RuntimeError('Model root changed')
    return [{'source': item['Source'], 'destination': item['Destination'], 'readWrite': item['RW']}
            for item in details['Mounts']]


def inventory(phase: str, *, candidate_user: Path | None = None) -> None:
    mounts = runtime_mounts(phase, candidate_user=candidate_user)
    details = json.loads(subprocess.check_output(['docker', 'inspect', 'spark-comfyui'], text=True))[0]
    packages = subprocess.check_output(['docker', 'exec', 'spark-comfyui', 'python', '-c',
        'import importlib.metadata as m,json; print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()}))'], text=True)
    commit = subprocess.check_output(['docker', 'exec', 'spark-comfyui', 'git', '-C', '/opt/ComfyUI', 'rev-parse', 'HEAD'], text=True).strip()
    save(WORK / f'{phase}-runtime.json', {'comfyCommit': commit, 'imageId': details['Image'],
        'launchCmd': details['Config']['Cmd'], 'entrypoint': details['Config']['Entrypoint'],
        'portBindings': details['HostConfig']['PortBindings'],
        'restartPolicy': details['HostConfig']['RestartPolicy'], 'mounts': mounts,
        'packages': json.loads(packages), 'hostMemory': memory_sample(comfy_pid())})


def run(phase: str, *, call_cap: int | None = None, candidate_user: Path | None = None) -> None:
    path = WORK / f'{phase}-receipt.json'
    if path.exists():
        raise RuntimeError('Receipt already exists; ambiguous or completed work cannot be replayed')
    runtime_mounts(phase, candidate_user=candidate_user)
    expected = BASE_COMMIT if phase == 'baseline' else NEXT_COMMIT
    commit = subprocess.check_output(['docker', 'exec', 'spark-comfyui', 'git', '-C', '/opt/ComfyUI', 'rev-parse', 'HEAD'], text=True).strip()
    if commit != expected:
        raise RuntimeError('Unexpected live runtime revision')
    pid = comfy_pid()
    document = json.loads((WORK / 'cases.json').read_text())
    if digest(TEMPLATE) != document['templateSha256']:
        raise RuntimeError('Frozen template changed')
    call_cap = call_cap if call_cap is not None else (2 if phase == 'baseline' else 3)
    if not 1 <= call_cap <= 3 or len(document['cases']) < call_cap:
        raise RuntimeError('Invalid bounded generation call cap')
    receipt = {'phase': phase, 'comfyCommit': commit, 'generationCallCap': call_cap,
               'generationCalls': 0, 'status': 'running', 'results': [],
               'memoryMeasurement': '1 Hz host availability and process RSS/HWM; not GPU allocation peak'}
    save(path, receipt)
    session = requests.Session()
    try:
        for case in document['cases'][:call_cap]:
            if graph_hash(case['graph']) != case['graphSha256']:
                raise RuntimeError('Frozen graph changed')
            if 'inputSha256' in case:
                image = INPUT / case['graph']['h3_prompt_study_start_frame']['inputs']['image']
                if digest(image) != case['inputSha256']:
                    raise RuntimeError('Frozen input image changed')
            queue = session.get('http://127.0.0.1:8188/queue', timeout=10).json()
            if queue.get('queue_running') or queue.get('queue_pending'):
                raise RuntimeError('Unrelated ComfyUI queue work; refuse to interleave')
            graph = copy.deepcopy(case['graph'])
            graph['92']['inputs']['filename_prefix'] = f'experiments/{EXPERIMENT}/{phase}_{case["id"]}'
            item = {'caseId': case['id'], 'graphSha256': case['graphSha256'], 'state': 'outcome_unknown',
                    'beforeMemory': memory_sample(pid)}
            receipt['generationCalls'] += 1
            receipt['results'].append(item)
            save(path, receipt)  # Persist uncertainty before the sole POST.
            samples = []
            stop = threading.Event()
            watcher = threading.Thread(target=sample_memory, args=(pid, samples, stop), daemon=True)
            watcher.start()
            started = time.monotonic()
            try:
                response = session.post('http://127.0.0.1:8188/prompt',
                    json={'prompt': graph, 'client_id': EXPERIMENT}, timeout=30)
                if response.status_code != 200:
                    item.update(state='request_rejected', httpStatus=response.status_code)
                    raise RuntimeError(f'ComfyUI admission rejected: {response.status_code}')
                prompt_id = response.json()['prompt_id']
                item.update(state='accepted', promptId=prompt_id)
                save(path, receipt)
                deadline = time.monotonic() + 1800
                while time.monotonic() < deadline:
                    history = session.get(f'http://127.0.0.1:8188/history/{prompt_id}', timeout=15).json()
                    record = history.get(prompt_id)
                    if record and record.get('status', {}).get('status_str') == 'error':
                        save(WORK / f'{phase}_{case["id"]}-history.json', record)
                        item['state'] = 'execution_failed'
                        raise RuntimeError('Known ComfyUI execution failure; no replay')
                    if record and record.get('status', {}).get('completed'):
                        break
                    time.sleep(3)
                else:
                    item['state'] = 'outcome_unknown'
                    raise RuntimeError('Completion timeout; no replay')
                item['elapsedMs'] = round((time.monotonic() - started) * 1000)
                save(WORK / f'{phase}_{case["id"]}-history.json', record)
                messages = record['status'].get('messages', [])
                item['cachedNodeIds'] = [node for kind, data in messages if kind == 'execution_cached' for node in data.get('nodes', [])]
                files = [entry for node in record['outputs'].values() for entry in node.get('images', []) if entry.get('filename', '').endswith('.mp4')]
                if len(files) != 1:
                    raise RuntimeError('Expected exactly one MP4')
                output = files[0]
                media = OUTPUT / output['subfolder'] / output['filename']
                metadata = inspect_media(media)
                video = next(x for x in metadata['streams'] if x['codec_type'] == 'video')
                audio = next(x for x in metadata['streams'] if x['codec_type'] == 'audio')
                if (video['width'], video['height'], int(video['nb_frames'])) != (case['width'], case['height'], 124):
                    raise RuntimeError('Media geometry/frame contract mismatch')
                if audio['codec_name'] != 'aac' or not 5 <= float(metadata['format']['duration']) < 5.3:
                    raise RuntimeError('Media audio/duration contract mismatch')
                item.update(state='completed', output=output, outputSha256=digest(media), media=metadata, fullStreamDecode='passed')
            finally:
                stop.set()
                watcher.join(timeout=3)
                item['sampledMemory'] = {'count': len(samples),
                    'minHostAvailableKiB': min((x['MemAvailableKiB'] for x in samples), default=None),
                    'maxProcessRSSKiB': max((x.get('VmRSSKiB', 0) for x in samples), default=None),
                    'maxProcessHWMKiB': max((x.get('VmHWMKiB', 0) for x in samples), default=None)}
                save(path, receipt)
            print(json.dumps({key: item[key] for key in ('caseId', 'state', 'elapsedMs', 'output')}, ensure_ascii=False), flush=True)
        receipt['status'] = 'completed'
    except Exception as error:
        receipt.update(status='stopped', errorType=type(error).__name__, error=str(error))
        raise
    finally:
        save(path, receipt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'baseline', 'candidate', 'baseline-inventory', 'candidate-inventory', 'candidate-mount-proof'])
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze()
    elif args.action == 'candidate-mount-proof':
        save(WORK / 'candidate-mount-proof.json', {'mounts': runtime_mounts('candidate'), 'passed': True})
    elif args.action.endswith('-inventory'):
        inventory(args.action.split('-')[0])
    else:
        run(args.action)
