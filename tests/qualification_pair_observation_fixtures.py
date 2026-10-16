"""Synthetic typed facts only; no auth, CLI, image service or subprocess."""
from uuid import uuid4

from admission_observation import FrozenJob, LedgerRow, LedgerSample, identity
from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecOutputEvidence,
    CodexExecReceipt,
    output_manifest_hash,
    transition_exec_attempt,
)


class Clock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 10
        return self.value


def attempt(*, domain="image", **changes):
    values = dict(attempt_id=uuid4(), run_id=uuid4(), project_id=uuid4(),
        job_id=("ij_" if domain == "image" else "ch_") + uuid4().hex,
        operation_key="image:shot-1" if domain == "image" else "outline", domain=domain,
        request_hash="1" * 64, package_hash="2" * 64, profile_hash="3" * 64,
        plotloom_code_revision="a" * 40, validation_plan_hash=None,
        reserved_image_outputs=int(domain == "image"),
        image_budget_state="reserved" if domain == "image" else "none", state="spawn_intent")
    return CodexExecAttempt(**(values | changes))


def frozen(value):
    return FrozenJob.from_prepared(**{name: item for name, item in identity(value) if name != "attempt_id"})


def sample(clock, row=None):
    return LedgerSample(clock(), clock(), row)


def classify(observer, value, observation):
    return observer.classify(value, checkpoint_attempt_id=value.attempt_id,
        current_package_hash=value.package_hash, sample=observation)


def queued(value, *, enabled=False):
    return LedgerRow(value, transition_exec_attempt(value, state="queued"), enabled)


def successful_text(*, pid=1001):
    original = attempt(domain="text")
    outputs = (CodexExecOutputEvidence(outputHash="4" * 64,
        outputRelativePath="delivery/candidate.json", sizeBytes=20),)
    output_hash = output_manifest_hash(outputs)
    current = transition_exec_attempt(original, state="completed", terminal_result="success",
        session_id=uuid4(), process_id=pid, process_group_id=pid,
        process_birth_identity=f"fixture:{pid}", process_exit_code=0,
        remote_tool_state="not_applicable", evidence_hash="5" * 64, output_hash=output_hash)
    receipt = CodexExecReceipt(attemptId=current.attempt_id, sessionId=current.session_id,
        profileHash=current.profile_hash, requestHash=current.request_hash,
        packageHash=current.package_hash, plotloomCodeRevision=current.plotloom_code_revision,
        processId=pid, processGroupId=pid,
        processBirthIdentity=current.process_birth_identity, processExitCode=0,
        expectedImageOutputs=0, evidenceHash=current.evidence_hash,
        outputHash=output_hash, outputs=outputs, remoteToolState="not_applicable")
    validated = CodexExecHostStatus(state="completed", attempt=current, receipt=receipt)
    assert validated.attempt == current and validated.receipt == receipt
    return LedgerRow(original, current, worker_pid=pid + 1,
        worker_group_id=pid + 1, worker_birth_identity=f"worker:{pid + 1}", receipt=receipt)


def receipt_bound_sessions():
    """Mock measurement facts for control-only tests; not native receipt evidence."""
    result=[]
    for index,(begin,end) in enumerate((('00:00:00','00:00:03'),('00:00:01','00:00:04'))):
        result.append(dict(attemptId=str(uuid4()),sessionId=str(uuid4()),domain='image',
            transcriptSha256='a'*64,receiptEvidenceHash='b'*64,receiptEvidenceHashVerified=True,
            imageCalls=[dict(callId='call-'+str(index),eventId='event-'+str(index),callOrdinal=1,completionOrdinal=2,
                callUtc='2026-10-15T'+begin+'Z',completionUtc='2026-10-15T'+end+'Z')]))
    return result
