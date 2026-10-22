"""Manual and direct Outline receiving cannot bypass report metadata ownership."""
import json
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256

import pytest

import plotloom.outline_report_metadata as metadata
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.persistence.schema import (
    CreativeHandoffExecutionPinRow,
    SourceOutlineCandidateRow,
)
from plotloom.source_outline_contracts import OutlineAcceptRequest
from tests.source_outline_fixtures import _deliver, _material, _request, _storage


@contextmanager
def _prepared(tmp_path):
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        yield store, request, _deliver(store, request)
    finally:
        store.close()


def _stale_schema(monkeypatch):
    schema = metadata.outline_report_metadata_schema() | {"title": "future schema"}
    monkeypatch.setattr(metadata, "outline_report_metadata_schema", lambda: schema)


def _output(store, request, filename, raw):
    delivery = store.creative_handoff_exchange().root / "jobs" / request.job_id / "delivery"
    (delivery / filename).write_bytes(raw)
    manifest_path = delivery / "completion.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["candidate" if filename == "outline.json" else "report"]["sha256"] = sha256(raw).hexdigest()
    manifest_path.write_bytes(canonical_json(manifest))


@pytest.mark.parametrize("lang", ["zh", "en", None])
def test_manual_and_direct_acceptance_preserve_content_locale(tmp_path, lang):
    with _prepared(tmp_path) as (store, request, _delivery):
        candidate = {"lang": lang, "params": {"language": "zh-CN"}, "episodes": []}
        raw = canonical_json(candidate)
        _output(store, request, "outline.json", raw)
        exchange = store.creative_handoff_exchange()
        delivery = exchange.read_delivery(request, store.creative_handoff_execution_pin(request))
        assert delivery.candidate == candidate
        ready = store.admit_outline_delivery(delivery)
        assert ready.outline == candidate
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        assert accepted.accepted_outline.outline == candidate
        assert store.project().brief.language == "zh-CN"


def test_manual_invalid_metadata_is_not_rewritten(tmp_path):
    with _prepared(tmp_path) as (store, request, _delivery):
        raw = b'{"lang":"zh-CN","story":"unchanged"}'
        _output(store, request, "outline.json", raw)
        with pytest.raises(CreativeHandoffError) as error:
            store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
        assert error.value.code == "outline_report_metadata_invalid"
        assert store.source_outline_state().candidate.status == "prepared"
        path = store.creative_handoff_exchange().root / "jobs" / request.job_id / "delivery/outline.json"
        assert path.read_bytes() == raw


@pytest.mark.parametrize("fault,code", [
    ("package", "package_conflict"), ("manifest", "delivery_manifest_invalid"),
    ("provenance", "delivery_execution_mismatch"), ("hash", "delivery_hash_mismatch"),
    ("object", "delivery_candidate_invalid"), ("report", "delivery_report_invalid"),
])
def test_manual_existing_errors_precede_stale_metadata_artifact(tmp_path, monkeypatch, fault, code):
    with _prepared(tmp_path) as (store, request, _delivery):
        exchange = store.creative_handoff_exchange()
        job = exchange.root / "jobs" / request.job_id
        manifest = job / "delivery/completion.json"
        if fault == "package":
            (job / "package/COPY_ASSIGNMENT.txt").write_text("changed")
        elif fault == "manifest":
            manifest.write_bytes(b"invalid")
        elif fault == "provenance":
            value = json.loads(manifest.read_bytes())
            value["executorProvenance"]["skillHash"] = "0" * 64
            manifest.write_bytes(canonical_json(value))
        elif fault == "hash":
            (job / "delivery/outline.json").write_bytes(b'{"lang":"zh-CN"}')
        elif fault == "object":
            _output(store, request, "outline.json", b"[]")
        else:
            _output(store, request, "report.html", b"not HTML")
        _stale_schema(monkeypatch)
        with pytest.raises(CreativeHandoffError) as error:
            exchange.read_delivery(request, store.creative_handoff_execution_pin(request))
        assert error.value.code == code


def test_valid_manual_transport_still_requires_current_schema(tmp_path, monkeypatch):
    with _prepared(tmp_path) as (store, request, _delivery):
        _stale_schema(monkeypatch)
        with pytest.raises(CreativeHandoffError) as error:
            store.creative_handoff_exchange().read_delivery(request, store.creative_handoff_execution_pin(request))
        assert error.value.code == "outline_report_schema_stale"


def test_direct_prepared_delivery_checks_metadata_and_terminal_status_first(tmp_path):
    with _prepared(tmp_path) as (store, request, delivery):
        invalid = replace(delivery, candidate={"lang": "zh-CN"})
        with pytest.raises(CreativeHandoffError) as error:
            store.admit_outline_delivery(invalid)
        assert error.value.code == "outline_report_metadata_invalid"
        assert store.source_outline_state().candidate.status == "prepared"
        store.admit_outline_delivery(delivery)
        store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        with pytest.raises(CreativeHandoffError) as error:
            store.admit_outline_delivery(invalid)
        assert error.value.code == "delivery_stale"


def test_ready_conflict_precedes_artifact_and_stored_metadata(tmp_path, monkeypatch):
    with _prepared(tmp_path) as (store, request, delivery):
        store.admit_outline_delivery(delivery)
        with store.repository._write() as session:
            session.get(SourceOutlineCandidateRow, request.job_id).outline = {"lang": "zh-CN"}
        _stale_schema(monkeypatch)
        with pytest.raises(CreativeHandoffError) as error:
            store.admit_outline_delivery(replace(delivery, manifest_hash="0" * 64))
        assert error.value.code == "delivery_conflict"


def test_ready_retry_validates_stored_dictionary_not_ignored_incoming(tmp_path):
    with _prepared(tmp_path) as (store, request, delivery):
        ready = store.admit_outline_delivery(delivery)
        assert store.admit_outline_delivery(replace(delivery, candidate={"lang": "zh-CN"})).outline == ready.outline
        with store.repository._write() as session:
            session.get(SourceOutlineCandidateRow, request.job_id).outline = {"lang": "zh-CN"}
        with pytest.raises(CreativeHandoffError) as error:
            store.admit_outline_delivery(delivery)
        assert error.value.code == "outline_report_metadata_invalid"
        assert store.source_outline_state().accepted_outline is None


def test_acceptance_cas_and_stale_checks_precede_stored_metadata(tmp_path):
    with _prepared(tmp_path) as (store, request, delivery):
        store.admit_outline_delivery(delivery)
        with store.repository._write() as session:
            session.get(SourceOutlineCandidateRow, request.job_id).outline = {"lang": "zh-CN"}
        with pytest.raises(RevisionConflictError):
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=request.job_id, expected_source_revision=2, expected_outline_revision=0,
            ))
        with pytest.raises(CreativeHandoffError) as error:
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
            ))
        assert error.value.code == "outline_report_metadata_invalid"
        assert store.source_outline_state().accepted_outline is None


@pytest.mark.parametrize("status", ["accepted", "cancelled"])
def test_prepared_terminal_status_precedes_stale_artifact_and_metadata(tmp_path, monkeypatch, status):
    with _prepared(tmp_path) as (store, request, delivery):
        with store.repository._write() as session:
            session.get(SourceOutlineCandidateRow, request.job_id).status = status
        _stale_schema(monkeypatch)
        with pytest.raises(CreativeHandoffError) as error:
            store.admit_outline_delivery(replace(delivery, candidate={"lang": "zh-CN"}))
        assert error.value.code == ("delivery_cancelled" if status == "cancelled" else "delivery_stale")


def test_acceptance_stale_candidate_precedes_metadata(tmp_path):
    with _prepared(tmp_path) as (store, request, delivery):
        store.admit_outline_delivery(delivery)
        with store.repository._write() as session:
            row = session.get(SourceOutlineCandidateRow, request.job_id)
            row.outline = {"lang": "zh-CN"}
            row.source_revision = 2
        with pytest.raises(CreativeHandoffError) as error:
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
            ))
        assert error.value.code == "delivery_stale"


def test_preparation_busy_guard_precedes_missing_schema(tmp_path):
    with _prepared(tmp_path) as (store, request, _delivery):
        artifacts = {k: v for k, v in request.input_artifacts.items() if k != metadata.OUTLINE_REPORT_SCHEMA_FILENAME}
        replacement = request.model_copy(update={"job_id": "ch_" + "b" * 32, "input_artifacts": artifacts})
        with pytest.raises(InvalidTransitionError, match="cancel the prepared outline"):
            store.repository.source_outline.prepare_candidate(store.manifest.project_id, replacement, execution_pin={})
        assert store.source_outline_state().candidate.job_id == request.job_id


@pytest.mark.parametrize("pin_fault", [False, True])
def test_preparation_pin_priority_and_schema_rejection_roll_back(tmp_path, pin_fault):
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        pin = store.creative_handoff_exchange().current_execution_pin("outline")
        request = request.model_copy(update={"input_artifacts": {
            k: v for k, v in request.input_artifacts.items() if k != metadata.OUTLINE_REPORT_SCHEMA_FILENAME
        }})
        before = store.source_outline_state()
        with pytest.raises(CreativeHandoffError) as error:
            store.repository.source_outline.prepare_candidate(store.manifest.project_id, request,
                execution_pin={} if pin_fault else pin)
        assert error.value.code == ("execution_pin_missing" if pin_fault else "outline_report_schema_missing")
        with store.repository._read() as session:
            assert session.get(CreativeHandoffExecutionPinRow, request.job_id) is None
            assert session.get(SourceOutlineCandidateRow, request.job_id) is None
        assert store.source_outline_state() == before
    finally:
        store.close()
