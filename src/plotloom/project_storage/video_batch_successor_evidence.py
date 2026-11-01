"""Read-time consistency for immutable corrected-source predecessor links."""
import json

from ..persistence.codec import stable_hash


def validate_successor_links(connection):
    rows = {row[0]: row for row in connection.execute(
        'SELECT id,project_id,state,manifest,execution FROM v2_video_batches')}
    for identifier, project_id, state, raw_manifest, raw_execution in rows.values():
        execution = json.loads(raw_execution)
        link = execution.get('correctedSourcePredecessor')
        back = execution.get('correctedSourceSuccessor')
        if back:
            target = rows.get(back.get('batchId'))
            retained = json.loads(target[4]).get('correctedSourcePredecessor') if target else None
            if (state != 'cancelled' or not retained or retained.get('batchId') != identifier
                    or back != {key: retained[key] for key in ('commandId','requestHash')} | {'batchId':target[0]}):
                raise ValueError('corrected-source successor backlink changed')
        if not link:
            continue
        from ..video_batch_successor import CorrectedSourceSuccessor, assert_corrected_manifest, same_execution_envelope
        from ..codex_exec_contracts import CodexExecAttempt, CodexExecProfile
        command = CorrectedSourceSuccessor.model_validate(link['request'])
        old = rows.get(str(command.predecessor_batch_id))
        if not old or old[1] != project_id or old[2] != 'cancelled':
            raise ValueError('corrected-source predecessor changed')
        previous, manifest = json.loads(old[4]), json.loads(raw_manifest)
        original = json.loads(old[3])
        assert_corrected_manifest(original, manifest)
        key = command.setup.single_request.idempotency_key
        for other_id, other in rows.items():
            other_setup = json.loads(other[3])['setup'].get('singleRequest')
            if other_id != identifier and other[1] == project_id and other_setup and other_setup['idempotencyKey'] == key:
                raise ValueError('corrected-source request identity belongs to another batch')
        for job_id, raw in connection.execute('SELECT id,snapshot FROM v2_video_jobs WHERE project_id=? AND idempotency_key=?',(project_id,key)):
            snapshot=json.loads(raw)
            basis=(snapshot.get('reviewedDirections') or {}).get('reviewBasis') or {}
            frozen={name:value for name,value in snapshot.items() if name not in {'reviewedDirections','compiledPrompt'}}
            # Native preparation commits its exact job before the batch attaches
            # the returned ID. That endorsed intermediate state must reopen.
            if (basis.get('batchId') != identifier or basis.get('manifestHash') != stable_hash(manifest)
                    or execution.get('authorizedManifestHash') != stable_hash(manifest)
                    or frozen != manifest['targets'][0]['snapshot']
                    or execution['jobs'] and job_id not in execution['jobs'].values()):
                raise ValueError('corrected-source request identity belongs to another video job')
        attempt = CodexExecAttempt.model_validate(link['attempt'])
        active = [previous[key] for key in ('draft','fidelity') if previous.get(key)]
        profile = CodexExecProfile.model_validate(link['executionProfile'])
        if (profile.profile_hash != command.expected_execution_profile_hash
                or any(not same_execution_envelope(data['profile'],link['executionProfile']) for data in active)
                or any(execution[key]['profile'] != link['executionProfile'] for key in ('draft','fidelity') if execution.get(key))):
            raise ValueError('corrected-source execution envelope changed')
        if (previous.get('authorizedManifestHash') or previous.get('jobs') or previous.get('segments')
                or not active or active[-1]['attempt'] != link['attempt']
                or attempt.state != 'outcome_unknown' or attempt.execution_failure != 'cancelled'
                or attempt.domain != 'text' or attempt.reserved_image_outputs or attempt.image_budget_state != 'none'
                or str(attempt.project_id) != project_id or str(attempt.run_id) != old[0]
                or attempt.attempt_id != command.predecessor_attempt_id or attempt.job_id != command.predecessor_job_id
                or link['batchId'] != old[0] or link['revision'] != command.expected_revision
                or link['commandId'] != str(command.command_id)
                or link['requestHash'] != stable_hash(command.model_dump(mode='json',by_alias=True))
                or link['nativeLocalExecutionStopped'] is not True or link['possiblePriorCost'] is not True
                or previous.get('correctedSourceSuccessor') != {'batchId':identifier,'commandId':link['commandId'],'requestHash':link['requestHash']}
                or manifest['setup'] != command.setup.model_dump(mode='json',by_alias=True)
                or stable_hash(manifest['sourceBinding']) != command.expected_source_hash
                or original['scopeShotIds'] != manifest['scopeShotIds']
                or len(original['targets']) != 1 or len(manifest['targets']) != 1
                or link['oldSourceHash'] != original['targets'][0]['sourceHash']
                or link['newSourceHash'] != manifest['targets'][0]['sourceHash']
                or link['oldSourceHash'] == link['newSourceHash']):
            raise ValueError('corrected-source immutable predecessor evidence changed')
