"""Prepare one fresh disposable Outline reservation; never dispatch or seal it."""
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from handoff_files import canonical, digest, exclusive_bytes, owned_root, require
from handoff_source import require_committed_profile_sources, source_identity
from paid_outline_composition import compose_registry
from paid_outline_contracts import PaidOutlineAllocation
from paid_outline_state import checkpoint_for, path_identity

from plotloom.autopilot_contracts import OperationScope, RunControlRequest
from plotloom.autopilot_exec_staged import reserve_prepared_codex_exec
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_controller import AutopilotTextController
from plotloom.autopilot_text_stages import (
    adopt_brief_source,
    native_checkpoint_evidence,
    prepare_text,
)
from plotloom.codex_exec_namespace_contracts import CodexExecNamespaceBinding
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.codex_exec_python_environment import inspect_checked_python_environment
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.format import PROJECT_MANIFEST_FILENAME


def prepare_outline_allocation(*, data_root, bundle_root, phase_root, source_root, executable,
        qa, qa_pin_sha256, brief, launch_request):
    """Return immutable DATA for later independent approval, not launch authority.

    All roots and inputs must be concretely allocated by the caller. No defaults
    select operator state, a project, budget, model or execution permission.
    """
    data, bundle, phase = (owned_root(value) for value in (data_root, bundle_root, phase_root))
    require(all(not list(value.iterdir()) for value in (data, bundle, phase)), "preparer requires fresh empty roots")
    require(all(a != b and a not in b.parents and b not in a.parents
        for a, b in ((data, bundle), (data, phase), (bundle, phase))), "allocation roots overlap")
    source_root = Path(source_root).resolve(strict=True)
    require(qa["projectRoot"] == str(source_root), "QA project root differs from owner source")
    require(type(qa_pin_sha256) is str and len(qa_pin_sha256) == 64
        and all(char in "0123456789abcdef" for char in qa_pin_sha256), "explicit QA file pin required")
    owner_source = source_identity(source_root, require_committed=True)
    require_committed_profile_sources(source_root)
    runtime = inspect_checked_python_environment(source_root)
    require(str(runtime.root) != qa["prefix"] and str(runtime.interpreter) != qa["entrypoint"],
        "QA cannot substitute for checked validator environment")
    allocation_id = uuid4()
    nonce = "paid-outline-" + allocation_id.hex
    exclusive_bytes(data, "owner.json", canonical({"version": 1, "purpose": "paid_outline_once",
        "allocationId": str(allocation_id), "nonce": nonce}))
    for name in ("outputs", "application", "private"):
        (data / name).mkdir(mode=0o700)
    limits = CodexExecPoolLimits(maxProcesses=1, maxTextProcesses=1, maxImageProcesses=1, maxQueuedJobs=1)
    registry = compose_registry(source_root, executable, data / "application", data / "outputs", data / "private", limits=limits)
    profile = registry.codex_exec_profile()
    storage = ProjectFolderStorage(outputs_root=data / "outputs", application_data_root=data / "application")
    service = AutopilotService(storage, registry)
    try:
        require(service.acquire_controller(), "disposable controller lease unavailable")
        with closing(storage.projects.create(brief)) as store:
            project_id = store.manifest.project_id
            home, project_database = store.home, store.database_path
        view = service.launch(project_id, launch_request)
        with closing(storage.projects.open(project_id)) as store:
            view = store.repository.autopilot.claim(project_id, service.claim)
            command = AutopilotTextController.command
            # Exact owner calls for this fresh state. No general advance/step
            # can dispatch a later stage, even if a precondition changes.
            require(not view.checkpoints and view.phase == "source", "fresh run is not at source")
            with command(store, view, service.claim, OperationScope.SOURCE):
                adopt_brief_source(store)
                store.repository.autopilot.progress("outline")
            view = store.repository.autopilot.current(project_id)
            with command(store, view, service.claim, OperationScope.TEXT):
                request = prepare_text(store, "outline", view.policy)
                evidence = native_checkpoint_evidence(store, request)
                require(evidence.execution_pin == view.policy.execution_pins["outline"], "prepared Outline pin changed")
                store.repository.autopilot.checkpoint("outline", state="prepared", evidence=evidence)
                store.repository.autopilot.progress("outline")
            paths = store.creative_handoff_exchange().write_package(request, evidence.execution_pin,
                executor_backend="codex_exec", plotloom_code_revision=view.policy.code_revision)
            view = store.repository.autopilot.current(project_id)
            attempt = reserve_prepared_codex_exec(store, registry, view, service.claim, checkpoint_for(view),
                domain="text", package_path=paths["packagePath"], command_factory=command)
            view = store.repository.autopilot.current(project_id)
            paused = service.control(project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
            checkpoint = checkpoint_for(paused)
            with store.repository.autopilot.access.leases.read() as session:
                row = store.repository.autopilot.row(session, project_id)
                frozen = {"policyHash": row.policy_hash, "briefHash": row.brief_hash,
                    "materialClosure": row.expected_closure, "briefRevision": row.brief_revision,
                    "lifecycleRevision": row.lifecycle_revision}
        require({entry.path for entry in storage.projects.discover()} == {home}, "preparer catalog is not allocation-only")
        namespace = CodexExecNamespaceBinding(version="plotloom.exec-one-attempt.v1", namespaceId=allocation_id,
            applicationRoot=path_identity(data / "application"), outputsRoot=path_identity(data / "outputs"),
            privateRoot=path_identity(data / "private"), sourceRoot=path_identity(source_root),
            database=path_identity(registry.bridge.exec_supervisor().database),
            executable=path_identity(executable) | {"sha256": profile.executable_sha256, "size": Path(executable).stat().st_size},
            profile=profile, limits=limits, attempt=attempt)
        namespace_bytes = canonical(namespace.model_dump(mode="json", by_alias=True))
        exclusive_bytes(data / "private", "namespace-binding.json", namespace_bytes)
        receiver_claim = uuid4().hex
        allocation = PaidOutlineAllocation(version="plotloom.paid-outline-once.v1", authority="paid_outline_once",
            allocationId=allocation_id, nonce=nonce, dataRoot=path_identity(data),
            ownerMarker=path_identity(data / "owner.json", file_hash=True), bundleRoot=path_identity(bundle),
            phaseRoot=path_identity(phase), projectHome=path_identity(home),
            projectManifest=path_identity(home / PROJECT_MANIFEST_FILENAME, file_hash=True),
            projectDatabase=path_identity(project_database), applicationDatabase=path_identity(storage.application.path),
            namespace=namespace, namespaceBindingSha256=digest(namespace_bytes),
            source={"revision": owner_source["revision"], "tree": owner_source["tree"],
                "workflowClosureSha256": owner_source["closureSha256"], "bundleSourceIdentitySha256": digest(canonical(owner_source))},
            validatorRuntime={"root": str(runtime.root), "interpreter": str(runtime.interpreter),
                "identityHash": runtime.identity_hash, "qaPinSha256": qa_pin_sha256},
            claimEdges={"pausedClaim": service.claim, "receiverClaim": receiver_claim,
                "pausedRevision": paused.revision, "claimedRevision": paused.revision + 1,
                "resumedRevision": paused.revision + 2}, expectedCheckpointRevision=checkpoint["revision"],
            applicationEntries=tuple(sorted(p.name for p in storage.application.root.iterdir())),
            initialAdmissions=1, imageAdmissions=0, retries=0, settlementAuthority="hold_only",
            canonicalAdoption=False, laterStages=False, **frozen)
        return allocation
    finally:
        service.close()
