"""Synthetic typed receipts and real telemetry parsing; no tool call is executed."""
import hashlib
import json
import sqlite3
from uuid import uuid4

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,CodexExecImageEvidence,CodexExecOutputEvidence,CodexExecReceipt,
    image_arguments_hash,output_manifest_hash,transition_exec_attempt,
)
from plotloom.codex_exec_telemetry import read_cli_session
from tests.codex_exec_fixtures import PROFILE
from tests.test_codex_exec_telemetry import _record,_image_call,_extension


def typed_measurement_arm(root,*,zero=False):
    from codex_exec_terminal_receipt import evidence_hash_for_process
    database=root/'private/codex-exec/supervisor.sqlite3'
    database.parent.mkdir(parents=True,mode=0o700)
    (root/'plan.json').write_text(json.dumps({'profile':PROFILE.model_dump(mode='json',by_alias=True)}))
    paths={}
    private_paths=[]
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE exec_attempts(attempt_id,status_json,receipt_json,private_dir)')
        for index,(begin,end) in enumerate((('00:00:00','00:00:03'),('00:00:01','00:00:04'))):
            session_id,attempt_id=uuid4(),uuid4()
            call_id,event_id='call-'+str(index),'event-'+str(index)
            records=[json.loads(_record('session_meta',{'id':str(session_id)},ordinal=0)),
                json.loads(_image_call(call_id,ordinal=1)),json.loads(_extension('completed',event_id=event_id,ordinal=2))]
            records[1]['timestamp']='2026-10-15T'+begin+'Z'
            records[2]['timestamp']='2026-10-15T'+(begin if zero else end)+'Z'
            path=root/(str(session_id)+'.jsonl')
            path.write_bytes(b''.join(json.dumps(row,separators=(',',':')).encode()+b'\n' for row in records))
            session=read_cli_session(path,session_id,max_event_bytes=PROFILE.max_event_bytes,max_total_bytes=PROFILE.max_output_bytes)
            private=database.parent/'attempts'/str(attempt_id)
            private.mkdir(parents=True,mode=0o700)
            for name in ('stdout.jsonl','stderr.log'):
                (private/name).write_bytes(b'synthetic private stream')
                (private/name).chmod(0o600)
            evidence=evidence_hash_for_process(private/'stdout.jsonl',private/'stderr.log',session.transcript_sha256,0)
            output=CodexExecOutputEvidence(outputHash='d'*64,outputRelativePath='delivery/outputs/frame.png',sizeBytes=9)
            prompt=hashlib.sha256(b'a quiet blue room').hexdigest()
            image=CodexExecImageEvidence(attemptId=attempt_id,sessionId=session_id,callId=call_id,callOrdinal=1,
                eventId=event_id,eventType='image_gen.generation',eventStatus='completed',
                argumentsHash=image_arguments_hash(prompt_hash=prompt,reference_hashes=(),transparent_background=False,num_last_images_to_include=None),
                promptHash=prompt,transparentBackground=False,outputHash=output.output_hash,outputRelativePath=output.output_relative_path)
            original=CodexExecAttempt(attemptId=attempt_id,runId=uuid4(),projectId=uuid4(),jobId='ij_'+uuid4().hex[:24],
                operationKey='image:shot-'+str(index),domain='image',requestHash='a'*64,packageHash='b'*64,
                profileHash=PROFILE.profile_hash,plotloomCodeRevision='c'*40,reservedImageOutputs=1,
                imageBudgetState='reserved',state='spawn_intent')
            current=transition_exec_attempt(original,state='completed',session_id=session_id,
                process_id=1001+index,process_group_id=1001+index,process_birth_identity='synthetic-not-probed',
                process_exit_code=0,terminal_result='success',remote_tool_state='completed',
                evidence_hash=evidence,output_hash=output_manifest_hash((output,)),remote_output_hash=output.output_hash,image_budget_state='consumed')
            receipt=CodexExecReceipt(attemptId=attempt_id,sessionId=session_id,profileHash=PROFILE.profile_hash,
                requestHash=original.request_hash,packageHash=original.package_hash,plotloomCodeRevision=original.plotloom_code_revision,
                processId=current.process_id,processGroupId=current.process_group_id,processBirthIdentity=current.process_birth_identity,
                processExitCode=0,expectedImageOutputs=1,evidenceHash=evidence,outputHash=current.output_hash,
                outputs=(output,),imageEvidence=(image,),remoteOutputHash=output.output_hash,remoteToolState='completed')
            connection.execute('INSERT INTO exec_attempts VALUES(?,?,?,?)',
                (str(attempt_id),current.model_dump_json(by_alias=True),receipt.model_dump_json(by_alias=True),str(private)))
            paths[session_id]=path
            private_paths.append(private)
    return paths,private_paths
