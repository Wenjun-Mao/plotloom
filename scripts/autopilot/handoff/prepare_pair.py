"""Offline refresh of the authored pair; no project creation or dispatch here."""
import json
import secrets
import subprocess
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from handoff_files import canonical, exclusive_bytes, owned_root, require
from handoff_source import source_identity, require_committed_profile_sources
from paid_outline_contracts import PaidFileIdentity, PaidSourceIdentity, PaidValidatorRuntime
from paid_outline_state import path_identity
from pair_contracts import PairArmAllocation, QualificationPairAllocation
from plotloom.codex_exec_namespace_contracts import ExecNamespaceExecutable
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.codex_exec_qualification_contracts import CodexExecQualificationBinding


def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def file_identity(path):
    return PaidFileIdentity(**path_identity(path), sha256=sha(path), size=path.stat().st_size)


def prepare(*, source_root, work_root, bundle_root, phase_root, executable, qa_bytes,
        author_inputs, preservation_bytes, historical_context, functional_proof_root):
    """Refresh explicit frozen author/evidence DATA in caller-allocated roots.

    Retain per-arm preparation/seal; never read old executable controls or copy
    an installation. This function does not create projects, call readiness or
    start workers. A separate release owns every actual invocation.
    """
    source = Path(source_root).resolve(strict=True)
    work, bundle, phase = map(owned_root, (work_root, bundle_root, phase_root))
    require(all(not list(root.iterdir()) for root in (work, bundle, phase)), "pair preparation requires empty allocated roots")
    require(all(a!=b and a not in b.parents and b not in a.parents for i,a in enumerate((work,bundle,phase))
        for b in (work,bundle,phase)[i+1:]),'pair allocation roots overlap')
    qa = json.loads(qa_bytes)
    require(qa['projectRoot'] == str(source), "pair QA source differs")
    owner = source_identity(source, require_committed=True)
    require_committed_profile_sources(source)
    from plotloom.codex_exec_python_environment import inspect_checked_python_environment
    checked = inspect_checked_python_environment(source)
    require(str(checked.root) != qa['prefix'], "pair QA cannot substitute for checked validator")
    import sys
    sys.path.insert(0,str(source/'scripts/autopilot'))
    import handoff_bundle
    require(Path(handoff_bundle.__file__).resolve()==source/'scripts/autopilot/handoff_bundle.py', 'offline builder import origin differs')
    contents, _inputs = handoff_bundle.bound_sources(bundle, qa_bytes=qa_bytes)
    code_controls = handoff_bundle.pair_code_controls(contents)
    pair_id = uuid4()
    nonce = 'qualification-pair-' + pair_id.hex
    exclusive_bytes(work, 'owner.json', canonical(dict(allocationId=str(pair_id), nonce=nonce)))
    exclusive_bytes(work, 'preservation_inputs.json', preservation_bytes)
    context = {key: historical_context[key] for key in ('historicalSourceRevision',
        'historicalHashManifest', 'historicalHashManifestSha256', 'qualifiedCurrentEvidence')}
    from plotloom.codex_exec_profile import INSTRUCTION_FILES, VALIDATOR_FILES
    inputs = set(INSTRUCTION_FILES) | set(VALIDATOR_FILES) | set(owner['files'])
    inputs.update(str(path.relative_to(source)) for path in (source/'src/plotloom').rglob('*.py'))
    context.update(sourceRevision=owner['revision'], sourceTree=owner['tree'],
        currentSourceInputs={name:sha(source/name) for name in sorted(inputs)},
        historicalDescriptor='preservation_inputs.json', historicalDescriptorSha256=sha(work/'preservation_inputs.json'),
        cli=dict(path=str(executable), sha256=sha(executable)))
    exclusive_bytes(work, 'current_source.json', canonical(context))
    require(author_inputs['launchRequest'] == dict(expectedBriefRevision=1, styleAuthority='brief', maxImages=32, maxJobs=40),
        "pair launch must retain authored Brief authority and finite budgets")
    require(set(author_inputs)=={'brief','launchRequest','priorEvidence'},'pair author input fields differ')
    from plotloom.api.contracts import ProjectCreateRequest
    ProjectCreateRequest(brief=author_inputs['brief'],initialStages=[])
    namespaces, plans = {}, {}
    from codex_exec_supervisor import CodexExecSupervisor
    for arm, capacities in (('serial',(1,1,1)),('parallel',(4,2,2))):
        target = work/arm
        target.mkdir(mode=0o700)
        for name in ('installation','installation/outputs','installation/application','private'):
            (target/name).mkdir(mode=0o700)
        exclusive_bytes(target/'private', 'bridge-token', secrets.token_hex(32).encode())
        from plotloom.project_storage import ProjectFolderStorage
        storage = ProjectFolderStorage(outputs_root=target/'installation/outputs', application_data_root=target/'installation/application')
        limits = CodexExecPoolLimits(**dict(zip(('maxProcesses','maxTextProcesses','maxImageProcesses'),capacities)), maxQueuedJobs=4)
        host = CodexExecSupervisor(Path(executable), source_root=source, outputs_root=target/'installation/outputs',
            private_root=target/'private/codex-exec', pool_limits=limits)
        profile = host.profile()
        ns = CodexExecQualificationBinding(version='plotloom.exec-qualification-arm.v1',
            namespaceId=uuid4(), pairId=pair_id, arm=arm, applicationRoot=path_identity(target/'installation/application'),
            applicationDatabase=path_identity(storage.application.path),
            outputsRoot=path_identity(host.outputs_root), privateRoot=path_identity(host.private_root),
            sourceRoot=path_identity(source), database=path_identity(host.database),
            executable=ExecNamespaceExecutable(**path_identity(Path(executable)), sha256=sha(executable), size=Path(executable).stat().st_size),
            controlsRoot=path_identity(bundle), controlsSha256=sha256(code_controls).hexdigest(),
            sourceRevision=owner['revision'], sourceTree=owner['tree'], qaPinSha256=sha256(qa_bytes).hexdigest(),
            checkedValidatorIdentity=checked.identity_hash, profile=profile, limits=limits)
        pin = exclusive_bytes(host.private_root, 'namespace-binding.json', canonical(ns.model_dump(mode='json',by_alias=True)))
        namespaces[arm] = PairArmAllocation(workRoot=path_identity(target), namespace=ns, namespaceBindingSha256=pin)
        plan = {key: author_inputs[key] for key in ('brief','launchRequest','priorEvidence')}
        plan.update(sourceRevision=owner['revision'], status='prepared_no_launch', arm=arm,
            submodule=subprocess.check_output(['git','-C',str(source/'third_party/shuohao-skills'),'rev-parse','HEAD']).decode().strip(),
            checkedPythonEnvironmentIdentity=checked.identity_hash, cliExecutable=str(executable),
            profile=profile.model_dump(mode='json',by_alias=True), profileHash=profile.profile_hash,
            functionalProofRoot=str(functional_proof_root), projectIdempotency={role:str(uuid4()) for role in ('primary','sidecar')},
            primaryEnvelope=dict(text=8,image=32,completeAllRoutes=True),
            sidecarEnvelope=dict(text=1,image=0,pauseAfterOutlineAdmission=True),
            maxWallSeconds=5400,maxSettlementSeconds=600,maxSteps=10000,
            performanceQualification=False, experiment='author-input-matched observational single pair')
        plans[arm] = plan
    exclusive_bytes(work,'prepared_inputs.json',canonical(dict(sourceRevision=owner['revision'],arms=plans,generationDispatches=0)))
    sealed = dict(sourceRevision=owner['revision'], preparedInputsSha256=sha(work/'prepared_inputs.json'),
        profiles={arm:plan['profileHash'] for arm,plan in plans.items()},
        functionalResultSha256=sha(Path(functional_proof_root)/'result.json'),
        order=['serial','parallel'], totalDispatchEnvelope=dict(text=18,image=64),
        analysisSha256=sha(source/'scripts/autopilot/handoff/analyze_pair.py'),
        sessionMeasurementSha256=sha(source/'scripts/autopilot/handoff/session_measurements.py'),
        captureOnly=True,generationDispatches=0)
    exclusive_bytes(work,'plan.json',canonical(sealed))
    for arm, plan in plans.items():
        exclusive_bytes(work/arm,'plan.json',canonical(plan | dict(sealedPlanSha256=sha(work/'plan.json'))))
    data_paths=[work/name for name in ('plan.json','prepared_inputs.json','preservation_inputs.json','current_source.json')]
    data_paths.extend(work/arm/'plan.json' for arm in ('serial','parallel'))
    return QualificationPairAllocation(version='plotloom.qualification-pair-once.v1',authority='qualification_pair_once',
        allocationId=pair_id,nonce=nonce,workRoot=path_identity(work),bundleRoot=path_identity(bundle),phaseRoot=path_identity(phase),
        ownerMarker=file_identity(work/'owner.json'),
        source=PaidSourceIdentity(revision=owner['revision'],tree=owner['tree'],workflowClosureSha256=owner['closureSha256'],
            bundleSourceIdentitySha256=sha256(contents['source-identity.json']).hexdigest()),
        validatorRuntime=PaidValidatorRuntime(root=str(checked.root),interpreter=str(checked.interpreter),
            identityHash=checked.identity_hash,qaPinSha256=sha256(qa_bytes).hexdigest()),
        inputs=tuple(file_identity(path) for path in data_paths), serial=namespaces['serial'],parallel=namespaces['parallel'])
