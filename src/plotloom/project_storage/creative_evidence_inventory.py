"""Confined retained creative evidence, derived from typed request/pin owners."""
from hashlib import sha256
import json
from pathlib import PurePosixPath
import sqlite3

from ..creative_handoff_contracts import CreativeHandoffRequest, CreativeDeliveryManifest
from ..creative_handoff_exchange import CreativeHandoffExchange, canonical_json, request_hash, execution_pin_for_request
from .format import ProjectStorageCorruptionError
from .snapshot_files import _safe_directory, _safe_regular, _assert_exchange_file_is_secret_free
from ..creative_package_publication import PUBLICATION_LOCK


def retained_requests(connection):
    requests = {}
    for table in ("v2_source_outline_candidates", "v2_cast_candidates", "v2_art_candidates", "v2_script_candidates", "v2_storyboard_review_candidates"):
        for identifier, raw, manifest_hash in connection.execute(f"SELECT job_id, request, manifest_hash FROM {table}"):
            requests[identifier] = (CreativeHandoffRequest.model_validate_json(raw), manifest_hash)
    for identifier, raw, evidence in connection.execute("SELECT id, native_request, response_evidence FROM v2_production_bridge_intent_jobs WHERE transport='codex_native'"):
        data = json.loads(evidence) if evidence else {}
        requests[identifier] = (CreativeHandoffRequest.model_validate_json(raw), data.get("manifestHash"))
    return requests


def missing_completed_jobs(root, database):
    """Only the verified prior-snapshot transition may capture these omissions."""
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        return {identifier: digest for identifier, (_request, digest) in retained_requests(connection).items()
            if digest is not None and not (root / "outputs/creative-handoff/jobs" / identifier).exists()}
    finally:
        connection.close()


def creative_evidence_paths(root, database, *, prior_snapshot_omissions=None):
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        requests = retained_requests(connection)
        pins = {identifier: (digest, json.loads(pin)) for identifier, digest, pin in connection.execute(
            "SELECT job_id, request_hash, execution_pin FROM v2_creative_handoff_execution_pins")}
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
    for identifier, (request, manifest_hash) in requests.items():
        job = base / identifier
        if not job.exists() and not job.is_symlink():
            continue
        _safe_directory(job, label="creative evidence job")
        if request.job_id != identifier or pins.get(identifier, (None,))[0] != request_hash(request):
            raise ProjectStorageCorruptionError("creative evidence request or pin identity changed")
        execution_pin_for_request(request, pins[identifier][1])
        candidate_name = CreativeHandoffExchange._candidate_filename(request.stage)
        expected = {
            "package/request.json", "package/COPY_ASSIGNMENT.txt", "package/completion-manifest.example.json",
            *(f"package/inputs/{name}" for name in request.input_artifacts),
            f"delivery/{candidate_name}", "delivery/report.html", "delivery/completion.json",
            PUBLICATION_LOCK,
        }
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
        if package_request.exists():
            raw = json.loads(package_request.read_text(encoding="utf-8"))
            expected_request = request.model_dump(mode="json", by_alias=True)
            if any(raw.get(key) != value for key, value in expected_request.items()) or raw.get("requestHash") != request_hash(request) or raw.get("executionPin") != pins[identifier][1]:
                raise ProjectStorageCorruptionError("retained creative package differs from its frozen request/pin")
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
            for output in (manifest.candidate, manifest.report):
                path = job / "delivery" / output.filename
                _safe_regular(path, label="retained creative output")
                if f"delivery/{output.filename}" not in observed or sha256(path.read_bytes()).hexdigest() != output.sha256:
                    raise ProjectStorageCorruptionError("retained creative output bytes changed")
    return paths
