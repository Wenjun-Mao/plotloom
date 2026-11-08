import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('frame_check', Path(__file__).parents[1] / 'scripts/check.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


@pytest.fixture
def sample(tmp_path):
    image = tmp_path / 'image.png'; image.write_bytes(b'same pixels')
    source = tmp_path / 'story.json'
    source.write_text(json.dumps({'episodes': [{'segments': [{'id': 'S1', 'blocking': 'offscreen', 'cuts': [
        {'frame': 'start', 'seconds': 2}, {'frame': 'different role', 'seconds': 3}]}]}]}))
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'segmentId': 'S1', 'sourceFile': str(source), 'sourceSha256': c.digest(source),
        'orderedImages': [{'index': 1, 'file': 'image.png', 'sha256': c.digest(image), 'atMs': 0},
                          {'index': 2, 'file': 'image.png', 'sha256': c.digest(image), 'atMs': 2000}]}))
    case = tmp_path / 'case.json'; c.write(case, c.adapt(manifest, [image]))
    bundle = c.prepare(case)
    report = {'schemaVersion': 1, 'caseId': 'S1', 'bundleFingerprint': bundle['fingerprint'], 'skillVersion': c.VERSION,
              'reviewer': {'model': 'test', 'reasoning': 'high'}, 'decision': 'pass', 'summary': 'reviewed',
              'findings': [], 'evidenceViewed': bundle['evidenceIds'], 'limitations': []}
    return image, source, manifest, case, bundle, report


def test_role_ids_survive_equal_pixels(sample):
    image, _, _, case, bundle, report = sample
    frames = c.read(case)['frames']
    assert frames[0]['image'] == frames[1]['image'] and frames[0]['id'] != frames[1]['id']
    assert c.validate(report, bundle)['valid']


def test_current_originals_rechecked(sample):
    image, _, _, _, bundle, report = sample
    image.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'): c.validate(report, bundle)


def test_story_and_case_mutation_rejected(sample):
    _, source, _, _, bundle, report = sample
    source.write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'): c.validate(report, bundle)


def test_foreign_evidence_and_unsupported_decisions_rejected(sample):
    _, _, _, _, bundle, report = sample
    report['evidenceViewed'] = ['foreign']
    with pytest.raises(ValueError, match='foreign'): c.validate(report, bundle)
    report['decision'] = 'approved'
    with pytest.raises(ValueError, match='unsupported'): c.validate(report, bundle)


def test_fail_needs_viewed_material_evidence(sample):
    _, _, _, _, bundle, report = sample
    report['decision'] = 'fail'
    with pytest.raises(ValueError, match='material'): c.validate(report, bundle)
    report['findings'] = [{'category': 'hands', 'severity': 'material', 'claim': 'visible conflict', 'evidenceIds': ['foreign']}]
    with pytest.raises(ValueError, match='not viewed'): c.validate(report, bundle)
    report['findings'][0]['evidenceIds'] = ['frame:1']
    assert c.validate(report, bundle)['decision'] == 'fail'


def test_pass_requires_every_role_and_no_uncertainty(sample):
    _, _, _, _, bundle, report = sample
    report['evidenceViewed'] = ['frame:1']
    with pytest.raises(ValueError, match='all supplied'): c.validate(report, bundle)
    report['evidenceViewed'] = bundle['evidenceIds']
    report['findings'] = [{'category': 'identity', 'severity': 'uncertain', 'claim': 'unclear', 'evidenceIds': ['frame:1']}]
    with pytest.raises(ValueError, match='uncertain'): c.validate(report, bundle)


def test_adapter_rejects_wrong_timing_and_pins(sample):
    _, _, manifest, _, _, _ = sample
    data = c.read(manifest); data['orderedImages'][1]['atMs'] = 1000; c.write(manifest, data)
    with pytest.raises(ValueError, match='timing'): c.adapt(manifest, [])
    data['sourceSha256'] = 'bad'; c.write(manifest, data)
    with pytest.raises(ValueError, match='hash mismatch'): c.adapt(manifest, [])


def test_missing_segment_id_only_allowed_for_unambiguous_story(sample):
    _, source, manifest, _, _, _ = sample
    data = c.read(manifest); del data['segmentId']; c.write(manifest, data)
    assert c.adapt(manifest, [])['caseId'] == 'S1'
    story = c.read(source); story['episodes'][0]['segments'].append({'id': 'S2', 'cuts': []}); c.write(source, story)
    data['sourceSha256'] = c.digest(source); c.write(manifest, data)
    with pytest.raises(ValueError, match='ambiguous'): c.adapt(manifest, [])


def test_prompt_is_pinned_and_compared_to_source(sample):
    _, source, manifest, _, _, _ = sample
    story = c.read(source); story['episodes'][0]['segments'][0]['h3Prompt'] = 'authored prompt'; c.write(source, story)
    prompt = manifest.parent / 'prompt.txt'; prompt.write_text('different prompt')
    data = c.read(manifest); data.update(sourceSha256=c.digest(source), promptFile='prompt.txt', promptSha256=c.digest(prompt)); c.write(manifest, data)
    with pytest.raises(ValueError, match='prompt differs'): c.adapt(manifest, [])
    prompt.write_text('authored prompt'); data['promptSha256'] = c.digest(prompt); c.write(manifest, data)
    assert len(c.adapt(manifest, [])['originals']) == 3
