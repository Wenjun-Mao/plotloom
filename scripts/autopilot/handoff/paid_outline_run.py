"""Consume the exact paid reservation once, observe its receipt, then HOLD."""
import time
from contextlib import closing
from pathlib import Path

from handoff_files import (
    canonical,
    digest,
    publish_record,
    read_owned,
    read_record,
    require,
)
from handoff_phase import B, load_phase
from handoff_receiver import accept_attendance
from paid_outline_composition import compose_registry
from paid_outline_contracts import PaidOutlineAllocation
from paid_outline_state import (
    assert_allocation_files,
    checkpoint_for,
    claim_and_resume,
    frozen_request,
)

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_exec_staged import (
    admit_reserved_codex_exec_once,
    observe_existing_codex_exec,
)
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_controller import AutopilotTextController
from plotloom.codex_exec_contracts import transition_exec_attempt
from plotloom.project_storage import ProjectFolderStorage


def load_allocation(phase):
    require(phase["kind"] == "paid_outline" and phase["authority"] == "paid_outline_once",
        "paid Outline requires separate paid authority")
    raw = read_owned(B / "paid-allocation.json")
    require(digest(raw) == phase["allocationSha256"], "paid allocation hash differs")
    value = PaidOutlineAllocation.model_validate_json(raw)
    from handoff_files import parse
    require(canonical(parse(raw)) == raw and value.phase_root.path == phase["phaseRoot"]
        and value.bundle_root.path == str(B) and value.nonce == phase["nonce"], "paid allocation phase binding differs")
    return value


def run_paid_outline(phase, phase_sha, launch, tree, qa, *, clock=time.monotonic_ns,
        wait=time.sleep, stopped=lambda: False):
    """No caller flag skips attendance, source, ownership or namespace checks."""
    root = Path(phase["phaseRoot"])
    allocation = load_allocation(phase)
    attendance, witness = accept_attendance(phase, phase_sha, launch, tree,
        clock=clock, wait=wait, stopped=stopped)
    accepted = read_record(root, "receiver-accepted.json")
    require(accepted is not None and accepted[0] == witness and witness["allocationSha256"] == phase["allocationSha256"]
        and witness["attendanceSha256"] == digest(read_owned(root / "attendance.json"))
        and witness["phaseSha256"] == phase_sha and witness["authority"] == "paid_outline_once"
        and witness["providerAuthority"] is False and witness["productionAuthority"] is False,
        "missing or substituted committed paid attendance")
    require(attendance["allocationSha256"] == phase["allocationSha256"]
        and attendance["authority"] == "paid_outline_once" and attendance["phaseSha256"] == phase_sha,
        "paid attendance identity differs")
    deadline = int(witness["deadlineMonotonicNs"])
    require(not stopped() and clock() < deadline, "original attachment deadline expired before paid admission")
    assert_allocation_files(allocation, qa)
    ns, attempt = allocation.namespace, allocation.namespace.attempt
    registry = compose_registry(ns.source_root.path, ns.executable.path, ns.application_root.path,
        ns.outputs_root.path, ns.private_root.path, limits=ns.limits, namespace_pin=allocation.namespace_binding_sha256)
    require(registry.codex_exec_profile() == ns.profile, "paid profile drift")
    host = registry.bridge.exec_supervisor()
    require(host._row(attempt.attempt_id) is None, "paid namespace already has an initial host attempt")
    storage = ProjectFolderStorage(outputs_root=Path(ns.outputs_root.path), application_data_root=Path(ns.application_root.path))
    homes = storage.projects.discover()
    require(len(homes) == 1 and homes[0].path == Path(allocation.project_home.path)
        and homes[0].manifest.project_id == str(attempt.project_id), "paid catalog differs from allocation")
    service = AutopilotService(storage, registry)
    expected_revision = None
    result = {"version": 1, "allocationSha256": phase["allocationSha256"], "phaseSha256": phase_sha,
        "attemptId": str(attempt.attempt_id), "settlementAuthority": "hold_only", "canonicalAdoption": False,
        "imageAdmissions": 0, "retryAuthorized": False, "qualification": False}
    try:
        require(service.acquire_controller(), "paid controller process lease unavailable")
        require(not stopped() and clock() < deadline, "original attachment deadline expired before claim")
        with closing(storage.projects.open(str(attempt.project_id))) as store:
            view = claim_and_resume(store, allocation, registry)
            expected_revision = allocation.claim_edges.resumed_revision
            checkpoint = checkpoint_for(view)
            request = frozen_request(store, view, allocation.claim_edges.receiver_claim)
            package = store.creative_handoff_exchange().root / "jobs" / attempt.job_id / "package"
            require(not stopped() and clock() < deadline, "original attachment deadline expired before consumption")
            runtime_deadline = clock() + ns.profile.max_runtime_seconds * 1_000_000_000
            def before_spawn():
                # Core readiness/profile/package checks can cross the original
                # attachment deadline. Recheck at its actual consumption hook,
                # with the final clock gate after every expensive source read.
                require(not stopped() and clock() < deadline, "original attachment deadline expired at consumption")
                load_phase(root, phase_sha, expected_kind="paid_outline")
                assert_allocation_files(allocation, qa)
                require(registry.codex_exec_profile() == ns.profile, "paid profile drift at consumption")
                latest_witness = read_record(root, "receiver-accepted.json")
                require(latest_witness is not None and latest_witness[0] == witness
                    and digest(read_owned(root / "attendance.json")) == witness["attendanceSha256"],
                    "committed attendance changed before consumption")
                markers = [p.name for p in root.iterdir() if p.name.startswith("attendance.commit-")]
                require(markers == ["attendance.commit-" + witness["attendanceSha256"]]
                    and read_owned(root / markers[0]) == b"", "attendance authority changed before consumption")
                require(not stopped() and clock() < deadline, "original attachment deadline expired at consumption")
            try:
                observed, receipt = admit_reserved_codex_exec_once(store, registry, view,
                    allocation.claim_edges.receiver_claim, checkpoint, expected_attempt=attempt,
                    expected_run_revision=expected_revision, package_path=str(package),
                    command_factory=AutopilotTextController.command, before_spawn=before_spawn)
            except Exception as error:  # noqa: BLE001 -- admission boundary must retain unknown external outcomes
                # The owner may have committed intent before losing the host
                # acknowledgment. Never call admit/resume again on this path.
                observed, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline")
                intent = transition_exec_attempt(attempt, state="spawn_intent")
                if observed is not None:
                    expected_revision += int(observed.state != "reserved") + int(observed.state != "reserved" and observed != intent)
                result.update(outcome="NOT_ADMITTED" if observed is not None and observed.state == "reserved" else "UNKNOWN",
                    initialAdmissionSpent=observed.state != "reserved" if observed else None, reason=type(error).__name__,
                    attemptState=observed.state if observed else "missing")
                return _pause_and_publish(service, allocation, expected_revision, root, result)
            intent = transition_exec_attempt(attempt, state="spawn_intent")
            expected_revision += 1 + int(observed != intent or receipt is not None)
            while observed.state not in {"completed", "failed", "settled", "outcome_unknown"}:
                if stopped() or clock() >= runtime_deadline:
                    result.update(outcome="UNKNOWN", reason="observation_stopped_or_runtime_elapsed")
                    break
                previous = observed, receipt
                observed, receipt = observe_existing_codex_exec(store, registry, view,
                    allocation.claim_edges.receiver_claim, expected_attempt=attempt,
                    command_factory=AutopilotTextController.command)
                expected_revision += int((observed, receipt) != previous)
                if (observed, receipt) == previous:
                    wait(0.2)
            current = store.repository.autopilot.current(str(attempt.project_id))
            require(current.revision == expected_revision and current.state == "running",
                "foreign run revision/control changed during observation")
            delivery = service.controller.validated_delivery(store, current, "outline", request) if receipt is not None else None
            if receipt is not None:
                require(delivery is not None, "typed receipt has no exact validated delivery")
                result.update(receiptSha256=digest(canonical(receipt.model_dump(mode="json", by_alias=True))),
                    deliverySha256=delivery.manifest_hash)
            result.setdefault("outcome", "RECEIPT_AND_VALIDATED_DELIVERY" if delivery else observed.state.upper())
            result["attemptState"] = observed.state
            return _pause_and_publish(service, allocation, expected_revision, root, result)
    except Exception as error:  # noqa: BLE001 -- exact HOLD and durable UNKNOWN are the only failure settlement
        result.update(outcome="UNKNOWN", reason=type(error).__name__)
        return _pause_and_publish(service, allocation, expected_revision, root, result)
    finally:
        service.close()


def _publish_hold(root, result):
    publish_record(root, "paid-result.json", result)
    return result


def _pause_and_publish(service, allocation, expected_revision, root, result):
    result["held"] = False
    if expected_revision is not None:
        try:
            paused = service.control(str(allocation.namespace.attempt.project_id),
                RunControlRequest(expected_revision=expected_revision, action="pause"))
            require(paused.state == "paused" and paused.revision == expected_revision + 1, "paid HOLD was not acknowledged")
            result.update(held=True, pausedRevision=paused.revision)
        except Exception as error:  # noqa: BLE001 -- report failed HOLD without claiming acknowledgment
            result["holdFailure"] = type(error).__name__
    return _publish_hold(root, result)
