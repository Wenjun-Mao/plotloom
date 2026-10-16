"""Real project/host owners; test-owned metadata and no external worker dispatch."""
import stat
import subprocess
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_test_support import _write_fake_cli
from plotloom.autopilot_contracts import LaunchRequest,OperationScope
from plotloom.autopilot_exec_staged import reserve_prepared_codex_exec
from plotloom.autopilot_service import AutopilotService
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.codex_exec_qualification_contracts import CodexExecQualificationBinding, QualificationProject
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage
from plotloom.persistence.codec import stable_hash


def path_identity(path):
    path = path.resolve(strict=True)
    info = path.stat()
    return dict(path=str(path), device=info.st_dev, inode=info.st_ino,
        uid=info.st_uid, mode=stat.S_IMODE(info.st_mode))


@pytest.fixture
def finite(supervisor, tmp_path, monkeypatch):
    # This fixture prepares only Outline. The unused Bridge pin lookup requires
    # committed source; use existing upstream metadata for those unused slots,
    # without weakening the production gate or fabricating Bridge execution.
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    original_pin = CreativeHandoffExchange.current_execution_pin
    fixture_revision = subprocess.check_output(['git', '-C', str(supervisor.source_root), 'rev-parse', 'HEAD']).decode().strip()
    monkeypatch.setattr(CreativeHandoffExchange, 'current_execution_pin',
        lambda self, stage: (original_pin(self, 'outline') | {'upstreamRevision': fixture_revision}
            if stage in {'bridge-intent', 'bridge-presentation'} else original_pin(self, stage)))
    marker=tmp_path/'forbidden-native-marker'
    _write_fake_cli(supervisor, "from pathlib import Path\nPath("+repr(str(marker))+").write_text('forbidden native exec')\nraise SystemExit(19)\n")
    application = tmp_path / "application"
    application.mkdir(mode=0o700)
    supervisor.outputs_root.chmod(0o700)
    storage = ProjectFolderStorage(outputs_root=supervisor.outputs_root, application_data_root=application)
    controls = tmp_path / "controls"
    controls.mkdir(mode=0o700)
    raw = b'{"files":{}}\n'
    (controls / "pair-controls.json").write_bytes(raw)
    (controls / "pair-controls.json").chmod(0o600)
    private = tmp_path / "finite-private"
    limits = CodexExecPoolLimits(maxProcesses=4, maxTextProcesses=2, maxImageProcesses=2, maxQueuedJobs=4)
    kwargs = dict(source_root=supervisor.source_root, outputs_root=supervisor.outputs_root, private_root=private)
    empty = CodexExecSupervisor(supervisor.executable, pool_limits=limits, **kwargs)
    profile = empty.profile()
    git = lambda ref: subprocess.check_output(['git','-C',str(supervisor.source_root),'rev-parse',ref]).decode().strip()
    binding = CodexExecQualificationBinding(version="plotloom.exec-qualification-arm.v1",
        namespaceId=uuid4(), pairId=uuid4(), arm="parallel", applicationRoot=path_identity(application),
        applicationDatabase=path_identity(storage.application.path),
        outputsRoot=path_identity(supervisor.outputs_root), privateRoot=path_identity(private),
        sourceRoot=path_identity(supervisor.source_root), database=path_identity(empty.database),
        executable=path_identity(supervisor.executable) | dict(sha256=sha256(supervisor.executable.read_bytes()).hexdigest(), size=supervisor.executable.stat().st_size),
        controlsRoot=path_identity(controls), controlsSha256=sha256(raw).hexdigest(),
        sourceRevision=git('HEAD'), sourceTree=git('HEAD^{tree}'), qaPinSha256='a'*64,
        checkedValidatorIdentity='b'*64, profile=profile, limits=limits)
    raw = binding.model_dump_json(by_alias=True).encode()
    (private / "namespace-binding.json").write_bytes(raw)
    (private / "namespace-binding.json").chmod(0o600)
    kwargs['namespace_binding_sha256'] = sha256(raw).hexdigest()
    host = CodexExecSupervisor(supervisor.executable, **kwargs)
    starts = []
    monkeypatch.setattr(host, '_start_worker', starts.append)
    registry = SimpleNamespace(codex_exec_profile=host.profile,
        require_codex_exec_readiness=lambda: None, codex_exec_admit=host.admit,
        codex_exec_status=host.status, codex_exec_suspend=host.suspend)
    service = AutopilotService(storage, registry)
    assert service.acquire_controller()
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
    service.launch(project_id, LaunchRequest(expectedBriefRevision=1, renderStyle='realistic',
        artRenderStyle='realistic', maxImages=32, maxJobs=40))
    with closing(storage.projects.open(project_id)) as store:
        view = store.repository.autopilot.claim(project_id, service.claim)
        assert view.policy.code_revision == binding.source_revision
        home = storage.projects._project_home(project_id).path
        registration = QualificationProject(role='primary', projectId=project_id, runId=view.id,
            claim=service.claim, home=path_identity(home), database=path_identity(home/'project.sqlite3'),
            manifestSha256=sha256((home/'project.json').read_bytes()).hexdigest(),
            policyHash=stable_hash(view.policy.model_dump(mode='json', by_alias=True)))
    host.register_qualification_project(registration)
    activation = host.activate_qualification(prior_serial_receipt_sha256='c'*64)
    service.step(project_id)
    service.step(project_id)
    with closing(storage.projects.open(project_id)) as store:
        view = store.repository.autopilot.current(project_id)
        checkpoint = next(item for item in view.checkpoints if item['operationKey']=='outline')
        package = store.creative_handoff_exchange().root/'jobs'/checkpoint['evidence']['jobId']/'package'
        attempt = reserve_prepared_codex_exec(store, registry, view, service.claim, checkpoint,
            domain='text', package_path=str(package), command_factory=service.controller.command)
        view=store.repository.autopilot.current(project_id)
        checkpoint=next(item for item in view.checkpoints if item['operationKey']=='outline')
        with service.controller.command(store,view,service.claim,OperationScope.TEXT):
            store.repository.autopilot.consume_reserved_exec_attempt_once(attempt,
                expected_checkpoint_revision=checkpoint['revision'],expected_run_revision=view.revision)
    try:
        yield SimpleNamespace(host=host, kwargs=kwargs, binding=binding, registration=registration,
            activation=activation, attempt=attempt, storage=storage, service=service, starts=starts,
            native_marker=marker)
    finally:
        service.close()
