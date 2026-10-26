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

from plotloom.alpha_campaign import campaign_lease, load_campaign, write_private_json
from plotloom.alpha_publication import content_only_review_payload
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


def run_sample(work_root, sample_id, *, cancel=False):
    """Advance one predeclared cell only; restarting observes its original IDs."""
    root = Path(work_root)
    with campaign_lease(root):
        campaign = load_campaign(root, check_source=True)
        sample = next((s for s in campaign.samples if s.sample_id == sample_id), None)
        if sample is None:
            raise ValueError("sample is outside the frozen native matrix")
        evidence = root / "evidence" / sample_id
        evidence.mkdir(exist_ok=True, mode=0o700)
        receipt_file = evidence / "receipt.json"
        if receipt_file.exists() and not cancel:
            raise ValueError("sample already has an outcome; inspect it instead of repeating native work")
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
            identity = {"workbench": runtime.url, "bridge": runtime.bridge_url,
                "dataRoot": str(config.data_root), "privateRoot": str(supervisor.private_root),
                "database": str(supervisor.database),
                "databaseDevice": supervisor.database.stat().st_dev,
                "databaseInode": supervisor.database.stat().st_ino,
                "namespaceBinding": supervisor._namespace_sha256,
                "capacity": capacity.model_dump(mode="json", by_alias=True),
                "profileHash": supervisor.profile().profile_hash}
            write_private_json(evidence / "runtime.json", identity, replace=True)
            # Independent service instance takes the production lease before the
            # ordinary app lifespan starts its background controller.
            with AutopilotTextPrefix(storage, registry) as prefix, serving(runtime):
                assert read_http(runtime.url + "/healthz") == {"status": "ok"}
                project_id = str(sample.project_id)
                homes = {h.manifest.project_id for h in storage.projects.discover(passive=True)}
                if project_id not in homes:
                    if cancel:
                        raise ValueError("cannot cancel a sample that was never admitted")
                    with closing(storage.projects.create(sample.brief, project_id=project_id)):
                        pass
                with closing(storage.projects.open(project_id)) as store:
                    if store.project().require_brief() != sample.brief:
                        raise ValueError("saved native sample Brief differs from the frozen workload")
                    view = store.repository.autopilot.current(project_id)
                if view is None:
                    view = prefix.launch(project_id, LaunchRequest(expected_brief_revision=1, style_authority="brief"))
                if (view.policy.executor_binding.profile_hash != campaign.source["profileHash"]
                        or view.policy.code_revision != campaign.source["commit"]
                        or view.policy.text_correction_limit != 1
                        or view.policy.execution_pins != campaign.source["executionPins"] | {"image": campaign.source["imagePin"]}):
                    raise ValueError("saved launch differs from the frozen native execution policy")
                if cancel:
                    view = prefix.service.control(project_id,
                        RunControlRequest(action="cancel", expected_revision=view.revision), expected_run_id=view.id)
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
                    receipt, private = collect_native_evidence(store, view, snapshot=campaign.source,
                        contract_hash=campaign.contract_hash, sample_id=sample_id,
                        duration_ms=round((time.monotonic() - started) * 1000))
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
                    write_private_json(evidence / "content.json", content)
                write_private_json(evidence / "bindings.private.json", private, replace=cancel)
                write_private_json(receipt_file, receipt.model_dump(mode="json", by_alias=True), replace=cancel)
                print(json.dumps({"sampleId": sample_id, "status": receipt.status,
                    "firstPass": sum(op.first_pass for op in receipt.operations)}), flush=True)
                return 0 if receipt.status == "installed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--cancel", action="store_true", help="Cancel only this exact predeclared disposable sample")
    args = parser.parse_args()
    return run_sample(args.campaign, args.sample, cancel=args.cancel)


if __name__ == "__main__":
    raise SystemExit(main())
