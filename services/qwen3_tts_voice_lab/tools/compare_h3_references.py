"""Exactly two serial Ref2VA jobs; frozen original MOSS D versus accepted Index take."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from memory_trace import MemoryTrace
from qualification_receipts import claim_receipt
from verify_published_h3 import GATEWAY, IMAGE, IMAGE_HASH, multipart
from verify_resident_reuse import idle

ROOT = Path('/home/wjmao/services')
CASES = (
    ('identity_audition', ROOT / 'moss-voicegenerator-trial/experiments/2026-09-28-qwen-comparison-float/moss_d.wav',
     'da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae'),
    ('line_performance', ROOT / 'index-chinese-emotion-trial/2026-09-29/moss_d_index_chinese_direction_seed-20260930.wav',
     '80ba844e1294cbf0d9587327d98a730891cd0558fc5ffaee153a70e6f8cb8bfb'),
)
PROMPT = (
    '<Picture 1> is the exact first frame. <Audio 1> is the woman\'s voice reference. '
    'One continuous cinematic portrait shot of the same Chinese female lighthouse '
    'keeper in dark workwear in the lantern room. Preserve her face and clothing. '
    'Locked camera, natural small gestures, keep her face and mouth visible. '
    'She speaks once in Mandarin, firmly and decisively because time is running '
    'out, without fear or panic: <d>[Chinese] 等等，别打开那扇门！控制台还在报警，'
    '先把电源切断！</d> Begin speaking promptly and complete the line, then remain '
    'silent. Quiet rain and natural synchronized sound. No other voices, '
    'no repeated words, no subtitles or typography.'
)
FIELDS = {'prompt': PROMPT, 'resolution': '576x1024', 'aspectPolicy': 'reject_mismatch',
          'durationSeconds': '8', 'seed': '20260923'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # No changed route, credential forwarding or implicit replay.


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, record):
    temporary = path.with_suffix('.tmp')
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
        file.write('\n')
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prepare(source, output):
    # Identical CPU-only preparation for both references; preserve original bytes.
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(source), '-ar', '32000',
                    '-ac', '1', '-c:a', 'pcm_s16le', str(output)], check=True)
    output.chmod(0o600)
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,sample_rate,channels', '-of', 'json', str(output)], text=True))
    assert info['streams'][0] == {'codec_name': 'pcm_s16le', 'sample_rate': '32000', 'channels': 1}
    assert 1 <= float(info['format']['duration']) <= 10 and output.stat().st_size <= 2 * 1024**2
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    claim_receipt(args.receipt)
    record = {'status': 'preflight', 'generationCallCap': 2, 'generationCalls': 0,
              'fields': FIELDS, 'imageSha256': IMAGE_HASH, 'cases': [], 'beforeHealth': idle()}
    assert digest(IMAGE) == IMAGE_HASH, 'comparison.image_changed'
    for label, source, expected in CASES:
        assert digest(source) == expected, 'comparison.source_changed'
        prepared = args.receipt.parent / (label + '.wav')
        info = prepare(source, prepared)
        record['cases'].append({'case': label, 'sourceSha256': expected,
                               'referenceSha256': digest(prepared), 'referenceInfo': info})
    config = json.loads(subprocess.check_output(['docker', 'inspect', 'plotloom-h3-gateway']))[0]
    key = next(value.split('=', 1)[1] for value in config['Config']['Env'] if value.startswith('H3_API_KEY='))
    opener = urllib.request.build_opener(NoRedirect())

    def gateway(path, data=None, content_type=None, binary=False):
        headers = {'Authorization': 'Bearer ' + key}
        if content_type:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(GATEWAY + path, data=data, headers=headers)
        with opener.open(request, timeout=30) as response:
            return response.read() if binary else json.load(response)

    trace_path = args.receipt.with_suffix('.memory.jsonl')
    save(args.receipt, record)
    trace = MemoryTrace(trace_path)
    try:
        with trace:
            for case in record['cases']:
                idle()
                trace.mark(case=case['case'], phase='dispatch_intent', jobId=None)
                body, boundary = multipart(FIELDS, IMAGE.read_bytes(),
                    (args.receipt.parent / (case['case'] + '.wav')).read_bytes())
                # Freeze intent durably before POST; any uncertainty ends this run.
                record['generationCalls'] += 1
                record['status'] = 'dispatch_started_no_replay'
                case['dispatchIntent'] = True
                save(args.receipt, record)
                accepted = gateway('/v1/video-jobs/from-image-with-voice', body,
                                   'multipart/form-data; boundary=' + boundary)
                case['accepted'] = accepted
                save(args.receipt, record)
                assert accepted['voiceReferenceSha256'] == case['referenceSha256']
                path = '/v1/video-jobs/' + accepted['id']
                print('Accepted', case['case'], accepted['id'], flush=True)
                deadline, previous = time.monotonic() + 2400, None
                while time.monotonic() < deadline:
                    trace.check()
                    result = gateway(path)
                    trace.mark(jobId=accepted['id'], phase=result['status'])
                    if result['status'] != previous:
                        print(case['case'], result['status'], flush=True)
                        previous = result['status']
                    case['result'] = result
                    save(args.receipt, record)
                    if result['status'] not in ('queued', 'running'):
                        break
                    time.sleep(5)
                else:
                    raise TimeoutError('comparison.poll_timeout_no_replay')
                assert result['status'] == 'succeeded' and result['outputReady'], 'comparison.job_failed'
                trace.mark(phase='output_transfer')
                output = args.receipt.parent / (case['case'] + '.mp4')
                with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as file:
                    file.write(gateway(path + '/output', binary=True))
                info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                    'format=duration:stream=codec_name,codec_type,width,height,nb_frames,sample_rate',
                    '-of', 'json', str(output)], text=True))
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-map', '0:v',
                                '-map', '0:a', '-f', 'null', '-'], check=True)
                video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
                audio = next(stream for stream in info['streams'] if stream['codec_type'] == 'audio')
                assert (video['width'], video['height'], video['nb_frames']) == (576, 1024, '192')
                assert audio['codec_name'] == 'aac' and audio['sample_rate'] == '32000'
                case.update(outputSha256=digest(output), media=info, fullDecode='passed')
                save(args.receipt, record)
            record.update(status='completed_pending_listening', finalHealth=idle())
            trace.mark(phase='completed', jobId=None, case=None)
    except Exception:
        record['status'] = 'failed_or_uncertain_no_replay'
        raise
    finally:
        record['memorySummary'] = trace.summary
        if trace_path.exists():
            record['memoryTraceSha256'] = digest(trace_path)
        save(args.receipt, record)
    print('Pair completed; no further tuning:', args.receipt, flush=True)


if __name__ == '__main__':
    main()
