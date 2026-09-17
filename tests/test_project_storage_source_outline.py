"""F1A regression coverage for source ownership and outline candidate admission."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.source_outline_contracts import (
    OutlineAcceptRequest,
    OutlineReopenRequest,
    SourceMaterial,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import RevisionConflictError


def _material(kind: str = "synopsis") -> SourceMaterial:
    return SourceMaterial(
        kind=kind,
        title="渡口的信",
        text="一位船夫必须在暴风雨前决定把最后一封信交给谁。",
        attribution="作者本人提供的 F1A 测试材料",
        rights_declaration="作者声明拥有用于此测试的改编许可；系统不作法律确认。",
        adaptation_intent="保留不可逆选择，并允许为互动形式补充一条分支后果。",
        invented_additions="可以增加一位目击者。",
    )


def _storage(tmp_path: Path) -> ProjectFolderStorage:
    return ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )


def _request(project_id: str, source: SourceMaterial, expected_outline_revision: int = 0) -> CreativeHandoffRequest:
    return CreativeHandoffRequest(
        job_id="ch_" + "a" * 32,
        project_id=project_id,
        section_id="story",
        stage="outline",
        expected_stage_revision=expected_outline_revision,
        source=source.model_dump(mode="json", by_alias=True),
        input_artifacts={},
        creative_brief="Produce one upstream-shaped review candidate only.",
    )


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    paths = exchange.write_package(request)
    package_request = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    outline = canonical_json({"source": "渡口的信", "params": {"episodes": 1}, "episodes": []})
    report = b"<!doctype html><html><body>derived outline</body></html>"
    (delivery / "outline.json").write_bytes(outline)
    (delivery / "report.html").write_bytes(report)
    manifest = {
        "schemaVersion": 1,
        "jobId": request.job_id,
        "requestHash": package_request["requestHash"],
        "deliveryId": "f1a-fixture-1",
        "stage": "outline",
        "candidate": {"filename": "outline.json", "sha256": sha256(outline).hexdigest()},
        "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()},
        "executorProvenance": {
            "codeRevision": "abcdef0",
            "skillVersion": "fixture",
            "skillHash": package_request["executionPin"]["specialistSkillHash"],
            "upstreamRevision": package_request["executionPin"]["upstreamRevision"],
            "upstreamSkillHash": package_request["executionPin"]["upstreamSkillHash"],
            "model": "fixture",
            "reasoningEffort": "high",
        },
        "limitations": ["fixture candidate"],
    }
    (delivery / "completion.json").write_text(json.dumps(manifest))
    result = exchange.read_delivery(request)
    assert result is not None
    return result


@pytest.mark.parametrize("kind", ["synopsis", "imported_text", "existing_work"])
def test_source_modes_persist_candidate_and_explicit_acceptance(tmp_path: Path, kind: str) -> None:
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material(kind)
        saved = store.save_source_material(expected_source_revision=0, material=source)
        assert saved.source is not None and saved.source.material.kind == kind
        request = _request(store.manifest.project_id, source)
        prepared = store.prepare_outline_candidate(request)
        assert prepared.status == "prepared"
        ready = store.admit_outline_delivery(_deliver(store, request))
        assert ready.status == "ready" and ready.outline == {"source": "渡口的信", "params": {"episodes": 1}, "episodes": []}
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        assert accepted.outline_status == "accepted"
        assert accepted.accepted_outline is not None
        assert accepted.accepted_outline.outline == ready.outline
        reopened = store.reopen_outline(OutlineReopenRequest(expected_outline_revision=1))
        assert reopened.outline_status == "reopened"
        assert reopened.accepted_outline == accepted.accepted_outline
        project_id = store.manifest.project_id
        store.close()
        store = storage.projects.open(project_id)
        persisted = store.source_outline_state()
        assert persisted.source is not None and persisted.source.material.kind == kind
        assert persisted.accepted_outline == accepted.accepted_outline
    finally:
        store.close()


def test_stale_foreign_and_racing_deliveries_cannot_change_accepted_content(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    second = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        first.save_source_material(expected_source_revision=0, material=source)
        request = _request(first.manifest.project_id, source)
        first.prepare_outline_candidate(request)
        delivery = _deliver(first, request)

        with pytest.raises(CreativeHandoffError, match="does not belong"):
            second.admit_outline_delivery(delivery)
        assert second.source_outline_state().accepted_outline is None

        first.save_source_material(expected_source_revision=1, material=_material("imported_text"))
        with pytest.raises(RevisionConflictError):
            first.save_source_material(expected_source_revision=1, material=_material("existing_work"))
        with pytest.raises(CreativeHandoffError, match="no longer the active|stale"):
            first.admit_outline_delivery(delivery)
        state = first.source_outline_state()
        assert state.source is not None and state.source.revision == 2
        assert state.accepted_outline is None
        assert state.candidate is None
    finally:
        first.close()
        second.close()


def test_malformed_and_racing_candidate_admission_leave_accepted_outline_unchanged(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        exchange = store.creative_handoff_exchange()
        paths = exchange.write_package(request)
        delivery = Path(paths["deliveryPath"])
        delivery.mkdir()
        (delivery / "outline.json").write_text("not-json")
        (delivery / "report.html").write_text("<html></html>")
        (delivery / "completion.json").write_text("not-json")
        with pytest.raises(CreativeHandoffError, match="completion manifest"):
            exchange.read_delivery(request)
        assert store.source_outline_state().accepted_outline is None

        # A clean subsequent package uses a new identity; malformed delivery
        # remains only rejected handoff evidence and cannot be installed.
        next_request = CreativeHandoffRequest.model_validate(
            request.model_dump(mode="python") | {"job_id": "ch_" + "b" * 32}
        )
        store.prepare_outline_candidate(next_request)
        store.creative_handoff_exchange().write_package(next_request)
        ready = store.admit_outline_delivery(_deliver(store, next_request))
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=ready.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        with pytest.raises(RevisionConflictError):
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=ready.job_id, expected_source_revision=1, expected_outline_revision=0,
            ))
        assert store.source_outline_state().accepted_outline == accepted.accepted_outline
    finally:
        store.close()
