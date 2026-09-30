"""One bounded private Spark qualification: 3 creation + 6 reuse calls, no retry."""

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from qualification_receipts import claim_receipt

BASE = 'http://100.64.35.71:8897'
LINE = '雨还没有停。主灯，或者码头，我们只能先保住一边。'
DIRECTION = '四十岁左右的中国女性，成熟低音，克制坚韧，自然口语，不要播音腔。'


def api(path, method='GET', body=None, binary=False):
    request = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read()
        return content if binary else json.loads(content)


def sample_memory():
    memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemTotal:', 'MemAvailable:'))}
    children = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit(): continue
        try:
            command = (process / 'cmdline').read_bytes().split(b'\0')
            if b'plotloom_voice_lab.engines.runner' not in command: continue
            status = (process / 'status').read_text().splitlines()
            rss = next(int(line.split()[1]) for line in status if line.startswith('VmRSS:'))
            children.append({'pid': int(process.name), 'rssGiB': round(rss / 1024**2, 3)})
        except (OSError, StopIteration): pass
    return {'availableGiB': round(memory['MemAvailable'] / 1024**2, 3),
            'unavailableGiB': round((memory['MemTotal'] - memory['MemAvailable']) / 1024**2, 3),
            'children': children}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    continuation = parser.add_mutually_exclusive_group()
    continuation.add_argument('--existing-pair', help='Explicitly finish a known failed pair using its one remaining creation call; never replay')
    continuation.add_argument('--delivery-only', help='Use only the final two reuse calls after four neutral trials; never retry a failed trial')
    args = parser.parse_args()
    claim_receipt(args.receipt)
    record = {'status': 'started', 'callCaps': {'creation': 3, 'reuse': 6},
              'beforeMemory': sample_memory(), 'results': [], 'peakChildCount': 0,
              'peakProcessRssGiB': 0, 'hostPeakUnavailableGiB': 0, 'observedProcessIds': []}

    def save(): args.receipt.write_text(json.dumps(record, indent=2) + '\n')
    save()

    def wait(path):
        start = time.monotonic(); phases = []; minimum = float('inf')
        while time.monotonic() - start < 1200:
            memory = sample_memory(); minimum = min(minimum, memory['availableGiB'])
            count = len(memory['children']); record['peakChildCount'] = max(record['peakChildCount'], count)
            assert count <= 1, 'qualification.concurrent_children'
            record['hostPeakUnavailableGiB'] = max(record['hostPeakUnavailableGiB'], memory['unavailableGiB'])
            for child in memory['children']:
                record['peakProcessRssGiB'] = max(record['peakProcessRssGiB'], child['rssGiB'])
                if child['pid'] not in record['observedProcessIds']: record['observedProcessIds'].append(child['pid'])
            progress = api(path + '/progress')
            if progress['phase'] and progress['phase'] not in phases:
                phases.append(progress['phase']); print(f'{path}: {progress["phase"]}', flush=True)
            result = api(path)
            if result['status'] not in ('queued', 'running'):
                result['observedPhases'] = phases; result['minAvailableGiB'] = minimum
                record['results'].append(result); save()
                assert result['status'] == 'completed', result.get('errorCode')
                return result
            time.sleep(1)
        raise TimeoutError('qualification.timeout_no_replay')

    try:
        assert not api('/health')['workerActive']
        with urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=3) as response:
            queue = json.load(response)
        assert not queue['queue_running'] and not queue['queue_pending']
        if args.delivery_only:
            project = api('/api/projects/' + args.delivery_only)
            assert len(project['candidates']) == 2
            histories = [api('/api/candidates/' + candidate['candidateId'] + '/generations')['generations']
                         for candidate in project['candidates']]
            assert sorted(map(len, histories)) == [1, 2]
            original = [result for history in histories for result in history]
            assert sorted(result['status'] for result in original) == ['completed', 'completed', 'failed']
            references = [api('/api/generations/' + candidate['currentGeneration']['generationId'])
                          for candidate in project['candidates']]
            neutral = api('/api/clone-trials?projectId=' + args.delivery_only)['trials']
            assert len(neutral) == 4 and all(trial['delivery']['mode'] == 'none' for trial in neutral)
            assert all(trial['status'] in ('completed', 'failed') for trial in neutral)
            record['results'].extend(original + neutral)
            record['knownFailedTrials'] = [trial['trialId'] for trial in neutral if trial['status'] == 'failed']
        elif args.existing_pair:
            project = api('/api/projects/' + args.existing_pair)
            assert len(project['candidates']) == 2 and not api('/api/clone-trials?projectId=' + args.existing_pair)['trials']
            histories = [api('/api/candidates/' + candidate['candidateId'] + '/generations')['generations']
                         for candidate in project['candidates']]
            assert all(len(history) == 1 for history in histories)
            original = [history[0] for history in histories]
            assert sorted(result['status'] for result in original) == ['completed', 'failed']
            failed = next(result for result in original if result['status'] == 'failed')
            assert failed['errorCode'] == 'generation.failed', 'no unknown/interrupted replay'
            record['results'].extend(original)
            record['priorFailureRetained'] = failed['generationId']
            first = next(candidate for candidate in project['candidates'] if candidate['candidateId'] == failed['candidateId'])
        else:
            project = api('/api/projects', 'POST', {'name': '多引擎技术验收 · 2026-09-30'})
            pid = project['projectId']; record['projectId'] = pid; save()
            project = api(f'/api/projects/{pid}', 'PUT', {'expectedRevision': project['revision'],
                'name': project['name'], 'brief': '成熟低音，克制而坚韧。', 'auditionText': LINE})
            pair = api(f'/api/projects/{pid}/paired-generations', 'POST', {
                'expectedProjectRevision': project['revision'], 'directions': [DIRECTION], 'seed': 20260929})
            original = [wait('/api/generations/' + gid) for gid in pair['generationIds']]
            project = api(f'/api/projects/{pid}'); first = project['candidates'][0]
        pid = project['projectId']; record['projectId'] = pid; save()
        if not args.delivery_only:
            replacement = api(f'/api/candidates/{first["candidateId"]}/generations', 'POST', {
                'expectedProjectRevision': project['revision'], 'expectedCandidateRevision': first['revision'], 'seed': 41398272})
            new = wait('/api/generations/' + replacement['generationId'])
            previous_sibling = next(result for result in original if result['candidateId'] != first['candidateId'])
            sibling = api('/api/generations/' + previous_sibling['generationId'])
            assert sibling['sourceSha256'] == previous_sibling['sourceSha256']
            record['siblingUnchanged'] = True
            references = [new, sibling]
            neutral = []
            for reference in references:
                api(f'/api/projects/{pid}/selections', 'POST', {'generationId': reference['generationId']})
                for engine in ('qwen_base', 'index_base'):
                    trial = api('/api/clone-trials', 'POST', {'projectId': pid, 'generationId': reference['generationId'],
                        'engineId': engine, 'text': '你先去检查灯塔，我留在这里等消息。', 'seed': 20260929})
                    neutral.append(wait('/api/clone-trials/' + trial['trialId']))
        moss = next(reference for reference in references if reference['engineId'] == 'moss_design')
        api(f'/api/projects/{pid}/selections', 'POST', {'generationId': moss['generationId']})
        for delivery, words in (
            ({'mode': 'text', 'description': '坚定、果断、时间紧迫，迅速下达指令，不害怕、不惊慌。'}, '别打开那扇门，先把电源切断。'),
            ({'mode': 'manual', 'vector': [0, .25, 0, 0, 0, 0, 0, 0]}, '我已经提醒过你了，为什么还是没有检查？')):
            trial = api('/api/clone-trials', 'POST', {'projectId': pid, 'generationId': moss['generationId'],
                'engineId': 'index_base', 'text': words, 'seed': 20260929, 'delivery': delivery})
            result = wait('/api/clone-trials/' + trial['trialId'])
            assert result['executionDetails']['mode'] == delivery['mode']
        voice = api('/api/voices', 'POST', {'projectId': pid, 'generationId': moss['generationId']})
        record['publishedVoiceId'] = voice['voiceId']
        record['publishedHashes'] = {kind: hashlib.sha256(api(f'/api/voices/{voice["voiceId"]}/audio?kind={kind}', binary=True)).hexdigest()
                                     for kind in ('source', 'h3')}
        assert len(record['results']) == 9
        record['afterMemory'] = sample_memory()
        assert not record['afterMemory']['children']
        record['status'] = 'incomplete_known_failure' if record.get('knownFailedTrials') else (
            'passed_with_known_failure' if args.existing_pair else 'passed')
        save()
        print(json.dumps({'status': record['status'], 'projectId': pid, 'voiceId': voice['voiceId'], 'calls': 9}), flush=True)
    except Exception as error:
        record['status'] = 'failed'; record['failure'] = str(error); save(); raise


if __name__ == '__main__': main()
