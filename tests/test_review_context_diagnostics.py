"""Current Cast/Art diagnostics retain evidence without changing admission."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest, ArtReviewState
from plotloom.art_style import freeze_art_style
from plotloom.cast_contracts import CastReopenRequest, CastReviewState
from plotloom.cast_style import freeze_cast_style
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import InvalidTransitionError
from plotloom.graph_safety_diagnostics import transition_error_content
from plotloom.persistence.project.art import ProjectArtPersistence
from plotloom.persistence.project.cast import ProjectCastPersistence
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.review_context_diagnostics import binding_diagnostics
from plotloom.source_outline_contracts import OutlineReopenRequest, SourceMaterial
from tests.art_delivery_fixtures import _binding, _deliver
from tests.creative_delivery_fixtures import _prepare_art_context


@pytest.mark.parametrize("stage", ["cast", "art"])
def test_missing_context_preparation_refusal_is_typed(
    tmp_path: Path, stage: str
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    before = client.get(f"/api/v2/projects/{project_id}/{stage}").json()
    response = client.post(
        f"/api/v2/projects/{project_id}/{stage}/candidates",
        json={"renderStyle": "realistic"},
    )
    assert response.status_code == 409
    assert response.json() == {
        "code": "review_context_not_current",
        "message": "an accepted source, outline, current section map, and installed graph are required before preparing cast",
        "diagnostic": {
            "code": "source_context_not_ready",
            "owner": "source",
            "technicalMessage": response.json()["message"],
            "field": None,
        },
    }
    assert client.get(f"/api/v2/projects/{project_id}/{stage}").json() == before


@pytest.mark.parametrize(
    "change,code,owner",
    [
        ("source", "source_context_not_ready", "source"),
        ("outline", "source_context_not_ready", "source"),
        ("cast", "accepted_cast_not_current", "characters"),
        ("style", "installed_graph_not_current", "source"),
    ],
)
def test_art_stale_read_names_the_actual_owner_and_preserves_evidence(
    tmp_path: Path, change: str, code: str, owner: str
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "t" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        accepted = store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        ).accepted_art
        report = store.art_candidate_report(candidate.job_id)
        cast = store.cast_state().accepted_cast
        if change == "source":
            store.save_source_material(
                expected_source_revision=1,
                material=SourceMaterial(
                    kind="synopsis",
                    title="Tide Light",
                    text="A changed source.",
                    attribution="fixture",
                    rights_declaration="fixture",
                    adaptation_intent="fixture",
                ),
            )
        elif change == "outline":
            store.reopen_outline(OutlineReopenRequest(expected_outline_revision=1))
        elif change == "cast":
            store.reopen_cast(CastReopenRequest(expected_cast_revision=1))
        else:
            project = store.project()
            store.update_brief(
                project.brief.model_copy(
                    update={"visual_style": "Changed author direction"}
                ),
                expected_revision=project.revision,
            )
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    response = client.get(f"/api/v2/projects/{project_id}/art")
    assert response.status_code == 200
    state = ArtReviewState.model_validate(response.json())
    assert state.status == "stale"
    assert state.stale_reasons[0].code == code
    assert state.stale_reasons[0].owner == owner
    assert state.accepted_art == accepted
    assert client.get(f"/api/v2/projects/{project_id}/cast").json()[
        "acceptedCast"
    ] == cast.model_dump(mode="json", by_alias=True)
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/art/candidates/{candidate.job_id}/report"
        ).text
        == report
    )
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/art-reference-proposals",
            json={
                "subjectType": "scene",
                "subjectId": "S01",
                "renderDirection": "No people.",
            },
        ).status_code
        == 409
    )
    refused = client.post(
        f"/api/v2/projects/{project_id}/art/candidates",
        json={"renderStyle": "realistic"},
    )
    assert refused.status_code == 409
    assert refused.json()["diagnostic"] == response.json()["staleReasons"][0]
    assert client.get(f"/api/v2/projects/{project_id}/art").json() == response.json()


def test_art_render_contract_diagnostic_when_shared_context_is_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _binding().model_copy(
        update={"render_contract": freeze_art_style("realistic", "Earlier direction")}
    )
    access = SimpleNamespace(
        rows=SimpleNamespace(
            project=lambda *_: SimpleNamespace(brief=FIXED_CHINESE_BRIEF.model_dump())
        )
    )
    owner = ProjectArtPersistence(access, None)
    # Isolate the style comparison; public Brief changes invalidate the graph first.
    monkeypatch.setattr(owner, "_context", lambda *_: (binding, {}, {}, {}, {}))
    reasons = owner._stale(None, "fixture", binding)
    assert [(item.code, item.owner, item.field) for item in reasons] == [
        ("art_render_contract_changed", "art", None)
    ]
    assert (
        reasons[0].technical_message
        == "art render contract is not current; prepare a new art task"
    )


@pytest.mark.parametrize(
    "stage,hash_field", [("art", "adapterHash"), ("cast", "implementationHash")]
)
def test_implementation_only_contract_change_does_not_claim_author_changed_direction(
    monkeypatch, stage, hash_field
):
    direction = FIXED_CHINESE_BRIEF.visual_direction
    freeze = freeze_art_style if stage == "art" else freeze_cast_style
    contract = freeze("realistic", direction)
    contract[hash_field] = "f" * 64
    binding = _binding().model_copy(update={"render_contract": contract})
    access = SimpleNamespace(
        rows=SimpleNamespace(
            project=lambda *_: SimpleNamespace(brief=FIXED_CHINESE_BRIEF.model_dump())
        )
    )
    owner = (
        ProjectArtPersistence(access, None)
        if stage == "art"
        else ProjectCastPersistence(access)
    )
    monkeypatch.setattr(owner, "_context", lambda *_: (binding, {}, {}, {}, {}))
    reasons = owner._stale(None, "fixture", binding)
    assert [item.code for item in reasons] == [f"{stage}_render_contract_changed"]
    assert (
        reasons[0].technical_message
        == f"{stage} render contract is not current; prepare a new {stage} task"
    )
    assert contract["authorDirection"] == direction


def test_binding_diagnostics_keep_field_order_and_raw_text() -> None:
    frozen = _binding()
    current = frozen.model_copy(
        update={"source_revision": 2, "cast_content_hash": "f" * 64}
    )
    reasons = binding_diagnostics(
        current,
        frozen,
        (("source_revision", "source"), ("cast_content_hash", "accepted cast")),
    )
    assert [
        (item.code, item.owner, item.field, item.technical_message) for item in reasons
    ] == [
        (
            "binding_revision_changed",
            "source",
            "source_revision",
            "source revision changed",
        ),
        (
            "binding_content_changed",
            "characters",
            "cast_content_hash",
            "accepted cast content changed",
        ),
    ]
    assert binding_diagnostics(frozen, frozen, (("source_revision", "source"),)) == []


@pytest.mark.parametrize("model", [CastReviewState, ArtReviewState])
def test_old_string_stale_contract_is_not_accepted(model: type) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "status": "stale",
                "staleReasons": ["raw text"],
                "acceptedReviewState": {"status": "missing", "staleReasons": []},
            }
        )


def test_ordinary_invalid_transition_format_remains_unchanged() -> None:
    assert transition_error_content(InvalidTransitionError("ordinary refusal")) == {
        "code": "invalid_transition",
        "message": "ordinary refusal",
    }
