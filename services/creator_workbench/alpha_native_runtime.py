"""Source-owned native Alpha composition over the existing isolated workbench."""
import argparse
import json
import time
from contextlib import closing, contextmanager
from pathlib import Path
from threading import Thread
from urllib.request import ProxyHandler, build_opener

import uvicorn
from isolated import RuntimeConfig, compose

from plotloom.alpha_campaign import campaign_lease, load_campaign, private_directory, write_private_json, publish_sample_outcome
from plotloom.alpha_publication import content_only_review_payload
from plotloom.alpha_pause import (QualificationResume, database_identity, pause_directories,
    pause_snapshot, publish_pause, recorded_duration, require_original_runtime, resume_paused_sample)
from plotloom.alpha_receipts import collect_native_evidence, installed_text_readback
from plotloom.autopilot_contracts import LaunchRequest, RunControlRequest
from plotloom.autopilot_text_prefix import AutopilotTextPrefix


@contextmanager
def serving(runtime):
    """Stop the ordinary runtime before the prefix process lease is released."""
    server = uvicorn.Server(uvicorn.Config(runtime.app, log_level="error", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [runtime.socket]}, daemon=True)
    thread.start()
    try:
        while not server.started:
            if not thread.is_alive():
                raise RuntimeError("isolated workbench did not start")
            time.sleep(0.05)
        yield
    finally:
        server.should_exit = True
        thread.join()


def read_http(url):
    with build_opener(ProxyHandler({})).open(url, timeout=30) as response:
        return json.load(response)


def run_sample(work_root, sample_id, *, cancel=False, resume=None):
    """Advance one predeclared cell only; restarting observes its original IDs."""
    root = Path(work_root)
    with campaign_lease(root):
        campaign = load_campaign(root, check_source=True)
        sample = next((s for s in campaign.samples if s.sample_id == sample_id), None)
        if sample is None:
            raise ValueError("sample is outside the frozen native matrix")
        evidence = private_directory(root / "evidence" / sample_id, create=True)
        reserved = [evidence / name for name in ("outcome", "cancellation", "pauses", "resumptions", "runtime.json")]
        reserved.append(root / "private/runtime.json")
        if any(path.is_symlink() for path in reserved):
            raise ValueError("reserved qualification evidence cannot be an alias")
        receipt_file = evidence / "outcome/receipt.json"
        if receipt_file.exists() and not cancel:
            raise ValueError("sample already has an outcome; inspect it instead of repeating native work")
        if (evidence / "cancellation").exists():
            raise ValueError("sample has cancellation evidence; do not repeat native work")
        runtime_file = evidence / "runtime.json"
        original = require_original_runtime(evidence) if runtime_file.exists() else None
        campaign_runtime = root / "private/runtime.json"
        original_campaign = require_original_runtime(root / "private") if campaign_runtime.exists() else None
        if original_campaign is None and ((root / "private/codex-exec").exists()
                or any((root / "data/application").iterdir())):
            raise ValueError("existing campaign state has no original runtime incarnation")
        if (resume is not None or pause_directories(evidence)) and original is None:
            raise ValueError("paused sample has no original runtime identity")
        if resume is not None and str(resume.project_id) != str(sample.project_id):
            raise ValueError("resume project differs from the frozen sample")
        config = RuntimeConfig(Path(campaign.data_root), Path(campaign.source["sourceRoot"]) / "src/plotloom/static",
            Path(campaign.source["cliPath"]), Path(campaign.token_file), 0, 0,
            pool_limits=campaign.pool_limits)
        started = time.monotonic()
        with compose(config) as runtime:
            storage = runtime.app.state.project_folder_storage
            registry = runtime.app.state.specialists
            supervisor = runtime.bridge.exec_supervisor()
            if supervisor.profile().profile_hash != campaign.source["profileHash"]:
                raise ValueError("actual isolated supervisor profile differs from the frozen campaign")
            capacity = supervisor.local_capacity_readiness()
            if capacity.image_lane_blocked:
                raise ValueError("actual isolated image admission prerequisite is blocked")
            identity = {
                "dataRoot": str(config.data_root), "privateRoot": str(supervisor.private_root),
                "namespaceBinding": supervisor._namespace_sha256,
                "profileHash": supervisor.profile().profile_hash,
                "commit": campaign.source["commit"], "contractHash": campaign.contract_hash,
                "databases": {"supervisor": database_identity(supervisor.database),
                    "application": database_identity(storage.application.path)}}
            if original_campaign is not None:
                if original_campaign != identity:
                    raise ValueError("campaign runtime namespace or database identity changed")
            else:
                write_private_json(campaign_runtime, identity)
            # Independent service instance takes the production lease before the
            # ordinary app lifespan starts its background controller.
            with AutopilotTextPrefix(storage, registry) as prefix, serving(runtime):
                assert read_http(runtime.url + "/healthz") == {"status": "ok"}
                project_id = str(sample.project_id)
                homes = {h.manifest.project_id for h in storage.projects.discover(passive=True)}
                if project_id not in homes:
                    if cancel or resume is not None or original is not None:
                        raise ValueError("original sample project is missing; do not recreate it")
                    with closing(storage.projects.create(sample.brief, project_id=project_id)):
                        pass
                with closing(storage.projects.open(project_id)) as store:
                    identity["databases"]["project"] = database_identity(store.database_path)
                    if store.project().require_brief() != sample.brief:
                        raise ValueError("saved native sample Brief differs from the frozen workload")
                    view = store.repository.autopilot.current(project_id)
                if original is not None:
                    if original != identity:
                        raise ValueError("native runtime namespace or database identity changed")
                else:
                    if view is not None:
                        raise ValueError("existing run has no retained original runtime identity")
                    write_private_json(runtime_file, identity)
                print(json.dumps({"sampleId": sample_id, "workbench": runtime.url,
                    "bridge": runtime.bridge_url, "runtimeIdentity": str(runtime_file)}), flush=True)
                if view is None:
                    if resume is not None:
                        raise ValueError("resume cannot launch a missing original run")
                    view = prefix.launch(project_id, LaunchRequest(expected_brief_revision=1, style_authority="brief"))
                if (view.policy.executor_binding.profile_hash != campaign.source["profileHash"]
                        or view.policy.code_revision != campaign.source["commit"]
                        or view.policy.text_correction_limit != 1
                        or view.policy.execution_pins != campaign.source["executionPins"] | {"image": campaign.source["imagePin"]}):
                    raise ValueError("saved launch differs from the frozen native execution policy")
                pauses = pause_directories(evidence)
                if resume is not None:
                    view = resume_paused_sample(prefix, project_id, evidence, resume, identity)
                elif pauses and not cancel:
                    values, digest = pause_snapshot(pauses[-1])
                    saved = values["bindings.private.json"]["run"]
                    if view.state != "paused" or (view.id, view.revision) != (saved["id"], saved["revision"]):
                        raise ValueError("paused sample requires its explicit exact resume request")
                    print(json.dumps({"sampleId": sample_id, "status": "paused", "runId": view.id,
                        "revision": view.revision, "pauseHash": digest}), flush=True)
                    return 3
                if cancel:
                    view = prefix.service.control(project_id,
                        RunControlRequest(action="cancel", expected_revision=view.revision), expected_run_id=view.id)
                elapsed_before = recorded_duration(evidence)
                previous = None
                while True:
                    view = prefix.step(project_id)
                    progress = (view.phase, view.state, tuple((c["operationKey"], c["state"]) for c in view.checkpoints))
                    if progress != previous:
                        print(json.dumps({"sampleId": sample_id, "phase": view.phase, "state": view.state,
                            "checkpoints": progress[2]}), flush=True)
                        previous = progress
                    if (any(c["operationKey"] == "installation" for c in view.checkpoints)
                            or view.state not in {"running", "waiting"}
                            or any(c["state"] == "outcome_unknown" for c in view.checkpoints)):
                        break
                    time.sleep(1)
                # This pause preserves all original reservations and prevents any
                # future ordinary controller from acquiring image work on reopen.
                prefix.pause(project_id)
                with closing(storage.projects.open(project_id)) as store:
                    view = store.repository.autopilot.current(project_id)
                    elapsed_ms = round((time.monotonic() - started) * 1000)
                    receipt, private = collect_native_evidence(store, view, snapshot=campaign.source,
                        contract_hash=campaign.contract_hash, sample_id=sample_id,
                        duration_ms=elapsed_before + elapsed_ms)
                    content = content_only_review_payload(store) if receipt.status == "installed" else None
                if receipt.status == "installed":
                    # Fresh ProjectStore plus real API readback: no stale in-memory
                    # installation object is accepted as persistence evidence.
                    with closing(storage.projects.open(project_id)) as reopened:
                        if installed_text_readback(reopened) != private["readback"]:
                            raise ValueError("native installed text changed on reopen")
                    response = read_http(runtime.url + f"/api/v2/projects/{project_id}/production-bridge")
                    if response["installation"]["status"] != "current":
                        raise ValueError("native installation is not current through the workbench API")
                    private["apiInstallation"] = response["installation"]
                if receipt.status == "incomplete" and view.state == "paused" and not cancel:
                    _path, digest = publish_pause(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
                        bindings=private, runtime_identity=identity, elapsed_ms=elapsed_ms)
                    print(json.dumps({"sampleId": sample_id, "status": "paused", "runId": view.id,
                        "revision": view.revision, "pauseHash": digest}), flush=True)
                    return 3
                publish_sample_outcome(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
                    bindings=private, content=content, cancellation=cancel)
                print(json.dumps({"sampleId": sample_id, "status": receipt.status,
                    "firstPass": sum(op.first_pass for op in receipt.operations)}), flush=True)
                return 0 if receipt.status == "installed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--cancel", action="store_true", help="Cancel only this exact predeclared disposable sample")
    parser.add_argument("--resume-project")
    parser.add_argument("--resume-run")
    parser.add_argument("--resume-revision", type=int)
    parser.add_argument("--pause-hash")
    args = parser.parse_args()
    resume = None
    if any(v is not None for v in (args.resume_project, args.resume_run, args.resume_revision, args.pause_hash)):
        if args.cancel:
            parser.error("resume and cancellation are separate operations")
        resume = QualificationResume(project_id=args.resume_project, run_id=args.resume_run,
            revision=args.resume_revision, snapshot_hash=args.pause_hash)
    return run_sample(args.campaign, args.sample, cancel=args.cancel, resume=resume)


if __name__ == "__main__":
    raise SystemExit(main())
