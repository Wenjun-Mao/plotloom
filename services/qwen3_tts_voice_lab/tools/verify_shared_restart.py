"""Idle control-service restart proof; reads existing media, never generates."""

import argparse
import json
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path

from compare_h3_references import NoRedirect, save
from qualify_published_takes import GATEWAY, GATEWAY_DB, LAB, LAB_DB, VOICE, sha
from qualification_receipts import claim_receipt


def database_hash(path):
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        tables = {table: db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
                  for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return sha(json.dumps(tables, sort_keys=True).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-receipt', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    qualification = json.loads(args.source_receipt.read_text())
    assert qualification['status'] == 'passed' and qualification['generationCalls'] == 0
    config = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    key = next(value.split('=', 1)[1] for value in config['Config']['Env'] if value.startswith('H3_API_KEY='))
    opener = urllib.request.build_opener(NoRedirect())

    def get(path, *, lab=False, binary=False):
        request = urllib.request.Request((LAB if lab else GATEWAY) + path, method='GET',
                                         headers={} if lab else {'Authorization': 'Bearer ' + key})
        with opener.open(request, timeout=10) as response:
            return response.read() if binary else json.load(response)

    def idle():
        health = get('/health')
        assert health['status'] == 'ok' and not health['queuedJobs'] and not health['activeDispatches']
        assert not get('/health', lab=True)['workerActive']
        queue = json.load(urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=5))
        assert not queue['queue_running'] and not queue['queue_pending']
        with sqlite3.connect(LAB_DB) as db:
            assert not db.execute('SELECT 1 FROM execution_grants WHERE release_confirmed=0').fetchone()

    take_ids = [qualification[name]['takeId'] for name in ('firstResult', 'secondResult')]
    video_id = qualification['videoResult']['id']

    def capture():
        voices = get('/api/voices', lab=True)
        takes = [get('/v1/voice-takes/' + take_id) for take_id in take_ids]
        for take in takes:
            assert take['status'] == 'completed' and take['voiceId'] == VOICE
            for kind in ('source', 'h3'):
                assert sha(get(f'/v1/voice-takes/{take["takeId"]}/audio?kind={kind}', binary=True)) == take[kind + 'Sha256']
        assert sha(get('/v1/video-jobs/' + video_id + '/output', binary=True)) == qualification['outputSha256']
        root = LAB_DB.parent
        waves = {str(path.relative_to(root)): sha(path.read_bytes()) for path in root.rglob('*.wav')}
        return {'voices': voices, 'takes': takes, 'waves': waves,
                'databases': {'lab': database_hash(LAB_DB), 'gateway': database_hash(GATEWAY_DB)}}

    record = {'status': 'preflight', 'generationCalls': 0,
              'sourceReceiptSha256': sha(args.source_receipt.read_bytes())}
    try:
        idle(); before = capture()
        record['status'] = 'restart_intent'; save(args.receipt, record)
        subprocess.run(['docker', 'restart', 'plotloom-h3-gateway'], check=True)
        subprocess.run(['systemctl', '--user', 'restart', 'plotloom-voice-lab.service'], check=True)
        deadline = time.monotonic() + 60
        while True:
            try:
                idle(); break
            except (OSError, AssertionError):
                if time.monotonic() >= deadline: raise
                time.sleep(1)
        after = capture()
        assert before == after, 'restart.changed_persistence'
        record.update(status='passed', voiceCount=len(before['voices']['voices']), wavCount=len(before['waves']),
                      takeIds=take_ids, voiceId=VOICE, videoId=video_id,
                      databaseHashes=before['databases'], managedWavHashes=before['waves'],
                      mediaHashes=[{key: take[key] for key in ('takeId', 'sourceSha256', 'h3Sha256')} for take in before['takes']],
                      videoSha256=qualification['outputSha256'], idleAfter=True)
    except Exception as error:
        record.update(status='failed', failure=str(error)); raise
    finally:
        save(args.receipt, record)
        print('Idle restart', record['status'], 'new generation calls: 0', flush=True)


if __name__ == '__main__': main()
