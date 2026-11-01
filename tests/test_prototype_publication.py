"""Real decoded provider-free candidates through V2 atomic publication/refusals."""
from contextlib import closing
from pathlib import Path
import json
import subprocess

import pytest
from sqlalchemy import select

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.schema import PlayerExportRow, VideoBatchReceiptRow
from plotloom.video_batch_contracts import BatchControl, BatchSetup, BatchConfirmation
from plotloom.operator_attribution import CodexTaskAttribution
from plotloom.video_ingestion import probe_video
from plotloom.video_backends.minimax_h3.catalog import H3_QUALIFIED_DURATION_FRAMES
from scripts.prototypes import prototype_publication as publication
from scripts.prototypes.scene_assembly import assemble, digest, probe
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch

ACTOR = CodexTaskAttribution(task_id='00000000-0000-4000-8000-000000000001')

@pytest.fixture(scope='module')
def takes(tmp_path_factory):
    root = tmp_path_factory.mktemp('prototype-native-takes')
    result = []
    for color, frames in [('blue', H3_QUALIFIED_DURATION_FRAMES[5]), ('red', H3_QUALIFIED_DURATION_FRAMES[8])]:
        path = root / (color + '.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', f'color=c={color}:size=576x1024:rate=24',
            '-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate=48000:duration={frames / 24}', '-frames:v', str(frames),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-movflags', '+faststart', '-y', str(path)], check=True, timeout=30)
        result.append(path)
    return result


def cancel(service, pid, view):
    return service.control(pid, BatchControl(batchId=view['id'], expectedControlRevision=view['controlRevision'], action='cancel'))


def finish(service, pid, view):
    start_batch(service, pid, ready_batch(service, pid, view))
    for _ in range(8):
        service.step(pid)
        value = service.current(pid)
        if value['state'] in {'awaiting_review', 'blocked'}:
            break
    assert value['state'] == 'awaiting_review', value['execution'].get('error')
    return value


@pytest.fixture
def draft(tmp_path, takes, monkeypatch):
    monkeypatch.setattr(publication, 'CONTINUITY', {})
    storage, _client, service, provider, pid, initial = batch_environment(tmp_path / 'native')
    sid = initial['manifest']['targets'][0]['shotId']
    cancel(service, pid, initial)
    provider._outputs = [takes[0].read_bytes()]
    service.video._probe = probe_video
    first = service.setup(pid, BatchSetup(profileId='minimax_h3_quality8_portrait_576x1024_v2', shotIds=[sid]))
    first = finish(service, pid, first)
    review = service.review(pid)
    service.confirm(pid, BatchConfirmation(expectedRevision=first['revision'], reviewHash=review['reviewHash'], basis='source-bound-selections.v1', attribution=ACTOR))
    with closing(storage.projects.open(pid)) as store:
        old = next(j for j in service.video.jobs(store) if j['selected'])
        visual = store.media.visual_selection_revision(pid)
    root = tmp_path / 'delivery'; root.mkdir(); (root / 'cache').mkdir()
    source = dict(format=1, gameId='prototype-fixture', title='Fixture', intro='', start='opening', nodes=[dict(id='opening', title='Opening', clips=[dict(slot=sid, dialogue=[], visibleText=[])], edges=[], question='', ending={'title':'End','text':'Done'})])
    bindings = {sid: dict(path=str(takes[0]), sha256=digest(takes[0].read_bytes()), probe=probe(takes[0]), jobId=old['id'])}
    static = Path(__file__).parents[1] / 'src/plotloom/player_static'
    archive, receipt = assemble(source, bindings, root / 'cache', static)
    (root / 'baseline.zip').write_bytes(archive); (root / 'baseline-receipt.json').write_text(json.dumps(receipt))
    publication.publish_baseline(storage, pid, root, {})
    args = first['manifest']['targets'][0]['args']
    from plotloom.video_contracts import VideoJobRequest
    request = VideoJobRequest(approvalId=args['approval_id'], shotId=sid, storyboardRevision=args['storyboard_revision'], expectedSelectionRevision=visual,
        idempotencyKey='explicit-prototype-alternative', requestedDurationSeconds=8, resolution='576x1024', audio=True, aspectPolicy='reject_mismatch',
        seed=31, profileId='minimax_h3_quality8_portrait_576x1024_v2', playbackIntent='whole_take')
    second = service.setup(pid, BatchSetup(profileId=request.profile_id, shotIds=[sid], singleRequest=request))
    provider._outputs = [takes[1].read_bytes()]
    second = finish(service, pid, second)
    cancel(service, pid, second)  # completed candidates survive ordinary stop-new-dispatch
    with closing(storage.projects.open(pid)) as store:
        before_hash, before = publication.current(store)
        current_source = publication.source_binding(store)
        jobs = service.video.jobs(store)
        candidate = next(j for j in jobs if j['id'] != old['id'])
        assert next(j for j in jobs if j['id'] == old['id'])['selected']
    body = publication.Apply(expectedReceiptHash=before_hash, expectedSourceHash=stable_hash(current_source), jobId=candidate['id'], operator=ACTOR)
    return storage, pid, root, body, before_hash, before, old, candidate


def test_apply_commits_native_selection_and_actual_package_together(draft):
    storage, pid, root, body, before_hash, before, old, candidate = draft
    new_hash, after = publication.apply_candidate(storage, pid, root, body)
    assert new_hash != before_hash and after['archiveHash'] != before['archiveHash']
    assert after['story']['storyRevision'] == before['story']['storyRevision']
    assert after['story']['assetVersion'] != before['story']['assetVersion']
    assert after['changedSlots'] == [candidate['snapshot']['shot']['id']]
    assert next(iter(after['bindings'].values()))['probe']['frames'] == H3_QUALIFIED_DURATION_FRAMES[8]
    with closing(storage.projects.open(pid)) as store:
        repository = publication.ProjectVideoRepository(store, storage.application)
        assert publication.selection_identity(repository, pid) == after['nativeSelections']
        assert after['nativeSelections'][candidate['snapshot']['shot']['id']]['jobId'] == candidate['id']
        assert publication.current(store)[0] == new_hash
        assert digest(store.artifacts.get(after['archiveUri'])) == after['archiveHash']
    with pytest.raises(InvalidTransitionError, match='发布版本'):
        publication.apply_candidate(storage, pid, root, body)


@pytest.mark.parametrize('failure', ['assembly', 'late-publication', 'stale-source', 'wrong-job'])
def test_failed_apply_preserves_prior_pointer_and_selection(draft, monkeypatch, failure):
    storage, pid, root, body, before_hash, before, old, candidate = draft
    if failure == 'assembly':
        monkeypatch.setattr(publication, 'assemble', lambda *_: (_ for _ in ()).throw(ValueError('build failed')))
    elif failure == 'late-publication':
        monkeypatch.setattr(publication, 'inventory_row', lambda *_: (_ for _ in ()).throw(ValueError('publication failed after selection')))
    elif failure == 'stale-source':
        body = body.model_copy(update={'expected_source_hash': '0' * 64})
    else:
        body = body.model_copy(update={'job_id': 'foreign-job'})
    with pytest.raises((InvalidTransitionError, ValueError)):
        publication.apply_candidate(storage, pid, root, body)
    with closing(storage.projects.open(pid)) as store:
        repository = publication.ProjectVideoRepository(store, storage.application)
        assert publication.current(store)[0] == before_hash
        assert publication.selection_identity(repository, pid) == before['nativeSelections']
        with store.repository._read() as session:
            assert len(list(session.scalars(select(PlayerExportRow)))) == 1
            assert len(list(session.scalars(select(VideoBatchReceiptRow)))) == 1  # baseline only


def test_incomplete_or_wrong_frame_continuity_bundle_refuses_apply(tmp_path, takes, monkeypatch):
    monkeypatch.setattr(publication, 'CONTINUITY', {'child': 'root'})
    cache = tmp_path / 'cache'; cache.mkdir()
    content = takes[0].read_bytes(); sha = digest(content); path = cache / (sha + '.mp4'); path.write_bytes(content)
    binding = {'path': str(path), 'sha256': sha, 'probe': probe(path)}
    root = {'id': 'candidate-root', 'outputHash': sha, 'state': 'ingested', 'current': True,
            'snapshot': {'shot': {'id': 'root'}, 'request': {'quality': 8}, 'keyframe': {'originalHash': 'x'}}}
    child = {'id': 'wrong-start', 'outputHash': 'b' * 64, 'state': 'ingested', 'current': True,
             'snapshot': {'shot': {'id': 'child'}, 'request': {'quality': 8}, 'keyframe': {'originalHash': '0' * 64}}}
    with pytest.raises(InvalidTransitionError, match='连续镜头尚未齐备'):
        publication.replacement_bundle(root, [root, child], {'root': binding, 'child': binding}, cache)


def test_scene_assembly_preserves_all_component_frames_and_slot_offsets(tmp_path, takes):
    slots = {name: {'path': str(path), 'sha256': digest(path.read_bytes()), 'probe': probe(path)} for name, path in zip(['one', 'two'], takes, strict=True)}
    source = dict(format=1, gameId='scene-fixture', title='Scene', intro='', start='scene', nodes=[
        dict(id='scene', title='Scene', clips=[dict(slot='one', dialogue=[{'speaker':'A','text':'First'}], visibleText=[]), dict(slot='two', dialogue=[{'speaker':'B','text':'Second'}], visibleText=[])], edges=[dict(id='choice', to='choice', label=None)], question='', ending=None),
        dict(id='choice', title='Choice', clips=[], edges=[], question='?', ending=None)])
    archive, receipt = assemble(source, slots, tmp_path / 'cache', Path(__file__).parents[1] / 'src/plotloom/player_static')
    scene = receipt['story']['nodes'][0]['clips'][0]
    assert receipt['scenes']['scene']['frames'] == sum(probe(p)['frames'] for p in takes)
    assert scene['segments'][1]['start'] == probe(takes[0])['frames'] / 24
    assert scene['segments'][1]['dialogue'][0]['text'] == 'Second'
    assert receipt['story']['nodes'][1]['clips'] == []
    assert digest(archive) == receipt['archiveHash']
