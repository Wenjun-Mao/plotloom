"""Task-installed V2 publication: native candidate selections and package share one commit.

No provider dispatch here. Only explicitly bound completed native candidates may
replace a published draft; all files are built before selecting any candidate.
"""
from __future__ import annotations

from contextlib import closing
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile

from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy import select

from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel
from plotloom.exceptions import InvalidTransitionError
from plotloom.operator_attribution import CodexTaskAttribution
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.schema import PlayerExportRow, VideoBatchReceiptRow, VideoBatchRow
from plotloom.project_storage.project_video import ProjectVideoRepository
from plotloom.video_batch_inventory import source_binding
from plotloom.video_batch_review import segment_confirmation_valid
from plotloom.persistence.schema import VideoSegmentRow, VideoCandidateSelectionRow

from scripts.prototypes.scene_assembly import assemble, digest, encoded, probe

PROTOTYPE = 'last-projection-v2'
CONTINUITY = {'n00-s3-c1': 'n00-s1-c1', 'n00-s3-c2': 'n00-s3-c1', 'n00-s3-c3': 'n00-s3-c2', 'n00-s3-c4': 'n00-s3-c3',
              'n10-s1-c1': 'n00-s3-c4', 'n10-s1-c2': 'n10-s1-c1', 'n10-s1-c3': 'n10-s1-c2',
              'e01-s1-c1': 'n00-s3-c4', 'e01-s1-c2': 'e01-s1-c1',
              'e02-s1-c1': 'n10-s1-c3', 'e02-s1-c2': 'e02-s1-c1',
              'e03-s1-c1': 'n10-s1-c3', 'e03-s1-c2': 'e03-s1-c1'}


class PrepareApply(CamelModel):
    expected_receipt_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    expected_source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    job_id: str = Field(min_length=1, max_length=100)
    operator: CodexTaskAttribution | None = None


class Apply(PrepareApply):
    proposal_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    replacement_jobs: list[str] = Field(min_length=1, max_length=64)


def current(store):
    with store.repository._read() as session:
        rows = list(session.scalars(select(PlayerExportRow).where(PlayerExportRow.project_id == store.manifest.project_id)
                                   .order_by(PlayerExportRow.created_at.desc(), PlayerExportRow.receipt_hash.desc())))
    for row in rows:
        receipt = json.loads(store.artifacts.get(row.receipt_uri))
        if receipt.get('prototype') == PROTOTYPE:
            if stable_hash(receipt) != row.receipt_hash or receipt['archiveHash'] != row.archive_hash:
                raise InvalidTransitionError('prototype publication receipt changed')
            return row.receipt_hash, receipt
    raise InvalidTransitionError('no published V2 baseline')


def selection_identity(repository, pid):
    # Preserve the actual chosen pointer even when an explicit source edit makes
    # that old take ineligible for a new native export. The old package remains.
    with repository.store.repository._read() as session:
        return {row.shot_id: {'jobId': row.selected_video_job_id, 'revision': row.revision}
                for row in session.scalars(select(VideoCandidateSelectionRow).where(VideoCandidateSelectionRow.project_id == pid))}


def frame_hash(binding, cache):
    target = cache / ('frame-' + binding['sha256'] + '.png')
    if not target.exists():
        n = binding['probe']['frames'] - 1
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', binding['path'], '-vf', f'select=eq(n\\,{n})', '-frames:v', '1', str(target)], check=True, capture_output=True)
    return digest(target.read_bytes())


def replacement_bundle(root_job, jobs, bindings, cache, declared_job_ids=None):
    """Find the declared downstream chain; refuse missing/wrong-frame candidates."""
    if declared_job_ids is not None and len(declared_job_ids) != len(set(declared_job_ids)):
        raise InvalidTransitionError('replacement bundle contains duplicate job identities')
    chosen = {root_job['snapshot']['shot']['id']: root_job}
    changed = dict(bindings)
    pending = list(chosen)
    while pending:
        slot = pending.pop(0); job = chosen[slot]
        path = cache / (job['outputHash'] + '.mp4')
        if not path.exists():
            raise InvalidTransitionError('candidate full output was not retained')
        changed[slot] = {'path': str(path), 'sha256': job['outputHash'], 'probe': probe(path), 'jobId': job['id'],
                         'snapshotHash': stable_hash(job['snapshot']), 'sourceKind': 'native-current-Q8-candidate',
                         'startFrameSha256': job['snapshot']['keyframe']['originalHash']}
        predecessor = CONTINUITY.get(slot)
        if predecessor and predecessor not in chosen and job['snapshot']['keyframe']['originalHash'] != frame_hash(changed[predecessor], cache):
            raise InvalidTransitionError(f'{slot}: START does not bind the currently published predecessor final frame')
        expected = frame_hash(changed[slot], cache)
        for child, parent in CONTINUITY.items():
            if parent != slot:
                continue
            published = bindings[child]
            prior_job = next((j for j in jobs if j['id'] == published.get('jobId')), None)
            published_start = published.get('startFrameSha256') or (prior_job['snapshot']['keyframe']['originalHash'] if prior_job else None)
            if published_start == expected:
                continue
            matching = [j for j in jobs if j['snapshot']['shot']['id'] == child and j['current'] and j['state'] == 'ingested'
                        and j['snapshot']['keyframe']['originalHash'] == expected and j['snapshot']['request']['quality'] == 8
                        and j['outputHash'] != published['sha256']
                        and (declared_job_ids is None or j['id'] in declared_job_ids)]
            if not matching or (declared_job_ids is not None and len(matching) != 1):
                raise InvalidTransitionError(f'连续镜头尚未齐备：{child} 必须从 {slot} 新原片的实际末帧开始。当前游戏保持原样。')
            chosen[child] = matching[0]; pending.append(child)
    if declared_job_ids is not None and set(declared_job_ids) != {job['id'] for job in chosen.values()}:
        raise InvalidTransitionError('declared replacement bundle differs from the necessary exact continuity scope')
    return chosen, changed


def inventory_row(store, receipt, archive):
    archive_uri = store.artifacts.put(archive)
    receipt = receipt | {'prototype': PROTOTYPE, 'archiveUri': archive_uri, 'projectId': store.manifest.project_id}
    uri = store.artifacts.put(encoded(receipt))
    return receipt, PlayerExportRow(receipt_hash=stable_hash(receipt), project_id=store.manifest.project_id,
        receipt_uri=uri, archive_hash=receipt['archiveHash'], archive_uri=archive_uri, created_at=utc_now())


def publish_baseline(storage, pid, root, presentation):
    with closing(storage.projects.open(pid)) as store:
        try:
            return current(store)
        except InvalidTransitionError as error:
            if str(error) != 'no published V2 baseline':
                raise
        archive = (root / 'baseline.zip').read_bytes()
        receipt = json.loads((root / 'baseline-receipt.json').read_text())
        if digest(archive) != receipt['archiveHash']:
            raise InvalidTransitionError('baseline archive changed')
        repository = ProjectVideoRepository(store, storage.application)
        receipt |= {'presentation': presentation, 'nativeSelections': selection_identity(repository, pid), 'sourceBinding': source_binding(store),
                    'continuity': CONTINUITY, 'continuityStatus': 'baseline-repair-pending'}
        with store.repository.manual_command() as session:
            receipt, row = inventory_row(store, receipt, archive); session.add(row)
        return row.receipt_hash, receipt


def refresh_player(storage, pid, root):
    """Explicit local UI checkpoint over identical bindings, before media Apply QA."""
    with closing(storage.projects.open(pid)) as store:
        before_hash, before = current(store)
        repository = ProjectVideoRepository(store, storage.application)
        selections = selection_identity(repository, pid)
        if selections != before['nativeSelections']:
            raise InvalidTransitionError('cannot refresh a package with divergent native selections')
        source = source_binding(store)
        archive, receipt = assemble(before['source'], before['bindings'], root / 'cache', Path(__file__).resolve().parents[2] / 'src/plotloom/player_static')
        if receipt['archiveHash'] == before['archiveHash']:
            return before_hash, before
        if receipt['story']['assetVersion'] != before['story']['assetVersion'] or receipt['story']['storyRevision'] != before['story']['storyRevision']:
            raise InvalidTransitionError('UI checkpoint must not adopt different story or media')
        receipt |= {'presentation': before['presentation'], 'nativeSelections': selections, 'sourceBinding': source,
                    'continuity': CONTINUITY, 'continuityStatus': before['continuityStatus'], 'priorUiReceiptHash': before_hash}
        with store.repository.manual_command() as session:
            if current(store)[0] != before_hash or selection_identity(repository, pid) != selections or source_binding(store) != source:
                raise InvalidTransitionError('UI checkpoint inputs changed')
            receipt, row = inventory_row(store, receipt, archive); session.add(row)
        return row.receipt_hash, receipt


def collect_inputs(store, storage, pid, root, request):
    before_hash, before = current(store)
    repository = ProjectVideoRepository(store, storage.application)
    source = source_binding(store)
    if before_hash != request.expected_receipt_hash or stable_hash(source) != request.expected_source_hash:
        raise InvalidTransitionError('发布版本或当前来源已变化；请重新读取，当前游戏保持原样。')
    jobs = repository.list_video_jobs(pid)
    candidate = next((j for j in jobs if j['id'] == request.job_id), None)
    if not candidate or candidate['state'] != 'ingested' or not candidate['current'] or candidate['snapshot']['request']['quality'] != 8:
        raise InvalidTransitionError('Apply requires a current ingested Q8 candidate')
    cache = root / 'cache'
    for job in jobs:
        if job['state'] == 'ingested' and job['current']:
            data = store.artifacts.get(repository.get_video_output_storage(pid, job['id'])['uri'])
            if digest(data) != job['outputHash']:
                raise InvalidTransitionError('candidate bytes changed')
            (cache / (job['outputHash'] + '.mp4')).write_bytes(data)
    return before_hash, before, repository, source, jobs, candidate, cache


def bundle_proposal(before_hash, before, source, root_job, chosen):
    return {'expectedReceiptHash': before_hash, 'expectedSourceHash': stable_hash(source), 'rootJobId': root_job['id'],
            'replacements': [{'slot': slot, 'jobId': job['id'], 'oldJobId': before['bindings'][slot].get('jobId'),
                              'oldSha256': before['bindings'][slot]['sha256'], 'newSha256': job['outputHash'],
                              'startFrameSha256': job['snapshot']['keyframe']['originalHash'], 'dependsOn': CONTINUITY.get(slot)}
                             for slot, job in sorted(chosen.items())]}


def prepare_apply(storage, pid, root, request):
    with closing(storage.projects.open(pid)) as store:
        before_hash, before, repository, source, jobs, candidate, cache = collect_inputs(store, storage, pid, root, request)
        chosen, _ = replacement_bundle(candidate, jobs, before['bindings'], cache)
        proposal = bundle_proposal(before_hash, before, source, candidate, chosen)
        return proposal | {'proposalHash': stable_hash(proposal)}


def apply_candidate(storage, pid, root, request):
    with closing(storage.projects.open(pid)) as store:
        before_hash, before, repository, source, jobs, candidate, cache = collect_inputs(store, storage, pid, root, request)
        chosen, bindings = replacement_bundle(candidate, jobs, before['bindings'], cache, request.replacement_jobs)
        proposal = bundle_proposal(before_hash, before, source, candidate, chosen)
        if stable_hash(proposal) != request.proposal_hash:
            raise InvalidTransitionError('替换范围或原片身份已变化；请重新核对完整提案。')
        expected_selections = selection_identity(repository, pid)
        if expected_selections != before['nativeSelections']:
            raise InvalidTransitionError('项目选择与已发布版本不同；请先核对，当前游戏保持原样。')
        proposals = {slot: repository.prepare_video_segment(pid, j['id'], in_frame=0,
                       expected_selection_revision=j['selectionRevision']) for slot, j in chosen.items()}
        archive, receipt = assemble(before['source'], bindings, cache, Path(__file__).resolve().parents[2] / 'src/plotloom/player_static')
        receipt |= {'presentation': before['presentation'], 'sourceBinding': source, 'continuity': CONTINUITY,
                    'continuityStatus': 'exact-final-frame-inputs', 'priorReceiptHash': before_hash,
                    'changedSlots': sorted(chosen), 'appliedProposal': proposal, 'operator': request.operator.model_dump(mode='json', by_alias=True) if request.operator else {'kind': 'unnamed_creator'}}
        from plotloom.human_confirmation_contracts import UnnamedCreatorConfirmation
        actor = request.operator or UnnamedCreatorConfirmation()
        with store.repository.manual_command() as session:
            if current(store)[0] != before_hash or source_binding(store) != source or selection_identity(repository, pid) != expected_selections:
                raise InvalidTransitionError('publication inputs changed while the package was being prepared')
            facts_by_batch = {}
            for slot, job in chosen.items():
                batch = session.scalar(select(VideoBatchRow).where(VideoBatchRow.project_id == pid).filter(
                    VideoBatchRow.id == job['snapshot']['reviewedDirections']['reviewBasis']['batchId']))
                if not batch or batch.state not in {'awaiting_review', 'cancelled'} or batch.execution.get('reviewAttribution'):
                    raise InvalidTransitionError('prototype Apply needs a settled non-QA native candidate batch')
                if job['reviews'] and job['reviews'][-1]['decision'] == 'reject':
                    raise InvalidTransitionError('rejected take requires its native reconsideration path')
                if session.scalar(select(VideoBatchReceiptRow).where(VideoBatchReceiptRow.batch_id == batch.id)):
                    raise InvalidTransitionError('candidate batch already has an immutable selection receipt')
                if batch.execution.get('jobs', {}).get(slot) != job['id']:
                    raise InvalidTransitionError('candidate differs from its exact native batch job')
                identifier = new_id(); session.info['pending_video_pack_receipt'] = identifier
                try:
                    selected = repository.select_video_segment(pid, proposals[slot]['id'], reviewer=actor, note='', expected_selection_revision=job['selectionRevision'])
                finally:
                    session.info.pop('pending_video_pack_receipt', None)
                fact = {'shotId': slot, 'jobId': job['id'], 'segmentId': selected['id'], 'selectionRevision': selected['selectedRevision'], 'derivativeHash': selected['derivativeHash']}
                facts = {'id': identifier, 'version': 'source-bound-selections.v1', 'batchId': batch.id, 'projectId': pid,
                         'manifestHash': batch.manifest_hash, 'reviewHash': stable_hash({'prototypeApply': before_hash, 'job': job['id'], 'segment': proposals[slot]}),
                         'attribution': receipt['operator'], 'kept': [], 'selections': [fact], 'prototypePublication': receipt['archiveHash']}
                session.add(VideoBatchReceiptRow(id=identifier, batch_id=batch.id, receipt=facts, receipt_hash=stable_hash(facts), created_at=utc_now()))
                facts_by_batch[batch.id] = fact
                if batch.state == 'awaiting_review':
                    batch.state = 'approved'; batch.revision += 1
            session.flush()
            if any(not segment_confirmation_valid(session, session.get(VideoSegmentRow, fact['segmentId'])) for fact in facts_by_batch.values()):
                raise InvalidTransitionError('source-bound selection receipt failed shared admission')
            receipt['nativeSelections'] = selection_identity(repository, pid)
            receipt, row = inventory_row(store, receipt, archive); session.add(row)
        return row.receipt_hash, receipt


def register(app, storage, pid, root, operator_task=None):
    def view(store):
        identity, receipt = current(store)
        return {'receiptHash': identity, 'sourceHash': stable_hash(source_binding(store)), 'gameUrl': '/v2-game/index.html',
                'downloadUrl': f'/api/v2/projects/{pid}/prototype-download', 'slots': receipt['bindings'], 'nativeSelections': receipt['nativeSelections'],
                'operator': {'kind': 'codex_task', 'taskId': operator_task} if operator_task else None}

    @app.get('/api/v2/projects/{project_id}/prototype-publication')
    def read(project_id: str):
        if project_id != pid:
            raise HTTPException(404)
        with closing(storage.projects.open(pid)) as store:
            return view(store)

    @app.post('/api/v2/projects/{project_id}/prototype-prepare-apply')
    def prepare(project_id: str, body: PrepareApply):
        if project_id != pid:
            raise HTTPException(404)
        try:
            return prepare_apply(storage, pid, root, body)
        except (InvalidTransitionError, ValueError, OSError, subprocess.CalledProcessError) as error:
            raise HTTPException(409, str(error)) from None

    @app.post('/api/v2/projects/{project_id}/prototype-apply')
    def apply(project_id: str, body: Apply):
        if project_id != pid:
            raise HTTPException(404)
        try:
            apply_candidate(storage, pid, root, body)
        except (InvalidTransitionError, ValueError, OSError, subprocess.CalledProcessError) as error:
            raise HTTPException(409, str(error)) from None
        with closing(storage.projects.open(pid)) as store:
            return view(store)

    @lru_cache(maxsize=4)
    def extract(archive_hash: str, archive_uri: str):
        target = root / 'published' / archive_hash
        if not target.exists():
            with closing(storage.projects.open(pid)) as store:
                data = store.artifacts.get(archive_uri)
            if digest(data) != archive_hash:
                raise InvalidTransitionError('published archive bytes changed')
            with ZipFile(BytesIO(data)) as archive:
                if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in archive.namelist()):
                    raise InvalidTransitionError('archive contains an unsafe public path')
                target.mkdir(parents=True); archive.extractall(target)
        return target

    @app.get('/api/v2/projects/{project_id}/prototype-download')
    def download(project_id: str):
        if project_id != pid:
            raise HTTPException(404)
        with closing(storage.projects.open(pid)) as store:
            _, receipt = current(store)
        game = extract(receipt['archiveHash'], receipt['archiveUri'])
        archive = game.parent / (receipt['archiveHash'] + '.zip')
        if not archive.exists():
            with closing(storage.projects.open(pid)) as store:
                archive.write_bytes(store.artifacts.get(receipt['archiveUri']))
        return FileResponse(archive, filename='the-last-projection-v2.zip', media_type='application/zip')

    @app.get('/v2-game/{filename:path}')
    def game(filename: str):
        name = PurePosixPath(filename)
        if name.is_absolute() or '..' in name.parts:
            raise HTTPException(404)
        with closing(storage.projects.open(pid)) as store:
            _, receipt = current(store)
        path = extract(receipt['archiveHash'], receipt['archiveUri']) / name
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, headers={'Cache-Control': 'no-cache'})
