"""One exact neutral reuse probe; keep other services running and never replay."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path

import soundfile as sf
from qualification_receipts import claim_receipt
from qualify_workflow import api, sample_memory


def get(origin: str, path: str) -> dict:
    with urllib.request.urlopen(origin + path, timeout=5) as response:
        return json.load(response)


def idle() -> dict:
    lab = api('/health')
    gateway = get('http://100.64.35.71:8090', '/health')
    comfy = get('http://127.0.0.1:8188', '/queue')
    image = get('http://127.0.0.1:30010', '/health')
    assert not lab['workerActive'] and not sample_memory()['children'], 'lab.busy'
    assert gateway['status'] == 'ok' and not gateway['activeDispatches'] and not gateway['queuedJobs'], 'gateway.busy'
    assert not comfy['queue_running'] and not comfy['queue_pending'], 'comfy.busy'
    assert image['status'] == 'ok', 'image.not_ready'
    return {'lab': lab, 'gateway': gateway, 'image': image}


def voice_hashes() -> dict:
    return {v['voiceId']: {kind: hashlib.sha256(api('/api/voices/' + v['voiceId'] + '/audio?kind=' + kind,
                                                   binary=True)).hexdigest()
                         for kind in ('source', 'h3')} for v in api('/api/voices')['voices']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-trial-id', required=True)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--resident-state', choices=['cold_comfy', 'post_h3'], required=True)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    health = idle()
    old = api('/api/clone-trials/' + args.reference_trial_id)
    assert old['engineId'] == 'index_base' and old['delivery']['mode'] == 'none'
    assert old['status'] in ('failed', 'completed'), 'reference.unknown'
    reference = api('/api/generations/' + old['generationId'])
    assert reference['sourceSha256'] == old['sourceSha256'], 'reference.changed'
    project = api('/api/projects/' + old['projectId'])
    saved_selection = project['selectedGenerationId']
    voices = voice_hashes()
    record = {'status': 'preflight', 'residentState': args.resident_state, 'additionalCallCap': 1,
              'synthesisPostCount': 0, 'originalTrial': old, 'beforeMemory': sample_memory(),
              'beforeHealth': health, 'phases': [], 'peakChildCount': 0, 'peakChildRssGiB': 0}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        temporary = args.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        temporary.chmod(0o600)
        temporary.replace(args.receipt)

    save()
    try:
        api('/api/projects/' + old['projectId'] + '/selections', 'POST', {'generationId': old['generationId']})
        # Record dispatch intent before the sole POST. Network uncertainty never
        # grants a second synthesis; inspect the existing task instead.
        record['status'] = 'dispatch_started_no_replay'
        record['synthesisPostCount'] = 1
        save()
        trial = api('/api/clone-trials', 'POST', {'projectId': old['projectId'], 'generationId': old['generationId'],
                    'engineId': 'index_base', 'text': old['text'], 'seed': old['seed'], 'delivery': {'mode': 'none'}})
        record['newTrialId'] = trial['trialId']
        save()
        print('Accepted one resident probe:', trial['trialId'], flush=True)
        path = '/api/clone-trials/' + trial['trialId']
        deadline = time.monotonic() + 1000
        while time.monotonic() < deadline:
            memory = sample_memory()
            record['peakChildCount'] = max(record['peakChildCount'], len(memory['children']))
            assert len(memory['children']) <= 1, 'probe.concurrent_children'
            for child in memory['children']:
                record['peakChildRssGiB'] = max(record['peakChildRssGiB'], child['rssGiB'])
            progress = api(path + '/progress')
            phase = progress.get('phase')
            if phase and phase not in record['phases']:
                record['phases'].append(phase)
                print('Phase:', phase, flush=True)
            trial = api(path)
            if trial['status'] not in ('queued', 'running'):
                break
            time.sleep(2)
        else:
            raise TimeoutError('probe.poll_timeout_no_replay')
        record['result'] = trial
        assert trial['status'] == 'completed', trial.get('errorCode')
        assert all(trial[k] == old[k] for k in ('sourceSha256', 'text', 'seed'))
        for key in ('modelId', 'modelRevision', 'sourceRevision', 'settings'):
            assert trial['executionSnapshot'][key] == old['executionSnapshot'][key], 'probe.changed_contract:' + key
        content = api(path + '/audio', binary=True)
        assert hashlib.sha256(content).hexdigest() == trial['audioSha256']
        info = sf.info(io.BytesIO(content))
        assert info.format == 'WAV' and info.channels == 1 and info.samplerate == 22050 and info.frames > 0
        record['output'] = {'sha256': trial['audioSha256'], 'sampleRate': info.samplerate,
                            'subtype': info.subtype, 'durationSeconds': info.duration}
        record['status'] = 'completed'
    except Exception as error:
        record.update(status='failed_or_uncertain_no_replay', failure=str(error))
        raise
    finally:
        current = api('/api/projects/' + old['projectId'])
        if saved_selection and current['selectedGenerationId'] == old['generationId']:
            api('/api/projects/' + old['projectId'] + '/selections', 'POST', {'generationId': saved_selection})
        record['originalTrialUnchanged'] = api('/api/clone-trials/' + args.reference_trial_id) == old
        record['publishedHashesUnchanged'] = voice_hashes() == voices
        record['afterMemory'] = sample_memory()
        record['finalHealth'] = idle()
        save()
        print('Probe receipt:', args.receipt, 'status:', record['status'], flush=True)
        assert record['originalTrialUnchanged'] and record['publishedHashesUnchanged'], 'probe.preservation_failed'
        assert not record['afterMemory']['children'] and record['peakChildCount'] <= 1, 'probe.child_not_released'


if __name__ == '__main__':
    main()
