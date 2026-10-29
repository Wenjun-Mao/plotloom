"""Synthetic immutable media witnesses; no real provider or normal-home access."""
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace

import pytest

from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.persistence.project.selected_media_policy import selected_playback_policy, selected_playback_read
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.video_storage_fixtures import FakeH3, _approved_keyframe, _fixture_app


@pytest.fixture
def selected_bridge(tmp_path,monkeypatch):
    # Production pin enforcement remains strict while the coordinator owns the
    # uncommitted fork. This test-only transport uses an explicitly synthetic pin.
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from tests.autopilot_controller_fixtures import PIN
    monkeypatch.setattr(CreativeHandoffExchange,"current_execution_pin",lambda _self,_stage:PIN)
    provider=FakeH3();storage,client=_fixture_app(tmp_path,provider)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project=store.manifest.project_id;proposal=_prepare_installable_bridge(store)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision,expected_content_hash=proposal.content_hash))
    approval,context=_approved_keyframe(client,storage,project)
    # Seed an already-ingested immutable witness. Preparing new H3 work would
    # exercise the unrelated current prompt compiler, not retained playback.
    from plotloom.contract_identity import utc_now
    from plotloom.persistence.codec import stable_hash
    from plotloom.language_policy import language_contract
    from plotloom.persistence.schema import VideoJobRow, ApprovalDecisionRow, ManagedAssetRow
    from plotloom.persistence.project.media_identifiers import new_video_job_id
    from tests.test_frozen_video_integrity import _job
    with closing(storage.projects.open(project)) as store:
        raw=b'explicitly-synthetic-original-witness'
        raw_hash=sha256(raw).hexdigest();uri=store.artifacts.put(raw,expected_hash=raw_hash)
        with store.repository._write() as session:
            frozen=_job().snapshot
            selection=context['selection']
            asset=session.get(ManagedAssetRow,selection['assetId'])
            decision=session.get(ApprovalDecisionRow,approval['id'])
            frozen.update(shot=context['shot'].model_dump(mode='json',by_alias=True),
                sourceTiming=store.repository._media.direct_video._source_timing.binding_in_session(
                    session,project,context['shot'].id,context['shot'].duration_units),
                approvalId=approval['id'],storyboardEntityRevisionId=decision.entity_revision_id,
                languageContract=language_contract('zh-CN'),
                keyframe={'bindingId':selection['id'],'assetId':asset.id,'originalHash':asset.original_hash,
                    'selectionRevision':selection['selectionRevision']})
            key='synthetic-retained-selected';identifier=new_video_job_id();now=utc_now()
            row=VideoJobRow(id=identifier,project_id=project,idempotency_key=key,state='ingested',
                requested_seconds=8,output_uri=uri,output_hash=raw_hash,snapshot=frozen,
                snapshot_hash=stable_hash(frozen),request_hash=stable_hash({'snapshot':frozen,'idempotencyKey':key}),
                created_at=now,updated_at=now)
            session.add(row)
        job={'id':identifier,'snapshot':frozen}
    base=f'/api/v2/projects/{project}';url=f"{base}/video-jobs/{job['id']}"
    # This metadata-only witness is explicitly synthetic, not a video-quality claim.
    content=b'explicitly-synthetic-playback-witness'
    def derive(_raw,*,in_frame,out_frame,authored_duration_units):
        return SimpleNamespace(content=content,digest=sha256(content).hexdigest(),in_frame=in_frame,out_frame=out_frame,
            source_probe={'frameCount':192,'fps':'24/1'},output_probe={'frameCount':out_frame-in_frame,'fps':'24/1'})
    monkeypatch.setattr('plotloom.project_storage.project_video.derive_playback_segment',derive)
    segment=client.post(url+'/segments',json={'inFrame':0,'outFrame':context['shot'].duration_units*24//1000,'expectedSelectionRevision':0})
    assert segment.status_code==201,segment.text
    segment=segment.json()
    selected=client.post(f"{base}/video-segments/{segment['id']}/select",json={'expectedSelectionRevision':0})
    assert selected.status_code==201,selected.text
    assert client.get(url+'/playback').content==content
    return storage,client,project,url,job,segment,content


def change_code_only(monkeypatch):
    monkeypatch.setattr('plotloom.persistence.project.cast.cast_style_current',lambda *_:False)
    monkeypatch.setattr('plotloom.persistence.project.art.art_style_current',lambda *_:False)
    monkeypatch.setattr('plotloom.language_policy.TIMING_POLICY_VERSION','new-code-only-version')
    def new_timing(*_args,**_kwargs):
        raise AssertionError('selected playback must never execute the new timing estimator')
    monkeypatch.setattr('plotloom.persistence.project.storyboard_review.freeze_f5_dialogue_timing',new_timing)


def test_selected_f5_media_survives_code_only_policy_drift_and_new_work_stays_refused(selected_bridge,monkeypatch):
    storage,client,project,url,job,segment,content=selected_bridge
    change_code_only(monkeypatch)
    with closing(storage.projects.open(project)) as store:
        with selected_playback_policy(project):
            state=store.production_bridge_state()
            assert state.installation.status=='current',state.model_dump(mode='json',by_alias=True)
    assert client.get(url+'/playback').content==content
    rows=client.get(f'/api/v2/projects/{project}/video-jobs').json()['jobs']
    current=next(row for row in rows if row['id']==job['id'])
    assert current['selected'] and current['playbackSegment']['id']==segment['id']
    assert not current['productionEligible'] and not current['current']
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().installation.status=='outdated'
        from plotloom.review_context_diagnostics import ReviewContextError
        with pytest.raises(ReviewContextError):store.prepare_script_candidate('ch_'+'r'*32)
        assert not selected_playback_read()
        with store.repository._read() as session:
            from plotloom.persistence.schema import VideoJobRow
            before=session.connection().connection.driver_connection.total_changes
            assert store.repository._media.direct_video._currentness.selected_video_current_in_session(session,session.get(VideoJobRow,job['id']))
            assert session.connection().connection.driver_connection.total_changes==before


@pytest.mark.parametrize('mutation',['source','script','language','selection','asset','approval','unresolved'])
def test_actual_changes_still_withdraw_selected_playback(selected_bridge,monkeypatch,mutation):
    storage,client,project,url,job,segment,_content=selected_bridge;change_code_only(monkeypatch)
    from plotloom.persistence.schema import ProjectRow,VideoCandidateSelectionRow,ManagedAssetRow,ApprovalDecisionRow
    with closing(storage.projects.open(project)) as store:
        with store.repository._write() as session:
            if mutation=='source':
                row=session.get(ProjectRow,project);row.brief=dict(row.brief,title='Actual author edit')
            elif mutation=='language':
                row=session.get(ProjectRow,project);row.brief=dict(row.brief,language='en-US')
            elif mutation=='unresolved':
                from plotloom.persistence.schema import VideoJobRow
                session.get(VideoJobRow,job['id']).state='outcome_unknown'
            elif mutation=='script':
                from sqlalchemy import select
                from copy import deepcopy
                from plotloom.persistence.schema import ScriptRevisionRow
                row=session.scalar(select(ScriptRevisionRow).where(ScriptRevisionRow.project_id==project))
                changed=deepcopy(row.script)
                from plotloom.persistence.codec import stable_hash
                changed['episodes'][0]['scenes'][0]['flow'][0]['action']+='真正改变来源动作。'
                row.script=changed;row.content_hash=stable_hash(changed)
            elif mutation=='selection':
                row=session.get(VideoCandidateSelectionRow,(project,job['snapshot']['shot']['id']));row.selected_video_job_id=None
            elif mutation=='asset':
                row=session.get(ManagedAssetRow,job['snapshot']['keyframe']['assetId']);row.original_hash='d'*64
            else:
                row=session.get(ApprovalDecisionRow,job['snapshot']['approvalId']);row.decision='reject'
    assert client.get(url+'/playback').status_code==404
    assert not selected_playback_read()


def test_selected_policy_scope_resets_on_exception_and_is_project_bound():
    assert not selected_playback_read()
    with pytest.raises(RuntimeError):
        with selected_playback_policy('one'):
            assert selected_playback_read('one') and not selected_playback_read('two')
            raise RuntimeError('read failed')
    assert not selected_playback_read()


@pytest.mark.parametrize('mutation',['line','delivery','script_hash','language'])
def test_retained_spoken_timing_requires_exact_source_coordinates_and_policy_inputs(mutation):
    from copy import deepcopy
    from plotloom.production_dialogue_timing import freeze_f5_dialogue_timing
    from plotloom.persistence.project.selected_media_policy import retained_timing_matches
    script={'episodes':[{'ep':1,'scenes':[{'flow':[{'line':'留下安字。','delivery':'natural'}]}]}]}
    frozen=freeze_f5_dialogue_timing(script,script_content_hash='a'*64,language='zh-CN')
    assert len(frozen.lines)==1 and retained_timing_matches(frozen,script,'a'*64,'zh-CN')
    changed=deepcopy(script);script_hash='a'*64;language='zh-CN'
    if mutation=='line':changed['episodes'][0]['scenes'][0]['flow'][0]['line']='删掉安字。'
    elif mutation=='delivery':changed['episodes'][0]['scenes'][0]['flow'][0]['delivery']='brisk'
    elif mutation=='script_hash':script_hash='b'*64
    else:language='en-US'
    assert not retained_timing_matches(frozen,changed,script_hash,language)
