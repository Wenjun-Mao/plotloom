"""Restart only an idle Lab and prove published bytes and project state survive."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import time
from pathlib import Path

from qualification_receipts import claim_receipt
from qualify_workflow import api, sample_memory
from verify_resident_reuse import idle

ROOT = Path('/home/wjmao/services/plotloom-voice-lab')
UNIT = 'plotloom-voice-lab.service'


def state(project_id: str, original_trial_id: str) -> dict:
    return {
        'project': api('/api/projects/' + project_id),
        'trials': api('/api/clone-trials?projectId=' + project_id),
        'originalFailure': api('/api/clone-trials/' + original_trial_id),
        'published': {
            item['voiceId']: {
                kind: hashlib.sha256(api('/api/voices/' + item['voiceId'] + '/audio?kind=' + kind,
                                         binary=True)).hexdigest()
                for kind in ('source', 'h3')
            } for item in api('/api/voices')['voices']
        },
        'wavHashes': {str(path.relative_to(ROOT / 'data')): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in (ROOT / 'data').rglob('*.wav')},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--original-trial-id', required=True)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    before_health = idle()
    before = state(args.project_id, args.original_trial_id)
    assert before['originalFailure']['status'] == 'failed'
    record = {'status': 'restart_not_started', 'generationCalls': 0,
              'beforeHealth': before_health, 'beforeState': before}

    def save():
        temporary = args.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.chmod(0o600)
        temporary.replace(args.receipt)

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    save()
    try:
        record['status'] = 'restart_started'
        save()
        subprocess.run(['systemctl', '--user', 'restart', UNIT], check=True, timeout=30)
        deadline = time.monotonic() + 30
        while True:
            try:
                api('/health')
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('restart.health_unavailable')
                time.sleep(1)
        assert state(args.project_id, args.original_trial_id) == before, 'restart.state_changed'
        with sqlite3.connect(f'file:{ROOT / "data/voice_lab.sqlite3"}?mode=ro', uri=True) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        record.update(status='passed', projectAndTrialsUnchanged=True, originalFailureUnchanged=True,
                      publishedHashesUnchanged=True, unchangedWavs=len(before['wavHashes']), integrity='ok',
                      finalHealth=idle(), afterMemory=sample_memory())
    except Exception as error:
        record.update(status='failed_no_automatic_repeat', failure=str(error))
        raise
    finally:
        save()
        print(json.dumps({key: value for key, value in record.items()
                          if key not in ('beforeHealth', 'beforeState', 'finalHealth')}), flush=True)


if __name__ == '__main__':
    main()
