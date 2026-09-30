"""One gateway Ref2VA job using exact published audio; no Voice ID resolver added."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

from qualification_receipts import claim_receipt
from qualify_workflow import api, sample_memory

GATEWAY = 'http://100.64.35.71:8090'
IMAGE = Path('/home/wjmao/services/spark-comfyui/data/input/experiments/h3-ref2va-portrait-2026-09-26/2026-09-26_c01-portrait-576x1024.png')
IMAGE_HASH = '4237ad89a723b7f059d3238eb3aca92acc6373d726b07b7161ef7e37af932d10'
PROMPT = (
    '<Picture 1> is the exact first frame. <Audio 1> is the woman\'s voice-timbre '
    'reference, not target dialogue or a soundtrack. One continuous cinematic '
    'portrait shot of the Chinese female lighthouse keeper in the same dark '
    'workwear and lantern room. Keep her face and mouth visible; locked camera. '
    'She raises the brass fuse only slightly without covering her mouth, speaks '
    'once in Mandarin in the first second, then remains silent: '
    '<d>[Chinese] 一枚，只够一边。</d> Natural synchronized sound, quiet rain. '
    'No other voices, no repeated words, no subtitles or typography.'
)


def multipart(fields: dict, image: bytes, voice: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    for key, name, kind, content in [('image', 'first.png', 'image/png', image),
                                      ('voiceAudio', 'reference.wav', 'audio/wav', voice)]:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{name}"\r\nContent-Type: {kind}\r\n\r\n'.encode()
                     + content + b'\r\n')
    return b''.join(parts) + f'--{boundary}--\r\n'.encode(), boundary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-receipt', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--resume-observation', action='store_true',
                        help='Observe the recorded accepted job only; never dispatch again.')
    args = parser.parse_args()
    if not args.resume_observation:
        claim_receipt(args.receipt)
    retained = json.loads(args.receipt.read_text()) if args.resume_observation else None
    if retained is not None:
        assert retained['generationCalls'] == 1 and retained.get('accepted', {}).get('id'), 'probe.no_accepted_job'
    workflow = json.loads(args.workflow_receipt.read_text())
    assert workflow['status'] == 'passed', 'workflow.incomplete'
    assert not api('/health')['workerActive'] and not sample_memory()['children'], 'lab.busy'
    voice_id = workflow['publishedVoiceId']
    metadata = api('/api/voices/' + voice_id)
    voice = api('/api/voices/' + voice_id + '/audio?kind=h3', binary=True)
    voice_hash = hashlib.sha256(voice).hexdigest()
    assert voice_hash == metadata['h3Sha256'] == workflow['publishedHashes']['h3']
    image = IMAGE.read_bytes()
    assert hashlib.sha256(image).hexdigest() == IMAGE_HASH
    assert image[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', image[16:24]) == (576, 1024)
    # Read only the installed gateway's secret in memory. Never write or print
    # its environment, auth header, or response bodies to the public receipt.
    config = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    key = next(value.split('=', 1)[1] for value in config['Config']['Env'] if value.startswith('H3_API_KEY='))

    def gateway(path: str, data=None, content_type=None, binary=False):
        headers = {'Authorization': 'Bearer ' + key}
        if content_type:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(GATEWAY + path, data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read() if binary else json.load(response)

    health = gateway('/health')
    assert health['status'] == 'ok', 'gateway.not_ready'
    if retained is None:
        assert not health['queuedJobs'] and not health['activeDispatches'], 'gateway.busy'
        with urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=5) as response:
            queue = json.load(response)
        assert not queue['queue_running'] and not queue['queue_pending'], 'comfy.busy'
    record = retained or {'status': 'preflight', 'generationCallCap': 1, 'generationCalls': 0,
              'voiceId': voice_id, 'voiceReferenceSha256': voice_hash, 'imageSha256': IMAGE_HASH,
              'beforeMemory': sample_memory()}
    assert record['voiceId'] == voice_id and record['voiceReferenceSha256'] == voice_hash
    assert record['imageSha256'] == IMAGE_HASH
    args.receipt.parent.mkdir(parents=True, exist_ok=True)

    def save():
        temporary = args.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.chmod(0o600)
        temporary.replace(args.receipt)

    fields = {'prompt': PROMPT, 'resolution': '576x1024', 'aspectPolicy': 'reject_mismatch',
              'durationSeconds': '5', 'seed': '20260923'}
    body, boundary = multipart(fields, image, voice)
    save()
    try:
        if retained is None:
            record.update(status='dispatch_started_no_replay', generationCalls=1)
            save()
            accepted = gateway('/v1/video-jobs/from-image-with-voice', body, 'multipart/form-data; boundary=' + boundary)
        else:
            accepted = record['accepted']
        assert accepted['voiceReferenceSha256'] == voice_hash, 'gateway.reference_changed'
        record['accepted'] = accepted
        save()
        job_path = '/v1/video-jobs/' + accepted['id']
        print('Accepted sole Ref2VA job:', accepted['id'], flush=True)
        deadline, previous = time.monotonic() + 1800, None
        while time.monotonic() < deadline:
            result = gateway(job_path)
            if result['status'] != previous:
                print('Gateway phase:', result['status'], flush=True)
                previous = result['status']
            record['result'] = result
            save()
            if result['status'] in ('succeeded', 'failed', 'outcome_unknown', 'interrupted', 'cancelled', 'expired'):
                break
            time.sleep(5)
        else:
            raise TimeoutError('probe.poll_timeout_no_replay')
        assert result['status'] == 'succeeded' and result['outputReady'], result.get('error')
        output = args.receipt.with_suffix('.mp4')
        output.write_bytes(gateway(job_path + '/output', binary=True))
        output.chmod(0o600)
        media = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
            'format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,nb_frames,sample_rate',
            '-of', 'json', str(output)], text=True))
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-map', '0:v', '-map', '0:a', '-f', 'null', '-'], check=True)
        video = next(s for s in media['streams'] if s['codec_type'] == 'video')
        audio = next(s for s in media['streams'] if s['codec_type'] == 'audio')
        assert (video['width'], video['height'], video['nb_frames']) == (576, 1024, '124')
        assert audio['codec_name'] == 'aac' and audio['sample_rate'] == '32000'
        record.update(status='completed', media=media, fullStreamDecode='passed',
                      outputSha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except Exception as error:
        record.update(status='failed_or_uncertain_no_replay', failure=str(error))
        raise
    finally:
        record['afterMemory'] = sample_memory()
        record['finalHealth'] = gateway('/health')
        save()
        print('H3 receipt:', args.receipt, 'status:', record['status'], flush=True)


if __name__ == '__main__':
    main()
