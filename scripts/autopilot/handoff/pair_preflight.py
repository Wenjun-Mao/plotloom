"""Current-source checks for the migrated method; no alternate executable path."""
from copy import deepcopy
import hashlib
import json
import subprocess
from pathlib import Path

from handoff_files import require
from pair_context import current, assert_control_bytes, assert_origins


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source():
    context = current()
    assert_control_bytes()
    assert_origins()
    from preservation import require_preserved_inputs
    require_preserved_inputs()
    owner = context.allocation.source
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=context.source,text=True).strip()
    tree = subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=context.source,text=True).strip()
    dirty = subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=context.source,text=True)
    require(revision == owner.revision and tree == owner.tree and not dirty, 'pair source differs from committed allocation')
    from plotloom.codex_exec_python_environment import inspect_checked_python_environment
    require(inspect_checked_python_environment(context.source).identity_hash ==
        context.allocation.validator_runtime.identity_hash, 'pair checked validator identity differs')
    assert_origins()


def preflight_campaign():
    _source()
    context = current()
    work = context.campaign
    sealed = json.loads((work/'plan.json').read_bytes())
    require(sealed['order'] == ['serial','parallel'] and sealed['totalDispatchEnvelope'] == dict(text=18,image=64)
        and sealed['sourceRevision'] == context.allocation.source.revision, 'pair order/envelope/source differs')
    require(sha(work/'prepared_inputs.json') == sealed['preparedInputsSha256'], 'pair prepared inputs differ')
    prepared = json.loads((work/'prepared_inputs.json').read_bytes())
    from campaign_guard import profiles_differ_only_in_capacity, require_historical_material_and_current_absence
    plans = {}
    for arm in sealed['order']:
        plan = json.loads((work/arm/'plan.json').read_bytes())
        expected = deepcopy(prepared['arms'][arm]) | dict(sealedPlanSha256=sha(work/'plan.json'))
        require(plan == expected, 'pair arm differs from frozen author inputs')
        ns = getattr(context.allocation,arm).namespace
        require(plan['profile'] == ns.profile.model_dump(mode='json',by_alias=True)
            and plan['profileHash'] == ns.profile.profile_hash, 'pair arm profile differs')
        plans[arm] = plan
    profiles_differ_only_in_capacity(plans['serial']['profile'],plans['parallel']['profile'])
    require(sha(Path(plans['serial']['functionalProofRoot'])/'result.json') ==
        sealed['functionalResultSha256'], 'retained historical result differs')
    require_historical_material_and_current_absence(Path(plans['serial']['functionalProofRoot']))
    return sealed


def preflight_arm():
    _source()
    context = current()
    require(context.arm in {'serial','parallel'}, 'fixed arm context required')
    plan = json.loads((context.work/'plan.json').read_bytes())
    ns = getattr(context.allocation,context.arm).namespace
    require(plan['arm'] == context.arm and plan['status'] == 'prepared_no_launch'
        and plan['sourceRevision'] == context.allocation.source.revision
        and plan['profile'] == ns.profile.model_dump(mode='json',by_alias=True)
        and plan['primaryEnvelope'] == dict(text=8,image=32,completeAllRoutes=True)
        and plan['sidecarEnvelope'] == dict(text=1,image=0,pauseAfterOutlineAdmission=True)
        and (plan['maxWallSeconds'],plan['maxSettlementSeconds'],plan['maxSteps']) == (5400,600,10000),
        'arm method/profile/ceilings differ')
    for relative,digest in plan['priorEvidence'].items():
        require(sha(context.source/relative) == digest, 'retained arm evidence differs')
    return plan
