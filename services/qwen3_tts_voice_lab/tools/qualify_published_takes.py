"""Exactly two published-voice Index takes and one serial Ref2VA job, no replay."""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path

from compare_h3_references import FIELDS, NoRedirect, save
from memory_trace import MemoryTrace
from qualification_receipts import claim_receipt
from verify_published_h3 import GATEWAY, IMAGE, IMAGE_HASH, multipart

VOICE = 'voice_5689e99835494d2f8024485523c4dbf6'  # Technical publication, not original MOSS D.
LAB = 'http://100.64.35.71:8897'
GATEWAY_DB = Path('/home/wjmao/services/plotloom-h3-gateway/data/gateway.sqlite3')
LAB_DB = Path('/home/wjmao/services/plotloom-voice-lab/data/voice_lab.sqlite3')
TEXT = '等等，别打开那扇门！控制台还在报警，先把电源切断！'
DELIVERY = {'mode': 'text', 'description': '情况紧迫，果断地制止对方。语气坚定，立即行动，不恐慌、不害怕。'}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def lane_entries(ids):
    with sqlite3.connect(GATEWAY_DB) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute('SELECT sequence,owner,job_kind,job_id,state,grant_id,error_code FROM generation_lane ORDER BY sequence') if row['job_id'] in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    record = {'status': 'preflight', 'callCap': {'index': 2, 'h3': 1}, 'calls': {'index': 0, 'h3': 0},
              'voiceId': VOICE, 'takes': [], 'timeline': []}
    save(args.receipt, record)
    config = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    key = next(v.split('=', 1)[1] for v in config['Config']['Env'] if v.startswith('H3_API_KEY='))
    opener = urllib.request.build_opener(NoRedirect())

    def request(path, body=None, *, lab=False, binary=False, content_type='application/json'):
        headers = {} if lab else {'Authorization': 'Bearer ' + key}
        if body is not None:
            headers['Content-Type'] = content_type
        with opener.open(urllib.request.Request((LAB if lab else GATEWAY) + path,
                         data=body, headers=headers), timeout=10) as response:
            return response.read() if binary else json.load(response)

    def checkpoint(phase, ids):
        record['timeline'].append({'phase': phase, 'monotonic': time.monotonic(), 'lane': lane_entries(ids)})
        save(args.receipt, record)

    def create_take(seed):
        record['calls']['index'] += 1
        record['status'] = 'dispatch_intent_no_replay'
        save(args.receipt, record)
        take = request('/v1/voice-takes', json.dumps({'voiceId': VOICE, 'text': TEXT,
                       'engineId': 'index_base', 'seed': seed, 'delivery': DELIVERY}, ensure_ascii=False).encode())
        record['takes'].append(take)
        save(args.receipt, record)
        return take['takeId']

    def await_take(take_id):
        deadline = time.monotonic() + 2400
        previous = None
        while time.monotonic() < deadline:
            value = request('/v1/voice-takes/' + take_id)
            if value['status'] != previous:
                print(take_id, value['status'], flush=True)
                previous = value['status']
            if value.get('dispatchErrorCode'):
                raise ValueError(value['dispatchErrorCode'])
            if value['status'] not in {'queued', 'running'}:
                assert value['status'] == 'completed' and value['h3Eligible'], 'take.failed_or_ineligible'
                return value
            time.sleep(2)
        raise TimeoutError('take.observation_timeout_no_replay')

    trace = MemoryTrace(args.receipt.with_suffix('.memory.jsonl'))
    try:
        health = request('/health')
        assert health['status'] == 'ok' and not health['queuedJobs'] and not health['activeDispatches'], 'gateway.busy'
        assert not request('/health', lab=True)['workerActive'], 'lab.busy'
        queue = json.load(urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=5))
        assert not queue['queue_running'] and not queue['queue_pending'], 'comfy.busy'
        identity = request('/api/voices/' + VOICE, lab=True)
        record['identityBefore'] = identity
        assert sha(IMAGE.read_bytes()) == IMAGE_HASH
        with trace:
            trace.mark(phase='first_take', case='published_technical_moss')
            first_id = create_take(20260929)
            first = await_take(first_id)
            # Explicit process release, not merely a completed audio record.
            for _ in range(50):
                if request('/health')['activeDispatches'] == 0:
                    break
                time.sleep(.2)
            else:
                raise ValueError('lane.first_take_not_released')
            with sqlite3.connect(LAB_DB) as db:
                assert db.execute('SELECT release_confirmed FROM execution_grants WHERE job_id=?', (first_id,)).fetchone() == (1,)
            source = request(f'/v1/voice-takes/{first_id}/audio?kind=source', binary=True)
            reference = request(f'/v1/voice-takes/{first_id}/audio?kind=h3', binary=True)
            assert sha(source) == first['sourceSha256'] and sha(reference) == first['h3Sha256']
            record['firstResult'] = first
            body, boundary = multipart(FIELDS, IMAGE.read_bytes(), reference)
            record['calls']['h3'] += 1
            save(args.receipt, record)
            video = request('/v1/video-jobs/from-image-with-voice', body, content_type='multipart/form-data; boundary=' + boundary)
            record['videoAccepted'] = video
            save(args.receipt, record)
            assert video['voiceReferenceSha256'] == first['h3Sha256']
            second_id = create_take(20260930)
            ids = [first_id, video['id'], second_id]
            for _ in range(50):
                if len(lane_entries(ids)) == 3:
                    break
                time.sleep(.2)
            ordered = lane_entries(ids)
            assert [entry['job_id'] for entry in ordered] == ids, 'lane.registration_order'
            checkpoint('all_admitted', ids)
            deadline, previous = time.monotonic() + 2400, None
            while time.monotonic() < deadline:
                result = request('/v1/video-jobs/' + video['id'])
                trace.mark(phase=result['status'], jobId=video['id'])
                if result['status'] != previous:
                    checkpoint('video_' + result['status'], ids)
                    print('H3', result['status'], flush=True)
                    previous = result['status']
                if result['status'] not in {'queued', 'running'}:
                    break
                time.sleep(3)
            assert result['status'] == 'succeeded' and result['outputReady'], 'video.failed_or_unknown'
            record['videoResult'] = result
            second = await_take(second_id)
            record['secondResult'] = second
            for kind in ('source', 'h3'):
                content = request(f'/v1/voice-takes/{second_id}/audio?kind={kind}', binary=True)
                assert sha(content) == second[kind + 'Sha256']
            assert sha(request(f'/v1/voice-takes/{first_id}/audio?kind=source', binary=True)) == first['sourceSha256']
            assert request('/api/voices/' + VOICE, lab=True) == identity
            content = request('/v1/video-jobs/' + video['id'] + '/output', binary=True)
            output = args.receipt.with_suffix('.mp4')
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as file:
                file.write(content)
            info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                'format=duration:stream=codec_name,codec_type,width,height,nb_frames,sample_rate', '-of', 'json', str(output)]))
            visual = next(s for s in info['streams'] if s['codec_type'] == 'video')
            audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
            assert (visual['width'], visual['height'], visual['nb_frames']) == (576, 1024, '192')
            assert audio['codec_name'] == 'aac' and audio['sample_rate'] == '32000'
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-map', '0:v', '-map', '0:a', '-f', 'null', '-'], check=True)
            record.update(status='passed', media=info, outputSha256=sha(content), firstTakeUnchanged=True)
            checkpoint('completed', ids)
    except Exception as error:
        record.update(status='failed_or_uncertain_no_replay', failure=str(error))
        raise
    finally:
        record['memorySummary'] = trace.summary
        save(args.receipt, record)
        print('Receipt', args.receipt, record['status'], record['calls'], flush=True)


if __name__ == '__main__':
    main()
