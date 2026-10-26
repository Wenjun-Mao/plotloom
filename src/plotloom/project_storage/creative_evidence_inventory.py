"""Confined retained creative evidence, derived from typed request/pin owners."""
import json
import sqlite3
from hashlib import sha256
from pathlib import PurePosixPath

from ..codex_exec_resources import upstream_skill_path_for_stage
from ..codex_exec_retained_outline import retained_outline_package_projection
from ..creative_handoff_contracts import (
    CREATIVE_CANDIDATE_FILENAMES,
    CreativeDeliveryManifest,
    CreativeHandoffRequest,
)
from ..creative_exchange_files import configured_exchange_root, creative_job_root
from ..creative_package_projection import project_creative_package
from ..creative_handoff_identity import canonical_json, request_hash
from ..creative_execution_pin import execution_pin_for_request
from ..creative_package_publication import PUBLICATION_LOCK
from .format import ProjectStorageCorruptionError
from .snapshot_files import (
    _assert_exchange_file_is_secret_free,
    _safe_directory,
    _safe_regular,
)


def retained_requests(connection):
    requests = {}
    for table in ("v2_source_outline_candidates", "v2_cast_candidates", "v2_art_candidates", "v2_script_candidates", "v2_storyboard_review_candidates"):
        for identifier, raw, manifest_hash in connection.execute(f"SELECT job_id, request, manifest_hash FROM {table}"):
            requests[identifier] = (CreativeHandoffRequest.model_validate_json(raw), manifest_hash)
    for identifier, raw, evidence in connection.execute("SELECT id, native_request, response_evidence FROM v2_production_bridge_intent_jobs WHERE transport='codex_native'"):
        data = json.loads(evidence) if evidence else {}
        requests[identifier] = (CreativeHandoffRequest.model_validate_json(raw), data.get("manifestHash"))
    from .video_batch_evidence import retained_batch_drafts
    for request, data, _attempt, _profile, _receipt in retained_batch_drafts(connection):
        requests[request.job_id] = (request, data.get("manifestHash"))
    return requests


def missing_completed_jobs(root, database):
    """Only the verified prior-snapshot transition may capture these omissions."""
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        return {identifier: digest for identifier, (_request, digest) in retained_requests(connection).items()
            if digest is not None and not (root / "outputs/creative-handoff/jobs" / identifier).exists()}
    finally:
        connection.close()


def _codex_creative_jobs(connection):
    """Bind CLI package shape to the frozen checkpoint and its project attempt."""
    from ..autopilot_contracts import POLICY_VERSION, LaunchPolicy
    from ..codex_exec_contracts import CodexExecAttempt, CodexExecReceipt

    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    v4_runs = {}
    if "v2_autopilot_runs" in tables:
        for run_id, project_id, raw_policy in connection.execute(
            "SELECT id, project_id, policy FROM v2_autopilot_runs"
        ):
            policy = json.loads(raw_policy)
            if policy.get("version") == POLICY_VERSION:
                parsed_policy = LaunchPolicy.model_validate(policy)
                v4_runs[run_id] = (project_id, parsed_policy.executor_binding, parsed_policy.code_revision)

    jobs = {}
    if "v2_autopilot_checkpoints" in tables:
        for run_id, project_id, operation_key, raw_evidence in connection.execute(
            "SELECT run_id, project_id, operation_key, evidence FROM v2_autopilot_checkpoints"
        ):
            run_binding = v4_runs.get(run_id)
            if run_binding is None or run_binding[0] != project_id:
                continue
            evidence = json.loads(raw_evidence)
            job_id = evidence.get("jobId")
            if job_id is not None:
                jobs[job_id] = {
                    "project_id": project_id,
                    "operation_key": operation_key,
                    "profile": run_binding[1],
                    "plotloom_code_revision": run_binding[2],
                    "attempt": None,
                    "receipt": None,
                }

    if "v2_autopilot_exec_attempts" in tables:
        for project_id, operation_key, job_id, raw_attempt, raw_receipt in connection.execute(
            "SELECT project_id, operation_key, job_id, snapshot, receipt FROM v2_autopilot_exec_attempts"
        ):
            attempt = CodexExecAttempt.model_validate_json(raw_attempt)
            if attempt.domain != "text":
                continue
            if (str(attempt.project_id) != project_id or attempt.operation_key != operation_key
                    or attempt.job_id != job_id):
                raise ProjectStorageCorruptionError("retained Codex creative attempt row identity changed")
            binding = jobs.get(job_id)
            if (binding is None or (binding["project_id"], binding["operation_key"])
                    != (project_id, operation_key) or binding["profile"] is None
                    or binding["profile"].profile_hash != attempt.profile_hash):
                raise ProjectStorageCorruptionError("retained Codex creative attempt has no exact v4 checkpoint")
            binding["attempt"] = attempt
            binding["receipt"] = CodexExecReceipt.model_validate_json(raw_receipt) if raw_receipt else None
    from .video_batch_evidence import retained_batch_drafts
    for request, _data, attempt, profile, receipt in retained_batch_drafts(connection):
        jobs[request.job_id] = {"project_id": request.project_id, "operation_key": request.stage, "profile": profile,
            "plotloom_code_revision": attempt.plotloom_code_revision, "attempt": attempt, "receipt": receipt}
    return jobs


def _retained_codex_request_projection(
    request, execution_pin, profile, exchange_root, *, plotloom_code_revision=None
):
    """Project only the package request shapes admitted by retained launch profiles."""
    if profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}:
        if request.stage == "outline":
            try:
                return retained_outline_package_projection(
                    request, execution_pin, source_revision=plotloom_code_revision
                )
            except (TypeError, ValueError) as error:
                raise ProjectStorageCorruptionError("retained Outline package projection is invalid") from error
        projected, _instructions, _template, _members = project_creative_package(
            creative_job_root(exchange_root, request.job_id), request,
            execution_pin,
            executor_backend="codex_exec",
            plotloom_code_revision=plotloom_code_revision,
        )
        return projected
    if profile.contract_version == "plotloom.codex-exec.v5":
        # v5 owns package v3, before the trusted validator plan became part of
        # the frozen request. Keep that exact projection read-only.
        return request.model_dump(mode="json", by_alias=True) | {
            "packageVersion": 3,
            "requestHash": request_hash(request),
            "candidateFilename": CREATIVE_CANDIDATE_FILENAMES[request.stage],
            "reportFilename": "report.html",
            "upstreamSkillPath": upstream_skill_path_for_stage(request.stage),
            "executionPin": execution_pin_for_request(request, execution_pin),
            "executorBackend": "codex_exec",
            "plotloomCodeRevision": plotloom_code_revision,
        }
    if profile.contract_version != "plotloom.codex-exec.v4":
        raise ProjectStorageCorruptionError("retained Codex creative package profile is unsupported")

    # v4 owns package v2, whose request omitted Plotloom source identity. Keep
    # this projection in the read-only inventory owner; it never feeds dispatch
    # or adoption and is bounded to immutable historical evidence inspection.
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 2,
        "requestHash": request_hash(request),
        "candidateFilename": CREATIVE_CANDIDATE_FILENAMES[request.stage],
        "reportFilename": "report.html",
        "upstreamSkillPath": upstream_skill_path_for_stage(request.stage),
        "executionPin": execution_pin_for_request(request, execution_pin),
        "executorBackend": "codex_exec",
    }


def creative_evidence_paths(root, database, *, prior_snapshot_omissions=None):
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        requests = retained_requests(connection)
        pins = {identifier: (digest, json.loads(pin)) for identifier, digest, pin in connection.execute(
            "SELECT job_id, request_hash, execution_pin FROM v2_creative_handoff_execution_pins")}
        codex_jobs = _codex_creative_jobs(connection)
    finally:
        connection.close()
    base = root / "outputs" / "creative-handoff" / "jobs"
    from .schema_transition import restored_creative_omissions
    omissions = prior_snapshot_omissions if prior_snapshot_omissions is not None else restored_creative_omissions(root)
    if any(identifier not in requests or requests[identifier][1] != digest for identifier, digest in omissions.items()):
        raise ProjectStorageCorruptionError("restored creative omission identity changed")
    missing = {identifier for identifier, (_request, digest) in requests.items() if digest is not None
        and not (base / identifier).exists()}
    if missing - omissions.keys():
        raise ProjectStorageCorruptionError("completed creative evidence is unavailable")
    if not base.exists() and not base.is_symlink():
        # Unexported requests have no final evidence; prior omissions require
        # the explicit verified-restoration record above.
        return []
    for directory in (root / "outputs", root / "outputs" / "creative-handoff", base):
        _safe_directory(directory, label="creative evidence ancestor")
    _safe_directory(base, label="creative evidence root")
    if any(path.name not in requests for path in base.iterdir()):
        raise ProjectStorageCorruptionError("creative evidence has an unowned job directory")
    paths = []
    exchange_root = configured_exchange_root(base.parent)
    for identifier, (request, manifest_hash) in requests.items():
        job = base / identifier
        if not job.exists() and not job.is_symlink():
            continue
        _safe_directory(job, label="creative evidence job")
        if request.job_id != identifier or pins.get(identifier, (None,))[0] != request_hash(request):
            raise ProjectStorageCorruptionError("creative evidence request or pin identity changed")
        execution_pin = execution_pin_for_request(request, pins[identifier][1])
        codex_binding = codex_jobs.get(identifier)
        if codex_binding is not None and (
            codex_binding["project_id"] != request.project_id
            or codex_binding["operation_key"] != (f"{request.stage}:correction:{request.text_correction.ordinal}" if request.text_correction else request.stage)
        ):
            raise ProjectStorageCorruptionError("retained Codex creative checkpoint differs from its request")
        executor_backend = "codex_exec" if codex_binding is not None else "specialist_chat"
        if codex_binding is None:
            projected, _instructions, _template, _package_members = project_creative_package(
                creative_job_root(exchange_root, request.job_id), request, execution_pin, executor_backend="specialist_chat"
            )
        else:
            projected = _retained_codex_request_projection(
                request,
                execution_pin,
                codex_binding["profile"],
                exchange_root,
                plotloom_code_revision=codex_binding["plotloom_code_revision"],
            )
        candidate_name = CREATIVE_CANDIDATE_FILENAMES[request.stage]
        expected = {
            "package/request.json", "package/COPY_ASSIGNMENT.txt",
            *(f"package/inputs/{name}" for name in request.input_artifacts),
            f"delivery/{candidate_name}", "delivery/report.html", "delivery/completion.json",
            PUBLICATION_LOCK,
        }
        if executor_backend == "specialist_chat":
            expected.add("package/completion-manifest.example.json")
        allowed_dirs = {"package", "package/inputs", "delivery"}
        observed = set()

        def visit(directory, prefix=""):
            _safe_directory(directory, label="creative evidence directory")
            for child in directory.iterdir():
                relative = f"{prefix}/{child.name}" if prefix else child.name
                if child.is_dir() and not child.is_symlink():
                    if relative not in allowed_dirs:
                        raise ProjectStorageCorruptionError("creative evidence has an unexpected directory")
                    visit(child, relative)
                else:
                    _safe_regular(child, label="creative evidence file")
                    if relative not in expected or child.stat().st_size > 4_000_000:
                        raise ProjectStorageCorruptionError("creative evidence file is unowned or oversized")
                    if relative == PUBLICATION_LOCK and child.stat().st_size != 0:
                        raise ProjectStorageCorruptionError("creative package publication lock contains unknown bytes")
                    _assert_exchange_file_is_secret_free(child)
                    observed.add(relative)
                    paths.append(PurePosixPath(child.relative_to(root).as_posix()))
        visit(job)
        required_package = {name for name in expected if name.startswith("package/")}
        if manifest_hash is not None and not required_package.issubset(observed):
            # These are retained original-location bytes, not a freshly
            # reprojected dispatch package at the recovery destination.
            raise ProjectStorageCorruptionError("completed creative evidence omits frozen package members")
        package_request = job / "package" / "request.json"
        if codex_binding is not None and codex_binding["attempt"] is not None:
            if not (job / "package").is_dir():
                raise ProjectStorageCorruptionError("retained Codex creative attempt lost its frozen package")
            from ..codex_exec_runtime import package_tree_hash
            attempt = codex_binding["attempt"]
            try:
                actual_package_hash = package_tree_hash(
                    job, max_total_bytes=codex_binding["profile"].max_output_bytes
                )
            except (OSError, TypeError, ValueError) as error:
                raise ProjectStorageCorruptionError("retained Codex creative package is unsafe") from error
            if (attempt.request_hash != request_hash(request)
                    or actual_package_hash != attempt.package_hash):
                raise ProjectStorageCorruptionError("retained Codex creative package differs from its exact attempt")
            if attempt.content_rejection is not None:
                rejected = job / "delivery" / candidate_name
                if not rejected.is_file() or sha256(rejected.read_bytes()).hexdigest() != attempt.content_rejection.candidate_hash:
                    raise ProjectStorageCorruptionError("rejected creative candidate differs from its immutable content evidence")
        if package_request.exists():
            raw = json.loads(package_request.read_text(encoding="utf-8"))
            if raw != projected:
                raise ProjectStorageCorruptionError("retained creative package differs from its frozen request/pin")
            if (codex_binding is not None and codex_binding["attempt"] is not None
                    and codex_binding["profile"].contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                    and codex_binding["attempt"].validation_plan_hash != projected.get("validationPlanHash")):
                raise ProjectStorageCorruptionError("retained Codex attempt differs from its frozen validation plan")
        for name, payload in request.input_artifacts.items():
            path = job / "package" / "inputs" / name
            if path.exists() and path.read_bytes() != canonical_json(payload):
                raise ProjectStorageCorruptionError("retained creative input bytes changed")
        if manifest_hash is not None:
            completion = job / "delivery" / "completion.json"
            if not completion.exists():
                raise ProjectStorageCorruptionError("retained final creative evidence changed")
            manifest = CreativeDeliveryManifest.model_validate_json(completion.read_bytes())
            if sha256(canonical_json(manifest.model_dump(mode="json", by_alias=True))).hexdigest() != manifest_hash:
                raise ProjectStorageCorruptionError("retained final creative manifest changed")
            if manifest.job_id != identifier or manifest.request_hash != request_hash(request) or manifest.stage != request.stage:
                raise ProjectStorageCorruptionError("retained creative delivery identity changed")
            expected_codex_schemas = {2, 3} if executor_backend == "codex_exec" else {1}
            if manifest.schema_version not in expected_codex_schemas:
                raise ProjectStorageCorruptionError("retained creative delivery backend differs from its frozen owner")
            if executor_backend == "codex_exec":
                from ..codex_exec_contracts import assert_receipt_matches_attempt
                attempt = codex_binding["attempt"]
                receipt = codex_binding["receipt"]
                if (attempt is None or receipt is None or attempt.state not in {"completed", "settled"}
                        or attempt.terminal_result != "success"
                        or manifest.executor_attempt_id != attempt.attempt_id
                        or manifest.codex_session_id != receipt.session_id
                        or manifest.executor_profile_hash != attempt.profile_hash
                        or not _retained_codex_manifest_revision_matches(
                            codex_binding, execution_pin, attempt, receipt, manifest
                        )):
                    raise ProjectStorageCorruptionError("retained Codex creative manifest lost its exact attempt receipt")
                try:
                    assert_receipt_matches_attempt(attempt, receipt)
                except (TypeError, ValueError) as error:
                    raise ProjectStorageCorruptionError("retained Codex creative attempt receipt is invalid") from error
                receipt_outputs = {item.output_relative_path: item for item in receipt.outputs}
                expected_outputs = {
                    f"delivery/{manifest.candidate.filename}",
                    f"delivery/{manifest.report.filename}",
                }
                if set(receipt_outputs) != expected_outputs or any(
                    (output := receipt_outputs.get(f"delivery/{declared.filename}")) is None
                    or output.output_hash != declared.sha256
                    for declared in (manifest.candidate, manifest.report)
                ):
                    raise ProjectStorageCorruptionError("retained Codex creative outputs differ from their attempt receipt")
                if attempt.validation_plan_hash is None:
                    if manifest.schema_version != 2:
                        raise ProjectStorageCorruptionError("legacy Codex creative delivery claims new validation proof")
                elif (manifest.schema_version != 3
                        or manifest.validation_plan_hash != attempt.validation_plan_hash
                        or receipt.text_validation is None
                        or manifest.validation_evidence_hash != receipt.text_validation.evidence_hash):
                    raise ProjectStorageCorruptionError("retained Codex validation manifest differs from its exact receipt")
            for output in (manifest.candidate, manifest.report):
                path = job / "delivery" / output.filename
                _safe_regular(path, label="retained creative output")
                if f"delivery/{output.filename}" not in observed or sha256(path.read_bytes()).hexdigest() != output.sha256:
                    raise ProjectStorageCorruptionError("retained creative output bytes changed")
    return paths


def _retained_codex_manifest_revision_matches(binding, execution_pin, attempt, receipt, manifest):
    """Keep old v4 provenance inspectable without relaxing current adoption checks."""
    profile = binding["profile"]
    if profile.contract_version == "plotloom.codex-exec.v5":
        frozen_revision = binding["plotloom_code_revision"]
        return (
            attempt.plotloom_code_revision == frozen_revision
            and receipt.plotloom_code_revision == frozen_revision
            and manifest.executor_provenance.code_revision == frozen_revision
        )
    if profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}:
        frozen_revision = binding["plotloom_code_revision"]
        return (
            attempt.plotloom_code_revision == frozen_revision
            and receipt.plotloom_code_revision == frozen_revision
            and manifest.executor_provenance.code_revision == frozen_revision
            and attempt.validation_plan_hash is not None
            and receipt.validation_plan_hash == attempt.validation_plan_hash
            and manifest.validation_plan_hash == attempt.validation_plan_hash
            and receipt.text_validation is not None
            and manifest.validation_evidence_hash == receipt.text_validation.evidence_hash
        )
    if profile.contract_version == "plotloom.codex-exec.v4":
        # The retained v4 publisher labelled upstreamRevision as codeRevision.
        # This validates that exact historical receipt shape; it cannot authorize
        # a new launch, change a package, or satisfy the current adoption owner.
        return (
            attempt.plotloom_code_revision is None
            and receipt.plotloom_code_revision is None
            and manifest.executor_provenance.code_revision == execution_pin["upstreamRevision"]
        )
    return False
