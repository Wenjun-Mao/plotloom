"""Operator-only idle proof and identity preservation. No cancellation/reset."""
from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
from pathlib import Path

import requests
from contract import COMMIT, IMAGE, digest, fingerprint, save

LAB_DATA = Path('/home/wjmao/services/plotloom-voice-lab/data')
GATEWAY_DATA = Path('/home/wjmao/services/plotloom-h3-gateway/data')


def canonical_configuration(value: dict) -> dict:
    """Docker inspect's mount order is unstable across start, unlike bindings."""
    result = copy.deepcopy(value)
    result['mounts'] = sorted(result['mounts'], key=lambda item: item['Destination'])
    return result


def lab_proof():
    db = sqlite3.connect(f'file:{LAB_DATA}/voice_lab.sqlite3?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        busy = {table: db.execute(f"SELECT count(*) FROM {table} WHERE status IN ('queued','running')").fetchone()[0]
                for table in ('generations', 'clone_trials', 'voice_takes')}
        grants = db.execute('SELECT count(*) FROM execution_grants WHERE release_confirmed=0').fetchone()[0]
        values = {table: [dict(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY id')]
                  for table in ('voices', 'voice_takes')}
        files = {str(path.relative_to(LAB_DATA)): digest(path)
                 for folder in ('voices', 'takes') for path in (LAB_DATA / folder).rglob('*.wav')}
        return {'busy': busy, 'unreleasedGrants': grants, 'recordHash': fingerprint(values),
                'files': files, 'voiceCount': len(values['voices']), 'takeCount': len(values['voice_takes'])}
    finally:
        db.close()


def gateway_proof(container='plotloom-h3-gateway'):
    # Container user can read its root-owned SQLite; no live permission changes.
    script = """import sqlite3,json
db=sqlite3.connect('file:/var/lib/plotloom-h3-gateway/gateway.sqlite3?mode=ro',uri=True)
print(json.dumps({'busy':db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','submitting','submitted','running','transfer_pending','outcome_unknown')").fetchone()[0],'lane':db.execute("SELECT count(*) FROM generation_lane WHERE state!='done'").fetchone()[0]}))
"""
    running = subprocess.check_output(['docker', 'inspect', container, '--format',
                                      '{{.State.Running}}'], text=True).strip() == 'true'
    if running:
        command = ['docker', 'exec', container, 'python', '-c', script]
    else:
        image = subprocess.check_output(['docker', 'inspect', container, '--format',
                                         '{{.Image}}'], text=True).strip()
        command = ['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python',
                   '--mount', f'type=bind,src={GATEWAY_DATA},dst=/var/lib/plotloom-h3-gateway,readonly',
                   image, '-c', script]
    return json.loads(subprocess.check_output(command, text=True))


def assert_idle():
    gateway = requests.get('http://100.64.35.71:8090/health', timeout=10)
    gateway.raise_for_status()
    info = gateway.json()
    if info['queuedJobs'] or info['activeDispatches']:
        raise RuntimeError('Managed generation lane busy')
    lab = requests.get('http://100.64.35.71:8897/health', timeout=10)
    lab.raise_for_status()
    if lab.json()['workerActive']:
        raise RuntimeError('Voice child worker active')
    proof, voice = gateway_proof(), lab_proof()
    if proof['busy'] or proof['lane'] or any(voice['busy'].values()) or voice['unreleasedGrants']:
        raise RuntimeError('Persisted job/grant unresolved; no maintenance')
    queue = requests.get('http://127.0.0.1:8188/queue', timeout=10)
    queue.raise_for_status()
    if queue.json()['queue_running'] or queue.json()['queue_pending']:
        raise RuntimeError('Direct Comfy work active')
    return voice


def baseline_configuration():
    value = json.loads(subprocess.check_output(['docker', 'inspect', 'spark-comfyui'], text=True))[0]
    if value['Image'] != IMAGE:
        raise RuntimeError('Baseline image changed')
    mounts = {item['Destination']: item['Source'] for item in value['Mounts']}
    if mounts.get('/opt/ComfyUI/user') != '/home/wjmao/services/spark-comfyui/data/user-v038':
        raise RuntimeError('Baseline user mount changed')
    commit = subprocess.check_output(['docker', 'exec', 'spark-comfyui', 'git', '-C',
                                      '/opt/ComfyUI', 'rev-parse', 'HEAD'], text=True).strip()
    if commit != COMMIT:
        raise RuntimeError('Baseline Comfy revision changed')
    processes = subprocess.check_output(['docker', 'top', 'spark-comfyui', '-eo', 'pid,args'], text=True).splitlines()[1:]
    commands = [line.split(maxsplit=1)[1].split() for line in processes if 'main.py' in line.split()]
    if len(commands) != 1 or not {'--bf16-unet', '--bf16-text-enc', '--bf16-vae'} <= set(commands[0]) or '--fast' in commands[0]:
        raise RuntimeError('Baseline launch precision changed')
    # Omit environment values; they may include credentials. The unchanged
    # stopped container is the restoration authority, not a recreated config.
    return {'image': value['Image'], 'containerId': value['Id'],
            'comfyCommit': commit, 'launchArgs': commands[0],
            'entrypoint': value['Config']['Entrypoint'], 'mounts': value['Mounts'],
            'ports': value['HostConfig']['PortBindings'],
            'restartPolicy': value['HostConfig']['RestartPolicy']}


def preserve_before_pause(root: Path):
    if (root / 'maintenance-before.json').exists():
        raise RuntimeError('Maintenance proof exists; refuse a second lifecycle')
    voice = assert_idle()
    configuration = baseline_configuration()
    save(root / 'maintenance-before.json', {'voices': voice, 'baseline': configuration})
    return configuration


def confirm_paused_idle():
    """Recheck admissions racing the stop; queued work is preserved, not cancelled."""
    for name in ('plotloom-h3-gateway', 'spark-comfyui'):
        running = subprocess.check_output(['docker', 'inspect', name, '--format',
                                          '{{.State.Running}}'], text=True).strip()
        if running != 'false':
            raise RuntimeError('Managed control/baseline runtime not paused')
    lab_active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet',
                                 'plotloom-voice-lab.service'], check=False).returncode == 0
    proof, voice = gateway_proof(), lab_proof()
    if lab_active or proof['busy'] or proof['lane'] or any(voice['busy'].values()) or voice['unreleasedGrants']:
        raise RuntimeError('Work raced maintenance; restore control, do not execute')
    return voice
