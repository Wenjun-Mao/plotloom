"""Pure acceptance measurements exclude raw evidence and honor whole-stage credit."""
from copy import deepcopy
from types import SimpleNamespace as NS

from plotloom.acceptance_metrics import (
    first_pass_stats, maximum_attempts_per_work_unit, public_token_usage, stable_issue_codes,
)
from plotloom.artifact_contracts import ArtifactKind
from plotloom.run_contracts import AttemptStatus, GenerationAttemptKind
from plotloom.stage_contracts import STAGE_ORDER
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.generation.prompts import canonical_json, sha256_text


def attempt(unit, status, *, unknown=False, kind=GenerationAttemptKind.PRIMARY, code=None):
    return NS(work_unit_id=unit, status=status, outcome_unknown=unknown,
              attempt_kind=kind, outcome_code=code)


def test_public_metrics_ignore_malformed_usage_and_private_issue_text_without_mutation():
    trace = NS(artifacts=[
        NS(kind=ArtifactKind.RESPONSE, content={'usage': {'inputTokens': 5, 'outputTokens': 8}}),
        NS(kind=ArtifactKind.RESPONSE, content={'usage': {'inputTokens': True, 'outputTokens': -1}}),
        NS(kind=ArtifactKind.RESPONSE, content={'usage': {'inputTokens': '99', 'outputTokens': 2.5}}),
        NS(kind=ArtifactKind.RESPONSE, content={'usage': []}),
        NS(kind=ArtifactKind.RESPONSE, content=['private response']),
        NS(kind=ArtifactKind.VALIDATION, content={'issues': [
            {'code': 'schema.shape', 'message': 'private prompt'}, {'code': 'private token text'},
            {'code': 'schema.shape'}, {'code': 4}, None]}),
    ], attempts=[
        attempt(None, AttemptStatus.FAILED, code='provider.timeout'),
        attempt(None, AttemptStatus.FAILED, code='contract.shape'),
        attempt(None, AttemptStatus.FAILED, code='private.provider_message'),
        attempt(None, AttemptStatus.SUCCEEDED, code='provider.ignored'),
    ])
    before = deepcopy(trace)
    assert public_token_usage(trace) == {'inputTokens': 5, 'outputTokens': 8, 'totalTokens': 13}
    assert stable_issue_codes(trace) == {'schema.shape', 'provider.timeout', 'contract.shape'}
    assert trace == before


def test_first_pass_requires_all_units_and_keeps_unknown_rejection_cancellation_priority():
    stages = STAGE_ORDER
    execution = NS(work_units=[NS(id=name, stage=stage) for stage, names in zip(
        stages, [('a', 'b'), ('c',), ('d',), ('e',)], strict=True) for name in names])
    trace = NS(attempts=[
        attempt('a', AttemptStatus.SUCCEEDED), attempt('b', AttemptStatus.FAILED),
        attempt('b', AttemptStatus.SUCCEEDED, kind=GenerationAttemptKind.CORRECTION),
        attempt('c', AttemptStatus.FAILED, unknown=True), attempt('c', AttemptStatus.CANCELLED),
        attempt('d', AttemptStatus.CANCELLED), attempt(None, AttemptStatus.SUCCEEDED),
    ])
    before = deepcopy((execution, trace))
    assert first_pass_stats(execution, trace, stage_order=stages) == {
        'total': 4, 'accepted': 0, 'rejected': 1, 'outcomeUnknown': 1, 'cancelled': 1, 'notRun': 1}
    assert maximum_attempts_per_work_unit(trace) == 2
    assert (execution, trace) == before
    # Missing primary for a sharded stage gets no credit, even when its sibling succeeds.
    assert first_pass_stats(execution, NS(attempts=[attempt('a', AttemptStatus.SUCCEEDED)]),
                            stage_order=stages)['accepted'] == 0
    assert maximum_attempts_per_work_unit(NS(attempts=[])) == 0


def test_fixed_story_workload_retains_exact_pre_move_canonical_hash():
    assert sha256_text(canonical_json(FIXED_CHINESE_BRIEF.model_dump(mode='json', by_alias=True))) == (
        '3c20eaf89fedefd724d78828e804b89a5bb7af392b08b6fba95f8b00fcb5368b')
