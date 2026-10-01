"""Idle, preservation-only Spark cutover preparation; never starts inference."""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path('/home/wjmao/services')
LAB = ROOT / 'plotloom-voice-lab'
GATEWAY = ROOT / 'plotloom-h3-gateway'
SOURCE = GATEWAY / 'source/services/minimax_h3_gateway'
UNIT = Path('/home/wjmao/.config/systemd/user/plotloom-voice-lab.service')


def rows(path):
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        return {table: {'columns': [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')],
                        'rows': db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()}
                for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file() and path.suffix not in {'.sqlite3', '.sqlite3-wal', '.sqlite3-shm'}}


def fetch(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def idle():
    health = fetch('http://100.64.35.71:8090/health')
    assert health['status'] == 'ok' and not health['queuedJobs'] and not health['activeDispatches'], 'cutover.gateway_busy'
    assert not fetch('http://100.64.35.71:8897/health')['workerActive'], 'cutover.lab_busy'
    queue = fetch('http://127.0.0.1:8188/queue')
    assert not queue['queue_running'] and not queue['queue_pending'], 'cutover.comfy_busy'
    with sqlite3.connect(LAB / 'data/voice_lab.sqlite3') as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('generations', 'clone_trials', 'voice_takes'):
            if table in tables:
                assert not db.execute(f"SELECT 1 FROM {table} WHERE status IN ('queued','running')").fetchone(), 'cutover.lab_admitted_work'
        if 'execution_grants' in tables:
            assert not db.execute('SELECT 1 FROM execution_grants WHERE release_confirmed=0').fetchone(), 'cutover.unreleased_grant'


def prepare(backup):
    idle()
    backup.mkdir(mode=0o700, parents=False, exist_ok=False)
    # Stop admissions before the definitive database checks; preserve stopped
    # owners on refusal rather than restarting independent inference queues.
    subprocess.run(['systemctl', '--user', 'stop', 'plotloom-voice-lab.service'], check=True)
    subprocess.run(['docker', 'stop', 'plotloom-h3-gateway'], check=True)
    with sqlite3.connect(GATEWAY / 'data/gateway.sqlite3') as db:
        assert not db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','submitting','submitted','running','transfer_pending')").fetchone(), 'cutover.gateway_admission_race'
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='generation_lane'").fetchone():
            assert not db.execute("SELECT 1 FROM generation_lane WHERE state!='done'").fetchone(), 'cutover.active_lane'
    with sqlite3.connect(LAB / 'data/voice_lab.sqlite3') as db:
        for table in ('generations', 'clone_trials'):
            assert not db.execute(f"SELECT 1 FROM {table} WHERE status IN ('queued','running')").fetchone(), 'cutover.lab_admission_race'
    from memory_trace import sample
    assert not any(p['label'] == 'voice_engine' for p in sample()['processes']), 'cutover.live_engine'
    record = {'status': 'preserved_stopped', 'services': {}}
    for label, root, name in [('lab', LAB, 'voice_lab.sqlite3'), ('gateway', GATEWAY, 'gateway.sqlite3')]:
        data, destination = root / 'data', backup / label
        original = rows(data / name)
        content = hashes(data)
        shutil.copytree(data, destination)
        with sqlite3.connect(data / name) as db, sqlite3.connect(destination / name) as target:
            db.backup(target)
        assert rows(destination / name) == original
        assert hashes(destination) == content
        record['services'][label] = {'tableCounts': {t: len(v['rows']) for t, v in original.items()}, 'fileHashes': content}
    private = backup / 'configuration'; private.mkdir(mode=0o700)
    for source, name in [(LAB / 'runtime.json', 'runtime.json'), (UNIT, 'voice-lab.service'), (SOURCE / '.env', 'gateway.env')]:
        shutil.copy2(source, private / name)
        (private / name).chmod(0o600)
    shutil.copytree(SOURCE, backup / 'gateway-source')
    info = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    record['previousGatewayImage'] = info['Image']
    (backup / 'preservation.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'backup': str(backup),
                      'tableCounts': {k: v['tableCounts'] for k, v in record['services'].items()}}))


def configure(release):
    state = subprocess.run(['systemctl', '--user', 'is-active', 'plotloom-voice-lab.service'],
                           text=True, capture_output=True)
    assert state.stdout.strip() != 'active', 'cutover.lab_still_active'
    key = secrets.token_urlsafe(48)
    content = f'VOICE_LAB_GATEWAY_URL=http://100.64.35.71:8090\nVOICE_LAB_DISPATCH_KEY={key}\n'
    descriptor = os.open(LAB / 'dispatch.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as file:
        file.write(content)
    env = SOURCE / '.env'
    lines = [line for line in env.read_text().splitlines() if not line.startswith(('H3_VOICE_LAB_URL=', 'H3_VOICE_LAB_KEY='))]
    lines += ['H3_VOICE_LAB_URL=http://100.64.35.71:8897', 'H3_VOICE_LAB_KEY=' + key]
    env.write_text('\n'.join(lines) + '\n'); env.chmod(0o600)
    shutil.copy2(release / 'plotloom-voice-lab.service', UNIT)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    print('Private dispatch configuration installed; no secret returned.')


def verify(backup):
    record = json.loads((backup / 'preservation.json').read_text())
    for label, root, name in [('lab', LAB, 'voice_lab.sqlite3'), ('gateway', GATEWAY, 'gateway.sqlite3')]:
        before = rows(backup / label / name)
        with sqlite3.connect(root / 'data' / name) as db:
            assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            for table, value in before.items():
                columns = ','.join(f'"{column}"' for column in value['columns'])
                assert db.execute(f'SELECT {columns} FROM "{table}" ORDER BY rowid').fetchall() == value['rows'], f'cutover.changed_{label}_{table}'
        current = hashes(root / 'data')
        assert all(current.get(path) == digest for path, digest in record['services'][label]['fileHashes'].items()), 'cutover.asset_changed'
    print('Both SQLite migrations preserved original columns/rows and all managed files.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'configure', 'verify'])
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    args = parser.parse_args()
    if args.backup.parent.resolve() != LAB or args.release.parent.resolve() != LAB / 'releases':
        raise ValueError('cutover.invalid_scope')
    if args.operation == 'prepare': prepare(args.backup)
    elif args.operation == 'configure': configure(args.release)
    else: verify(args.backup)


if __name__ == '__main__': main()
