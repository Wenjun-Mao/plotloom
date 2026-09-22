"""F1A regression coverage for source ownership and outline candidate admission."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import update

from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.source_outline_contracts import (
    BranchOutcome, OutlineAcceptRequest,
    OutlineReopenRequest,
    SectionChoice, SectionMap, SectionMapGraphInstallRequest, SectionMapSaveRequest, StorySection,
    SourceMaterial,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import ProjectLifecycleStatus, StageName, StageStatus, utc_now
from plotloom.domain import InitialStage
from plotloom.exceptions import (
    InvalidTransitionError,
    ProjectBusyError as LifecycleProjectBusyError,
    RevisionConflictError,
)
from plotloom.persistence.schema import ProjectRow
from plotloom.project_storage import ProjectBusyError
from tests.backend_core.conftest import make_story_bible, make_story_graph


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


def _request(
    project_id: str, source: SourceMaterial, expected_outline_revision: int = 0, job_suffix: str = "a",
) -> CreativeHandoffRequest:
    return CreativeHandoffRequest(
        job_id="ch_" + job_suffix * 32,
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


def test_explicit_binary_section_map_is_bound_to_outline_and_stales_on_source_change(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        outline = accepted.accepted_outline
        assert outline is not None
        mapping = SectionMap(
            sections=[
                StorySection(section_id="opening", title="渡口", summary="船夫收到最后一封信。"),
                StorySection(section_id="ending-a", title="交给妹妹", summary="妹妹在风暴前读到信。", ending=True),
                StorySection(section_id="ending-b", title="交给船长", summary="船长带信离岸。", ending=True),
            ],
            choice=SectionChoice(
                choice_id="deliver", section_id="opening", prompt="把信交给谁？",
                outcomes=[
                    BranchOutcome(outcome_id="sister", label="交给妹妹", consequence="妹妹留下。", ending_section_id="ending-a"),
                    BranchOutcome(outcome_id="captain", label="交给船长", consequence="船长启航。", ending_section_id="ending-b"),
                ],
            ),
        )
        saved = store.save_section_map(SectionMapSaveRequest(
            expected_section_map_revision=0, expected_source_revision=1,
            expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
            mapping=mapping,
        ))
        assert saved.section_map_status == "current"
        assert saved.accepted_section_map is not None
        assert saved.accepted_section_map.mapping == mapping
        installed = store.install_section_map_graph(SectionMapGraphInstallRequest(
            expected_source_revision=1, expected_source_content_hash=saved.source.content_hash,  # type: ignore[union-attr]
            expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
            expected_section_map_revision=1, expected_section_map_content_hash=saved.accepted_section_map.content_hash,
            expected_graph_revision=0,
        ))
        assert installed.graph_admission is not None
        assert installed.graph_admission.status == "current"
        graph = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH)
        assert graph.start_node_id == "opening"
        assert {node.id for node in graph.nodes} == {"opening", "ending-a", "ending-b"}
        assert [(edge.id, edge.choice_text, edge.state_effects["sourceMapConsequence"]) for edge in graph.edges] == [
            ("sister", "交给妹妹", "妹妹留下。"), ("captain", "交给船长", "船长启航。"),
        ]
        with pytest.raises(RevisionConflictError):
            store.install_section_map_graph(SectionMapGraphInstallRequest(
                expected_source_revision=1, expected_source_content_hash=saved.source.content_hash,  # type: ignore[union-attr]
                expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
                expected_section_map_revision=1, expected_section_map_content_hash=saved.accepted_section_map.content_hash,
                expected_graph_revision=0,
            ))
        project_id = store.manifest.project_id
        store.close()
        store = storage.projects.open(project_id)
        reopened = store.source_outline_state()
        assert reopened.accepted_section_map is not None
        assert reopened.section_map_status == "current"
        assert reopened.graph_admission is not None and reopened.graph_admission.status == "current"

        # The F1B source-map graph records no Story Bible input.  Installing
        # an otherwise independent Bible later must not invalidate that graph
        # just because the generic canonical stage order lists Bible first.
        store.update_stage(
            StageName.STORY_BIBLE,
            make_story_bible().model_dump(mode="json", by_alias=True),
            expected_revision=0,
        )
        assert store.authoring.get_stage_head(project_id, StageName.STORY_GRAPH).status == StageStatus.READY

        edited_mapping = mapping.model_copy(deep=True)
        edited_mapping.sections[0].summary = "船夫收到最后一封信，并看见风暴逼近。"
        edited_mapping.choice.prompt = "在风暴前把信交给谁？"
        edited_mapping.choice.outcomes[0].label = "把信亲手交给妹妹"
        edited = store.save_section_map(SectionMapSaveRequest(
            expected_section_map_revision=1, expected_source_revision=1,
            expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
            mapping=edited_mapping,
        ))
        assert edited.accepted_section_map is not None
        assert edited.accepted_section_map.mapping.sections[0].section_id == "opening"
        assert edited.accepted_section_map.mapping.choice.outcomes[0].outcome_id == "sister"
        assert edited.graph_admission is not None and edited.graph_admission.status == "stale"
        changed_id = edited_mapping.model_copy(deep=True)
        changed_id.sections[0].section_id = "other-opening"
        changed_id.choice.section_id = "other-opening"
        with pytest.raises(InvalidTransitionError, match="immutable"):
            store.save_section_map(SectionMapSaveRequest(
                expected_section_map_revision=2, expected_source_revision=1,
                expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
                mapping=changed_id,
            ))

        replacement_request = _request(project_id, source, expected_outline_revision=1, job_suffix="b")
        store.prepare_outline_candidate(replacement_request)
        store.admit_outline_delivery(_deliver(store, replacement_request))
        outline_stale = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=replacement_request.job_id, expected_source_revision=1, expected_outline_revision=1,
        ))
        assert outline_stale.section_map_status == "stale"
        assert outline_stale.section_map_stale_reasons == ["accepted outline revision changed to r2"]
        assert outline_stale.graph_admission is not None
        assert outline_stale.graph_admission.status == "stale"
        assert store.authoring.get_stage_head(project_id, StageName.STORY_GRAPH).status == StageStatus.STALE

        changed = _material()
        changed = changed.model_copy(update={"text": changed.text + " 来源经过作者修订。"})
        stale = store.save_source_material(expected_source_revision=1, material=changed)
        assert stale.section_map_status == "stale"
        assert stale.section_map_stale_reasons == ["accepted source revision changed to r2"]
        with pytest.raises(RevisionConflictError):
            store.save_section_map(SectionMapSaveRequest(
                expected_section_map_revision=2, expected_source_revision=1,
                expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
                mapping=mapping,
            ))
    finally:
        store.close()


def test_section_map_rejects_extra_or_unreachable_sections() -> None:
    with pytest.raises(ValueError, match="at most 3"):
        SectionMap(
            sections=[
                StorySection(section_id="opening", title="开场", summary="选择开始。"),
                StorySection(section_id="ending-a", title="A", summary="结束 A。", ending=True),
                StorySection(section_id="ending-b", title="B", summary="结束 B。", ending=True),
                StorySection(section_id="unused", title="多余", summary="不可达。", ending=True),
            ],
            choice=SectionChoice(
                choice_id="choice-route", section_id="opening", prompt="选择？",
                outcomes=[
                    BranchOutcome(outcome_id="route-a", label="A", consequence="A。", ending_section_id="ending-a"),
                    BranchOutcome(outcome_id="route-b", label="B", consequence="B。", ending_section_id="ending-b"),
                ],
            ),
        )


def test_section_map_install_rejects_stale_inputs_and_never_overwrites_an_unrelated_graph(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    normal_graph = make_story_graph()
    store = storage.projects.create(FIXED_CHINESE_BRIEF, initial_stages=(
        InitialStage(stage=StageName.STORY_BIBLE, payload=make_story_bible().model_dump(mode="json", by_alias=True)),
        InitialStage(stage=StageName.STORY_GRAPH, payload=normal_graph.model_dump(mode="json", by_alias=True)),
    ))
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        outline = accepted.accepted_outline
        assert outline is not None
        mapped = store.save_section_map(SectionMapSaveRequest(
            expected_section_map_revision=0, expected_source_revision=1,
            expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
            mapping=SectionMap(
                sections=[
                    StorySection(section_id="entry", title="渡口", summary="船夫握着信。"),
                    StorySection(section_id="ending-a", title="妹妹", summary="妹妹收到信。", ending=True),
                    StorySection(section_id="ending-b", title="船长", summary="船长带走信。", ending=True),
                ],
                choice=SectionChoice(choice_id="delivery", section_id="entry", prompt="交给谁？", outcomes=[
                    BranchOutcome(outcome_id="sister", label="妹妹", consequence="她留下。", ending_section_id="ending-a"),
                    BranchOutcome(outcome_id="captain", label="船长", consequence="他启航。", ending_section_id="ending-b"),
                ]),
            ),
        ))
        assert mapped.accepted_section_map is not None and mapped.source is not None
        install = dict(
            expected_source_revision=1, expected_source_content_hash=mapped.source.content_hash,
            expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash,
            expected_section_map_revision=1, expected_section_map_content_hash=mapped.accepted_section_map.content_hash,
            expected_graph_revision=1,
        )
        with pytest.raises(RevisionConflictError):
            store.install_section_map_graph(SectionMapGraphInstallRequest(**(install | {"expected_source_content_hash": "0" * 64})))
        assert store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH) == normal_graph
        with pytest.raises(InvalidTransitionError, match="not source-map-owned"):
            store.install_section_map_graph(SectionMapGraphInstallRequest(**install))
        assert store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH) == normal_graph
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

        first.cancel_outline_candidate(request.job_id)
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

        # A malformed external folder does not itself terminally resolve the
        # persisted publication. The author explicitly cancels it before a
        # different frozen identity can be prepared.
        store.cancel_outline_candidate(request.job_id)
        next_request = CreativeHandoffRequest.model_validate(
            request.model_dump(mode="python") | {"job_id": "ch_" + "b" * 32}
        )
        store.prepare_outline_candidate(next_request)
        store.creative_handoff_exchange().write_package(next_request)
        ready = store.admit_outline_delivery(_deliver(store, next_request))
        accepted = store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=ready.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        with pytest.raises(InvalidTransitionError, match="accepted"):
            store.cancel_outline_candidate(ready.job_id)
        with pytest.raises(RevisionConflictError):
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=ready.job_id, expected_source_revision=1, expected_outline_revision=0,
            ))
        assert store.source_outline_state().accepted_outline == accepted.accepted_outline
    finally:
        store.close()


def test_cancelled_outline_publication_unblocks_lifecycle_and_rejects_late_install(
    tmp_path: Path,
) -> None:
    """A persisted prepared job stays busy until its own terminal cancellation."""

    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    source = _material()
    store.save_source_material(expected_source_revision=0, material=source)
    request = _request(project_id, source)
    store.prepare_outline_candidate(request)
    delayed_delivery = _deliver(store, request)
    lifecycle_revision = store.project().lifecycle_revision
    with pytest.raises(InvalidTransitionError, match="cancel the prepared"):
        store.save_source_material(expected_source_revision=1, material=_material("imported_text"))
    replacement = CreativeHandoffRequest.model_validate(
        request.model_dump(mode="python") | {"job_id": "ch_" + "b" * 32}
    )
    with pytest.raises(InvalidTransitionError, match="cancel the prepared"):
        store.prepare_outline_candidate(replacement)
    store.close()

    with pytest.raises(ProjectBusyError, match="source_outline_publication_active"):
        storage.projects.close_project(project_id)
    with pytest.raises(ProjectBusyError, match="source_outline_publication_active"):
        storage.lifecycle.archive(project_id, expected_lifecycle_revision=lifecycle_revision)
    with pytest.raises(ProjectBusyError, match="source_outline_publication_active"):
        storage.recovery.create_snapshot(project_id)
    store = storage.projects.open(project_id)
    try:
        with pytest.raises(LifecycleProjectBusyError):
            store.archive(expected_lifecycle_revision=lifecycle_revision)
    finally:
        store.close()

    store = storage.projects.open(project_id)
    try:
        cancelled = store.cancel_outline_candidate(request.job_id)
        assert cancelled.candidate is not None
        assert cancelled.candidate.status == "cancelled"
        with pytest.raises(CreativeHandoffError, match="cancelled"):
            store.admit_outline_delivery(delayed_delivery)
        with pytest.raises(CreativeHandoffError, match="cancelled"):
            store.outline_candidate_request(request.job_id)
        with pytest.raises(InvalidTransitionError, match="not ready"):
            store.accept_outline_candidate(OutlineAcceptRequest(
                job_id=request.job_id, expected_source_revision=1,
                expected_outline_revision=0,
            ))
        assert store.source_outline_state().accepted_outline is None
    finally:
        store.close()

    assert storage.recovery.create_snapshot(project_id).status == "complete"
    assert storage.projects.close_project(project_id) >= 1


def test_prepared_outline_publication_blocks_permanent_delete_of_historical_archive(
    tmp_path: Path,
) -> None:
    """The permanent-delete boundary also scans persisted prepared jobs.

    Normal archive first rejects a prepared job.  This setup represents an
    archived folder created before that guard existed, so the delete guard is
    independently proven against the actual persisted candidate row.
    """

    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    source = _material()
    store.save_source_material(expected_source_revision=0, material=source)
    store.prepare_outline_candidate(_request(project_id, source))
    # An older release could have persisted this impossible combination before
    # the shared lifecycle guard existed. Set up that exact historical row
    # directly, then prove the current permanent-delete boundary still refuses
    # to erase a project while its specialist can publish.
    project = store.project()
    with store.repository.engine.begin() as connection:
        connection.execute(update(ProjectRow).where(ProjectRow.id == project_id).values(
            lifecycle_status=ProjectLifecycleStatus.ARCHIVED.value,
            lifecycle_revision=project.lifecycle_revision + 1,
            archived_at=utc_now(),
            updated_at=utc_now(),
        ))
    archived = store.project()
    title = archived.brief.title
    store.close()

    with pytest.raises(ProjectBusyError, match="source_outline_publication_active"):
        storage.lifecycle.permanently_delete(
            project_id,
            expected_lifecycle_revision=archived.lifecycle_revision,
            confirmation_title=title,
        )
