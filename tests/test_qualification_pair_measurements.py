"""Small fake evidence streams test measurement admission, not provider/validator acceptance."""
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from tests.qualification_pair_test_support import pair_controls  # noqa: F401


def evidence_case(tmp_path,*,text=False):
    from codex_exec_supervisor import CodexExecSupervisor
    attempt=uuid4()
    private=tmp_path/'private/codex-exec/attempts'/str(attempt)
    private.mkdir(parents=True,mode=0o700)
    for name,raw in (('stdout.jsonl',b'{"synthetic":"stdout"}\n'),('stderr.log',b'unit stderr')):
        (private/name).write_bytes(raw)
        (private/name).chmod(0o600)
    transcript=tmp_path/'transcript.jsonl'
    transcript.write_text(json.dumps(dict(ordinal=1,timestamp='2026-10-15T00:00:00Z',callId='same-call'))+'\n')
    session=SimpleNamespace(transcript_sha256=hashlib.sha256(transcript.read_bytes()).hexdigest(),
        transcript_size_bytes=transcript.stat().st_size)
    validation=SimpleNamespace(evidence_hash='c'*64) if text else None
    base=CodexExecSupervisor._evidence_hash(private/'stdout.jsonl',private/'stderr.log',session.transcript_sha256,0)
    digest=hashlib.sha256(f'{base}:{validation.evidence_hash}'.encode('ascii')).hexdigest() if text else base
    receipt=SimpleNamespace(attempt_id=attempt,process_exit_code=0,evidence_hash=digest,text_validation=validation)
    return dict(root=tmp_path,private=private,row=dict(private_dir=str(private)),receipt=receipt,session=session,
        profile=SimpleNamespace(max_output_bytes=10000),transcript=transcript)


def admit(module,case):
    return module.admit_receipt_measurements(case['root'],case['row'],case['receipt'],case['session'],case['profile'])


@pytest.mark.parametrize('text',[False,True])
def test_unchanged_image_and_layered_text_evidence_admits_measurements(pair_controls,tmp_path,text):
    case=evidence_case(tmp_path,text=text)
    result=admit(pair_controls.modules['session_measurements'],case)
    assert result==dict(receiptEvidenceHash=case['receipt'].evidence_hash,receiptEvidenceHashVerified=True)


@pytest.mark.parametrize('drift',['timestamp','stdout','stderr','validation'])
def test_measurement_drift_refuses_before_timestamp_or_overlap_publication(pair_controls,tmp_path,drift):
    module=pair_controls.modules['session_measurements']
    case=evidence_case(tmp_path,text=drift=='validation')
    admit(module,case)
    if drift=='timestamp':
        data=json.loads(case['transcript'].read_bytes())
        data['timestamp']='2026-10-15T00:01:00Z'
        case['transcript'].write_text(json.dumps(data)+'\n')
        # This reproduces the old fresh-parse self-consistency gap: IDs stay the
        # same and the new parse agrees with the new bytes, but not the receipt.
        case['session'].transcript_sha256=hashlib.sha256(case['transcript'].read_bytes()).hexdigest()
    elif drift=='validation':case['receipt'].text_validation.evidence_hash='d'*64
    else:(case['private']/('stdout.jsonl' if drift=='stdout' else 'stderr.log')).write_bytes(b'changed private stream')
    with pytest.raises(RuntimeError,match='successful receipt evidence'):
        admit(module,case)


@pytest.mark.parametrize('condition',['absent','zero','touching','unbound','positive'])
def test_only_positive_distinct_receipt_bound_tool_intervals_qualify(pair_controls,tmp_path,condition):
    module=pair_controls.modules['session_measurements']
    sessions=pair_controls.exports['receipt_bound_sessions']()
    for index,session in enumerate(sessions):
        case=evidence_case(tmp_path/str(index))
        session.update(admit(module,case),attemptId=str(case['receipt'].attempt_id),
            transcriptSha256=case['session'].transcript_sha256)
    if condition=='absent':sessions[1]['imageCalls']=[]
    elif condition=='zero':
        for session in sessions:session['imageCalls'][0]['completionUtc']=session['imageCalls'][0]['callUtc']
    elif condition=='touching':sessions[1]['imageCalls'][0]['callUtc']=sessions[0]['imageCalls'][0]['completionUtc']
    elif condition=='unbound':sessions[1]['receiptEvidenceHashVerified']=False
    gates=dict(cross=1,images=2,texts=3)
    guard=pair_controls.modules['campaign_guard']
    if condition=='positive':
        proof=guard.require_arm_overlap(gates,sessions)
        assert proof['receiptBoundImageOverlap']['positiveOverlapSeconds']>0
        assert proof['capacityOnlySpeedupEstablished'] is False
    else:
        with pytest.raises(RuntimeError,match='receipt-bound'):
            guard.require_arm_overlap(gates,sessions)


@pytest.mark.parametrize('condition',['positive','timestamp','stdout','stderr','zero'])
def test_actual_typed_receipt_session_measurement_path(pair_controls,tmp_path,monkeypatch,condition):
    from tests.qualification_pair_measurement_fixtures import typed_measurement_arm
    paths,private=typed_measurement_arm(tmp_path,zero=condition=='zero')
    module=pair_controls.modules['session_measurements']
    monkeypatch.setattr(module,'resolve_codex_home',lambda **_options:tmp_path)
    monkeypatch.setattr(module,'locate_exact_session',lambda _home,session_id:paths[session_id])
    if condition=='timestamp':
        path=next(iter(paths.values()))
        records=[json.loads(line) for line in path.read_text().splitlines()]
        records[1]['timestamp']='2026-10-15T00:00:02Z'
        path.write_bytes(b''.join(json.dumps(row,separators=(',',':')).encode()+b'\n' for row in records))
    elif condition in {'stdout','stderr'}:
        (private[0]/('stdout.jsonl' if condition=='stdout' else 'stderr.log')).write_bytes(b'changed private evidence')
    if condition in {'timestamp','stdout','stderr'}:
        with pytest.raises(RuntimeError,match='successful receipt evidence'):
            module.measure_sessions(tmp_path)
    else:
        sessions=module.measure_sessions(tmp_path)
        assert len(sessions)==2 and all(item['receiptEvidenceHashVerified'] for item in sessions)
        if condition=='zero':
            with pytest.raises(RuntimeError,match='receipt-bound'):
                pair_controls.modules['campaign_guard'].require_arm_overlap(dict(cross=1,images=2,texts=3),sessions)
        else:
            assert pair_controls.modules['campaign_guard'].require_arm_overlap(dict(cross=1,images=2,texts=3),sessions)['receiptBoundImageOverlap']['positiveOverlapSeconds']>0
