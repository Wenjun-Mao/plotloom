"""GET-only completion proof for three already-accepted jobs; cannot resubmit."""

import argparse
import json
import os
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path

from qualify_published_takes import ACTIVE_VIDEO_STATES, GATEWAY, LAB_DB, VOICE, lane_entries, sha
from compare_h3_references import NoRedirect, save
from memory_trace import MemoryTrace
from qualification_receipts import claim_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-receipt', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    source = json.loads(args.source_receipt.read_text())
    assert source['calls'] == {'index': 2, 'h3': 1} and len(source['takes']) == 2
    first_id, second_id = (take['takeId'] for take in source['takes'])
    video_id = source['videoAccepted']['id']
    assert first_id == source['firstResult']['takeId'] and source['voiceId'] == VOICE
    ids = [first_id, video_id, second_id]
    assert [entry['job_id'] for entry in lane_entries(ids)] == ids
    config = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    key = next(value.split('=', 1)[1] for value in config['Config']['Env'] if value.startswith('H3_API_KEY='))
    opener = urllib.request.build_opener(NoRedirect())

    def get(path, binary=False):
        # GET is the only network operation in this observer. A lost reply
        # cannot cause another synthesis or Comfy workflow submission.
        request = urllib.request.Request(GATEWAY + path, headers={'Authorization': 'Bearer ' + key}, method='GET')
        with opener.open(request, timeout=15) as response:
            return response.read() if binary else json.load(response)

    record = {'status': 'observing_accepted_only', 'generationCalls': 0,
              'sourceReceiptSha256': sha(args.source_receipt.read_bytes()),
              'originalObserverFailure': source.get('failure'), 'voiceId': VOICE,
              'originalCalls': source['calls'], 'timeline': []}
    save(args.receipt, record)
    trace = MemoryTrace(args.receipt.with_suffix('.memory.jsonl'))
    try:
        with trace:
            deadline, previous = time.monotonic() + 2400, None
            while time.monotonic() < deadline:
                video = get('/v1/video-jobs/' + video_id)
                second = get('/v1/voice-takes/' + second_id)
                phase = (video['status'], second['status'])
                trace.mark(phase=video['status'], jobId=video_id)
                if phase != previous:
                    record['timeline'].append({'phase': phase, 'lane': lane_entries(ids)})
                    save(args.receipt, record); print('Observed', *phase, flush=True)
                    previous = phase
                assert not second.get('dispatchErrorCode'), 'take.dispatch_unresolved'
                if video['status'] not in ACTIVE_VIDEO_STATES:
                    assert video['status'] == 'succeeded' and video['outputReady'], 'video.failed_or_unknown'
                    if second['status'] not in {'queued', 'running'}:
                        assert second['status'] == 'completed' and second['h3Eligible'], 'take.failed_or_ineligible'
                        if all(entry['state'] == 'done' for entry in lane_entries(ids)):
                            break
                time.sleep(3)
            else:
                raise TimeoutError('accepted_jobs.observation_timeout_no_replay')
            first = get('/v1/voice-takes/' + first_id)
            assert first['sourceSha256'] == source['firstResult']['sourceSha256']
            assert first['h3Sha256'] == source['firstResult']['h3Sha256'] == video['voiceReferenceSha256']
            for take in (first, second):
                for kind in ('source', 'h3'):
                    assert sha(get(f'/v1/voice-takes/{take["takeId"]}/audio?kind={kind}', True)) == take[kind + 'Sha256']
            with urllib.request.urlopen('http://100.64.35.71:8897/api/voices/' + VOICE, timeout=10) as response:
                assert json.load(response) == source['identityBefore']
            with sqlite3.connect(LAB_DB) as db:
                grants = db.execute('SELECT job_id,release_confirmed FROM execution_grants ORDER BY rowid').fetchall()
                assert grants == [(first_id, 1), (second_id, 1)]
            content = get('/v1/video-jobs/' + video_id + '/output', True)
            output = args.receipt.with_suffix('.mp4')
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as file: file.write(content)
            media = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                'format=duration:stream=codec_name,codec_type,width,height,nb_frames,sample_rate', '-of', 'json', str(output)]))
            visual = next(s for s in media['streams'] if s['codec_type'] == 'video')
            audio = next(s for s in media['streams'] if s['codec_type'] == 'audio')
            assert (visual['width'], visual['height'], visual['nb_frames']) == (576, 1024, '192')
            assert audio['codec_name'] == 'aac' and audio['sample_rate'] == '32000'
            assert 7.8 <= float(media['format']['duration']) <= 8.3
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-map', '0:v', '-map', '0:a', '-f', 'null', '-'], check=True)
            record.update(status='passed', firstResult=first, secondResult=second, videoResult=video,
                          lane=lane_entries(ids), media=media, outputSha256=sha(content), firstTakeUnchanged=True)
    except Exception as error:
        record.update(status='failed_or_uncertain_no_replay', failure=str(error))
        raise
    finally:
        record['memorySummary'] = trace.summary
        save(args.receipt, record)
        print('Observation receipt', args.receipt, record['status'], 'new generation calls: 0', flush=True)


if __name__ == '__main__': main()
