"""Explicit fresh work after corrected source; never settle or retry UNKNOWN."""
from uuid import UUID

from pydantic import Field
from sqlalchemy import select

from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile
from .domain_base import CamelModel
from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash
from .persistence.schema import VideoBatchRow, VideoJobRow
from .video_batch_contracts import BatchSetup
from .video_batch_inventory import inventory, source_binding, validate_manifest


class CorrectedSourceSuccessor(CamelModel):
    command_id: UUID
    predecessor_batch_id: UUID
    expected_revision: int = Field(strict=True, ge=1)
    predecessor_job_id: str = Field(min_length=1, max_length=64)
    predecessor_attempt_id: UUID
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_execution_profile_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    setup: BatchSetup


def _refuse(message):
    raise InvalidTransitionError("corrected-source successor: " + message)


def _settings(setup):
    value = dict(setup)
    single = dict(value.get("singleRequest") or {})
    # Only a current visual revision and a fresh admission identity may vary.
    single.pop("expectedSelectionRevision", None)
    single.pop("idempotencyKey", None)
    value["singleRequest"] = single
    return value


def same_execution_envelope(before, after):
    # A causal source repair changes the validator's complete Python-tree hash.
    # It never grants a model, executable, instruction, permission or limit change.
    return {k:v for k,v in before.items() if k != 'validatorHash'} == {k:v for k,v in after.items() if k != 'validatorHash'}


def assert_corrected_manifest(original, manifest):
    old_setup, setup = original['setup'], manifest['setup']
    old_request, request = old_setup.get('singleRequest'), setup.get('singleRequest')
    old_targets, targets = original['targets'], manifest['targets']
    if (not old_request or not request or len(setup.get('shotIds') or []) != 1
            or _settings(old_setup) != _settings(setup)
            or request['idempotencyKey'] == old_request['idempotencyKey']
            or request.get('reviewedDirections') is not None
            or manifest['scopeShotIds'] != original['scopeShotIds'] or manifest['kept']
            or manifest['backend'] != original['backend']
            or len(old_targets) != 1 or len(targets) != 1
            or any(t['mode'] != 'generate' or t['jobId'] for t in old_targets + targets)
            or old_targets[0]['sourceHash'] == targets[0]['sourceHash']
            or original['sourceBinding'] == manifest['sourceBinding']):
        _refuse('requires changed source, the same single-shot settings/backend/budgets, and a fresh unreviewed identity')


def _stopped_predecessor(service, view, command):
    execution = view["execution"]
    if (view["state"] != "cancelled" or execution.get("authorizedManifestHash")
            or execution.get("jobs") or execution.get("segments")
            or execution.get("reviewAttribution") or execution.get("correctedSourceSuccessor")):
        _refuse("requires one cancelled, unstarted non-QA batch without a successor")
    active = [execution[key] for key in ("draft", "fidelity") if execution.get(key)]
    if not active:
        _refuse("missing native text attempt")
    retained = active + execution.get("draftHistory", []) + execution.get("fidelityHistory", [])
    for data in retained:
        attempt = CodexExecAttempt.model_validate(data["attempt"])
        if attempt.execution_failure in {"permission", "authorization", "configuration"}:
            _refuse("a retained execution refusal needs its own resolution")
    latest = active[-1]
    attempt = CodexExecAttempt.model_validate(latest["attempt"])
    if (attempt.attempt_id != command.predecessor_attempt_id or attempt.job_id != command.predecessor_job_id
            or str(attempt.project_id) != view["projectId"] or str(attempt.run_id) != view["id"]
            or attempt.state != "outcome_unknown" or attempt.execution_failure != "cancelled"
            or attempt.domain != "text" or attempt.reserved_image_outputs != 0 or attempt.image_budget_state != "none"):
        _refuse("requires the exact cancelled text-only UNKNOWN with no image reservation")
    profile = CodexExecProfile.model_validate(service.registry.codex_exec_profile())
    if profile.profile_hash != command.expected_execution_profile_hash:
        _refuse('prospective execution profile changed')
    for data in active:
        prior = CodexExecAttempt.model_validate(data["attempt"])
        if (prior.domain != "text" or prior.reserved_image_outputs or prior.image_budget_state != "none"
                or not same_execution_envelope(data["profile"], profile.model_dump(mode="json", by_alias=True))):
            _refuse("native text profile or reservation changed")
        status = service.registry.codex_exec_status(prior.attempt_id)
        if (status.attempt != prior or not status.local_execution_stopped
                or prior.state not in {"completed", "failed", "settled", "outcome_unknown"}
                or prior.state == "outcome_unknown" and prior.attempt_id != attempt.attempt_id):
            _refuse("native host has not proved every exact text attempt stopped")
    return attempt, profile


def create_successor(service, store, session, project_id, command):
    owner = store.repository.video_batches
    request_hash = stable_hash(command.model_dump(mode="json", by_alias=True))
    prior_command = session.scalar(select(VideoBatchRow).where(
        VideoBatchRow.project_id == project_id,
        VideoBatchRow.execution["correctedSourcePredecessor"]["commandId"].as_string() == str(command.command_id)))
    if prior_command:
        if prior_command.execution["correctedSourcePredecessor"]["requestHash"] != request_hash:
            _refuse("command identity was already used for different inputs")
        return owner.view(prior_command)
    view = owner.current(project_id)
    if (not view or view["id"] != str(command.predecessor_batch_id)
            or view["revision"] != command.expected_revision):
        _refuse("predecessor batch or revision changed")
    store.require_recovery_acknowledged()
    attempt, profile = _stopped_predecessor(service, view, command)
    if stable_hash(source_binding(store)) != command.expected_source_hash:
        _refuse("current corrected source changed")
    new_setup = command.setup.model_dump(mode="json", by_alias=True)
    from .video_batch_replacement import evidence_reader
    from .video_single_replacement import assert_fresh_single_replacement
    assert_fresh_single_replacement(evidence_reader(session), project_id, view['manifest'], new_setup,
        [{'shotId':view['manifest']['scopeShotIds'][0]}])
    manifest = inventory(store, service.require_video(), command.setup)
    old_targets, new_targets = view["manifest"]["targets"], manifest["targets"]
    assert_corrected_manifest(view['manifest'], manifest)
    uncertain = {"prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"}
    for job in session.scalars(select(VideoJobRow).where(VideoJobRow.project_id == project_id)):
        if job.snapshot.get("shot", {}).get("id") in manifest["scopeShotIds"] and job.state in uncertain:
            _refuse("existing H3 work in this scope must retain its own lifecycle")
    validate_manifest(store, service.require_video(), manifest, compiled=False)
    link = {"commandId": str(command.command_id), "requestHash": request_hash,
            "request": command.model_dump(mode="json", by_alias=True),
            "executionProfile": profile.model_dump(mode="json", by_alias=True),
            "batchId": view["id"], "revision": view["revision"], "attempt": attempt.model_dump(mode="json", by_alias=True),
            "possiblePriorCost": True, "nativeLocalExecutionStopped": True,
            "oldSourceHash": old_targets[0]["sourceHash"], "newSourceHash": new_targets[0]["sourceHash"]}
    created = owner.create(project_id, manifest)
    if created["id"] == view["id"]:
        _refuse("predecessor changed before successor creation")
    owner.change(project_id, view["id"], expected_revision=command.expected_revision,
        mutate=lambda row: setattr(row, "execution", row.execution | {"correctedSourceSuccessor": {
            "commandId": str(command.command_id), "requestHash": request_hash, "batchId": created["id"]}}))
    return owner.change(project_id, created["id"], expected_revision=created["revision"],
        mutate=lambda row: setattr(row, "execution", row.execution | {"correctedSourcePredecessor": link}))
