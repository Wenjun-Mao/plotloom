import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from common import digest, sha, write
from prepare_review import detail, prepare, sheet
from review_results import SKILL_VERSION, batch, validate


def test_skill_version_matches_validator_and_result_contract():
    skill_dir = SCRIPTS.parent
    frontmatter = (skill_dir / 'SKILL.md').read_text().split('---', 2)[1]
    version = yaml.safe_load(frontmatter)['metadata']['version']
    contract = (skill_dir / 'references' / 'contracts.md').read_text()
    result_section = contract.split('## Primary review result', 1)[1]
    example = json.loads(result_section.split('```json', 1)[1].split('```', 1)[0])
    assert version == SKILL_VERSION == example['skillVersion']


@pytest.fixture
def case(tmp_path):
    video = tmp_path/'clip.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=64x48:rate=4:duration=2', '-pix_fmt', 'yuv420p', str(video)], check=True)
    ref = tmp_path/'ref.txt'; ref.write_text('reference')
    data = {'schemaVersion': 1, 'caseId': 'sample', 'video': video.name, 'worldState': 'Room remains empty offscreen.',
            'requirements': {'speech': False, 'perceptualAudio': False},
            'shots': [{'id': 'a', 'startSeconds': 0, 'endSeconds': 2, 'expected': 'Moving test pattern', 'references': [ref.name], 'dialogue': []}]}
    path = tmp_path/'case.json'; write(path, data)
    return path, video, ref, data


def review(bundle, path, decision='pass'):
    b = json.loads((bundle/'bundle.json').read_text())
    r = {'schemaVersion': 1, 'caseId': b['caseId'], 'bundleFingerprint': b['fingerprint'], 'skillVersion': '0.1.3',
         'reviewer': {'model': 'test', 'reasoning': 'high'}, 'decision': decision, 'summary': 'Reviewed.',
         'findings': ([{'category': 'action', 'severity': 'material', 'claim': 'Wrong action', 'startSeconds': 0, 'endSeconds': 1, 'evidenceIds': ['anchor:0']}] if decision == 'fail' else []), 'evidenceViewed': ['overview', 'anchor:0', 'reference:a:1'],
         'speech': {'status': 'not_required', 'notes': ''}, 'limitations': ['sampled']}
    write(path, r); return r


def test_bad_inputs_do_not_create_output(case, tmp_path):
    path, video, ref, c = case
    c['shots'][0]['endSeconds'] = 3; write(path, c)
    with pytest.raises(ValueError): prepare(path, tmp_path/'out')
    assert not (tmp_path/'out').exists()
    c['shots'][0]['endSeconds'] = 2; c['asr'] = {'file': 'missing', 'sha256': 'bad'}; write(path, c)
    with pytest.raises(ValueError): prepare(path, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_cache_content_invalidation_and_corruption(case, tmp_path):
    path, video, ref, c = case
    first, hit = prepare(path, tmp_path/'out'); assert not hit
    assert prepare(path, tmp_path/'out') == (first, True)
    ref.write_text('different'); second, hit = prepare(path, tmp_path/'out'); assert second != first and not hit
    asr = tmp_path/'asr.json'; write(asr, {'sourceSha256': sha(video), 'segments': []})
    c['asr'] = {'file': asr.name, 'sha256': sha(asr)}; write(path, c)
    third, _ = prepare(path, tmp_path/'out'); assert third != second
    write(asr, {'sourceSha256': sha(video), 'segments': [{'startSeconds': 0, 'endSeconds': 1, 'text': 'hello'}]})
    c['asr']['sha256'] = sha(asr); write(path, c)
    fourth, _ = prepare(path, tmp_path/'out'); assert fourth != third
    b = json.loads((fourth/'bundle.json').read_text()); (fourth/b['evidence'][0]['file']).write_text('corrupt')
    with pytest.raises(ValueError, match='corrupt'): prepare(path, tmp_path/'out')


def test_review_validation_and_detail(case, tmp_path):
    path, video, _, _ = case; bundle, _ = prepare(path, tmp_path/'out')
    review_path = tmp_path/'review.json'; r = review(bundle, review_path)
    validate(review_path, bundle)
    r['evidenceViewed'] = ['foreign']; write(review_path, r)
    with pytest.raises(ValueError): validate(review_path, bundle)
    r['evidenceViewed'] = ['anchor:0']; r['findings'] = [{'category': 'action', 'severity': 'material', 'claim': 'wrong', 'startSeconds': 0, 'endSeconds': 1, 'evidenceIds': ['anchor:0']}]; write(review_path, r)
    with pytest.raises(ValueError): validate(review_path, bundle)
    with pytest.raises(ValueError): detail(bundle, video, 8, tmp_path/'detail')
    assert not (tmp_path/'detail').exists()
    d = detail(bundle, video, 2, tmp_path/'detail'); r['decision'] = 'fail'; r['evidenceViewed'] = ['detail:2']; r['findings'][0]['evidenceIds'] = ['detail:2']; write(review_path, r)
    validate(review_path, bundle, [d])
    (d/'frame.png').write_bytes(b'bad')
    with pytest.raises(ValueError): validate(review_path, bundle, [d])


def test_required_speech_and_deterministic_audit(case, tmp_path):
    path, video, _, c = case; bundle, _ = prepare(path, tmp_path/'out')
    rows = []
    for i, decision in enumerate(['pass', 'fail', 'needs_review']):
        rp = tmp_path/f'r{i}.json'; review(bundle, rp, decision); rows.append({'review': str(rp), 'bundle': str(bundle)})
    manifest = tmp_path/'batch.json'; write(manifest, rows)
    a = batch(manifest, 'seed', 1); assert a == batch(manifest, 'seed', 1)
    assert {x['decision'] for x in a['selectedForAudit']} == {'pass', 'fail', 'needs_review'}
    assert a['auditStatus'] == 'selection_only'
    c['requirements']['speech'] = True; write(path, c); sb, _ = prepare(path, tmp_path/'out')
    rp = tmp_path/'speech.json'; r = review(sb, rp); r['speech']['status'] = 'uncertain'; write(rp, r)
    with pytest.raises(ValueError, match='needs_review'): validate(rp, sb)


def test_pinned_reuse_and_source_invalidation(case, tmp_path):
    path, video, _, c = case
    receipt = tmp_path/'receipt.json'
    write(receipt, {'status': 'PASS', 'outputSha256': sha(video), 'ffmpegDecodeExitCode': 0})
    c['technicalReceipt'] = {'file': receipt.name, 'sha256': sha(receipt)}
    write(path, c)
    b, _ = prepare(path, tmp_path/'out')
    assert json.loads((b/'bundle.json').read_text())['technical']['decode'] == 'reused_pinned_receipt'
    # A changed source must not use a receipt bound to the old bytes.
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-c', 'copy', '-metadata', 'comment=changed', str(tmp_path/'changed.mp4')], check=True)
    c['video'] = 'changed.mp4'; write(path, c)
    with pytest.raises(ValueError, match='receipt'): prepare(path, tmp_path/'other')
    assert not (tmp_path/'other').exists()
    del c['technicalReceipt']; write(path, c)
    changed, _ = prepare(path, tmp_path/'out'); assert changed != b
    with pytest.raises(ValueError, match='original source changed'): detail(b, tmp_path/'changed.mp4', 0, tmp_path/'details')


def test_inspection_pinning(case, tmp_path):
    path, video, _, c = case
    # Use actual decoded source frames as a small externally retained inspection.
    from common import extract
    image = tmp_path/'inspection.png'; extract(video, 0, image)
    desc = tmp_path/'inspection.json'
    write(desc, {'sourceSha256': sha(video), 'overview': image.name,
                 'pages': [{'file': image.name, 'frameIndices': [0, 3, 7]}]})
    c['inspection'] = {'file': desc.name, 'sha256': sha(desc)}; write(path, c)
    b, _ = prepare(path, tmp_path/'out')
    assert any(x['kind'] == 'uniform_inspection' for x in json.loads((b/'bundle.json').read_text())['evidence'])
    image.write_bytes(b'modified image bytes')
    changed, _ = prepare(path, tmp_path/'out'); assert changed != b
    c['inspection']['sha256'] = '0' * 64; write(path, c)
    with pytest.raises(ValueError, match='hash mismatch'): prepare(path, tmp_path/'unused')
    assert not (tmp_path/'unused').exists()


def test_asr_missing_model_fails_before_output(case, tmp_path):
    from blind_asr import recognize
    _, video, _, _ = case
    output = tmp_path/'recognition.json'
    with pytest.raises(ValueError, match='model directory'):
        recognize(video, sys.executable, tmp_path/'missing', output)
    assert not output.exists()


def test_mechanical_cache_excludes_skill_text_but_pins_extraction_code(case, tmp_path, monkeypatch):
    import shutil
    import prepare_review as module
    import common
    path, _, _, _ = case
    fake = tmp_path/'skill'; scripts = fake/'scripts'; scripts.mkdir(parents=True)
    for name in ('common.py', 'prepare_review.py'):
        shutil.copyfile(SCRIPTS/name, scripts/name)
    (fake/'SKILL.md').write_text('initial review rule')
    monkeypatch.setattr(common, '__file__', str(scripts/'common.py'))
    first, _ = module.prepare(path, tmp_path/'cache')
    (fake/'SKILL.md').write_text('changed review rule')
    assert module.prepare(path, tmp_path/'cache') == (first, True)
    with (scripts/'common.py').open('a') as f: f.write('\n# changed extraction code\n')
    changed, hit = module.prepare(path, tmp_path/'cache')
    assert changed != first and not hit


@pytest.mark.parametrize('field,value', [('requirements', {'speech': False, 'perceptualAudio': False}),
                                         ('technical', {'status': 'FAIL'}),
                                         ('caseSnapshotSha256', '0'*64),
                                         ('video', {'durationSeconds': 999}),
                                         ('caseId', 'other')])
def test_bundle_metadata_is_bound(case, tmp_path, field, value):
    path, _, _, c = case
    if field == 'requirements':
        c['requirements']['speech'] = True; write(path, c)
    bundle, _ = prepare(path, tmp_path/'out')
    rp = tmp_path/'review.json'; review(bundle, rp, 'needs_review')
    b = json.loads((bundle/'bundle.json').read_text()); b[field] = value; write(bundle/'bundle.json', b)
    with pytest.raises(ValueError, match='fingerprint'): validate(rp, bundle)


def test_evidence_metadata_tamper_and_original_changes(case, tmp_path):
    path, video, ref, c = case
    asr = tmp_path/'asr.json'; write(asr, {'sourceSha256': sha(video), 'segments': []})
    c['asr'] = {'file': asr.name, 'sha256': sha(asr)}; write(path, c)
    bundle, _ = prepare(path, tmp_path/'out'); rp = tmp_path/'review.json'; review(bundle, rp)
    bpath = bundle/'bundle.json'; original = bpath.read_text(); b = json.loads(original)
    b['evidence'][0]['id'] = 'other'; write(bpath, b)
    with pytest.raises(ValueError, match='fingerprint'): validate(rp, bundle)
    bpath.write_text(original)
    for source in (path, video, ref, asr):
        old = source.read_bytes(); source.write_bytes(old + b'changed')
        with pytest.raises(ValueError, match='original source changed'): validate(rp, bundle)
        source.write_bytes(old)
    validate(rp, bundle)


def test_detail_frame_timestamp_cannot_be_relabelled(case, tmp_path):
    path, video, _, _ = case; bundle, _ = prepare(path, tmp_path/'out')
    d = detail(bundle, video, 2, tmp_path/'detail')
    rp = tmp_path/'r.json'; r = review(bundle, rp, 'fail')
    r['evidenceViewed'] = ['detail:2']; r['findings'][0]['evidenceIds'] = ['detail:2']; write(rp, r)
    validate(rp, bundle, [d])
    rec = json.loads((d/'detail.json').read_text()); rec['timeSeconds'] = 1.5; write(d/'detail.json', rec)
    with pytest.raises(ValueError, match='native frame timestamp'): validate(rp, bundle, [d])


def test_pass_requires_shot_coverage_and_all_references(case, tmp_path):
    path, _, _, c = case
    first = c['shots'][0]; second = copy.deepcopy(first)
    first['endSeconds'] = 1; second.update(id='b', startSeconds=1, endSeconds=2)
    c['shots'] = [first, second]; write(path, c)
    bundle, _ = prepare(path, tmp_path/'out'); rp = tmp_path/'r.json'; r = review(bundle, rp)
    with pytest.raises(ValueError, match='references'): validate(rp, bundle)
    r['evidenceViewed'].append('reference:b:1'); write(rp, r)
    # overview includes both shots; remove it to exercise one-shot evidence only.
    r['evidenceViewed'].remove('overview'); write(rp, r)
    with pytest.raises(ValueError, match='every shot'): validate(rp, bundle)
    r['evidenceViewed'].append('anchor:3'); write(rp, r); validate(rp, bundle)


def test_material_fail_permitted_when_audio_unassessed(case, tmp_path):
    path, _, _, c = case; c['requirements'] = {'speech': True, 'perceptualAudio': True}; write(path, c)
    bundle, _ = prepare(path, tmp_path/'out'); rp = tmp_path/'r.json'; r = review(bundle, rp, 'fail')
    r['speech']['status'] = 'not_assessed'; write(rp, r); validate(rp, bundle)
    r['findings'] = []; write(rp, r)
    with pytest.raises(ValueError, match='material finding'): validate(rp, bundle)
    r['decision'] = 'pass'; write(rp, r)
    with pytest.raises(ValueError, match='needs_review'): validate(rp, bundle)


@pytest.mark.parametrize('count', [12, 6, 1])
def test_contact_sheet_geometry_and_tile_positions(tmp_path, count):
    colors = [(20 + i * 17, 220 - i * 13, 30 + i * 11) for i in range(count)]
    images = []
    for i, color in enumerate(colors):
        image = tmp_path/f'{i}.ppm'
        image.write_bytes(b'P6\n320 200\n255\n' + bytes(color) * (320 * 200))
        images.append(image)
    out = tmp_path/'sheet.png'
    sheet(images, out)
    import struct
    width, height = struct.unpack('>II', out.read_bytes()[16:24])
    assert (width, height) == (min(count, 4) * 320, ((count + 3) // 4) * 200)
    pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(out), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    for i, color in enumerate(colors):
        offset = (((i // 4) * 200 + 100) * width + (i % 4) * 320 + 160) * 3
        assert all(abs(a - b) <= 2 for a, b in zip(pixels[offset:offset+3], color))


def test_contact_sheet_rejects_wrong_output_geometry(tmp_path, monkeypatch):
    import prepare_review as module
    def bad_output(args):
        Path(args[-1]).write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + (1).to_bytes(4, 'big') * 2)
    monkeypatch.setattr(module, 'run', bad_output)
    with pytest.raises(ValueError, match='dimensions.*coverage'):
        sheet([tmp_path/'frame.png'], tmp_path/'bad.png')


def test_current_review_rejects_old_code_malformed_sheet(case, tmp_path):
    path, video, _, _ = case
    bundle, _ = prepare(path, tmp_path/'out')
    rp = tmp_path/'review.json'
    review(bundle, rp)
    validate(rp, bundle)
    bpath = bundle/'bundle.json'
    b = json.loads(bpath.read_text())
    page = next(e for e in b['evidence'] if e['id'] == 'overview')
    # Reproduce the former xstack expression using distinct native inputs.
    anchors = [bundle/e['file'] for e in b['evidence'] if e['kind'] == 'native_anchor'][:2]
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(anchors[0]), '-i', str(anchors[1]),
                    '-filter_complex', '[0:v]scale=320:200[v0];[1:v]scale=320:200[v1];'
                    '[v0][v1]xstack=inputs=2:layout=0*320_0*200|1*320_0*200[out]',
                    '-map', '[out]', '-frames:v', '1', '-y', str(bundle/page['file'])], check=True)
    import struct
    assert struct.unpack('>II', (bundle/page['file']).read_bytes()[16:24]) == (321, 200)
    page['sha256'] = sha(bundle/page['file'])
    b['inputManifest']['code']['prepare_review.py'] = '0' * 64
    b['cacheKey'] = digest(b['inputManifest'])
    b['fingerprint'] = digest({k: v for k, v in b.items() if k != 'fingerprint'})
    write(bpath, b)
    review(bundle, rp)
    with pytest.raises(ValueError, match='preparation code is stale'):
        validate(rp, bundle)
    with pytest.raises(ValueError, match='preparation code is stale'):
        detail(bundle, video, 0, tmp_path/'detail')
