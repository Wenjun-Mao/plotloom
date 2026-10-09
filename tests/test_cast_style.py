"""Character style is explicit frozen direction, never inferred from Brief prose."""
from copy import deepcopy
import json
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.cast_style import CastPrepareRequest, STYLE_OWNER, cast_style_current, freeze_cast_style, validate_cast_style
from plotloom.api.project_folder_cast import register_project_folder_cast_routes


def styled_cast(contract):
    preset = contract["preset"]
    return {"style": contract["style"], "characters": [{"id": "C01", "image": {
        "style": preset["label"], "prompt": preset["render"], "sheet": preset["render"],
        "negativePrompt": preset["negative"], "tags": preset["tags"],
    }}]}


@pytest.mark.parametrize("style", ["live-action", "realistic", "ghibli"])
def test_frozen_style_roundtrip_and_direction_currentness(style):
    contract = freeze_cast_style(style, "冷光，磨损的蓝色外套")
    validate_cast_style(styled_cast(contract), contract)
    assert cast_style_current(contract, "冷光，磨损的蓝色外套")
    assert not cast_style_current(contract, "暖色")
    assert not cast_style_current(None, "冷光，磨损的蓝色外套")
    changed = deepcopy(contract)
    changed["preset"]["render"] = "substituted preset"
    assert not cast_style_current(changed, contract["authorDirection"])
    with pytest.raises(ValueError, match="stale"):
        validate_cast_style(styled_cast(contract), changed)


@pytest.mark.parametrize("change", ["style", "label", "prompt", "sheet", "negative", "painterly", "tags"])
def test_live_action_rejects_wrong_or_contradictory_style(change):
    contract = freeze_cast_style("live-action", "真人写实")
    cast = styled_cast(contract)
    image = cast["characters"][0]["image"]
    if change == "style": cast["style"] = "realistic"
    elif change == "label": image["style"] = "半写实厚涂"
    elif change in {"prompt", "sheet"}: image[change] = "A painted character"
    elif change == "negative": image["negativePrompt"] = "photorealistic"
    elif change == "painterly": image["prompt"] += ", painterly rendering"
    else: image["tags"] = ["anime"]
    with pytest.raises(ValueError):
        validate_cast_style(cast, contract)


def test_preparation_has_no_implicit_preset():
    with pytest.raises(ValueError): CastPrepareRequest.model_validate({})
    with pytest.raises(ValueError): CastPrepareRequest(render_style="unknown")
    with pytest.raises(ValueError, match="missing"):
        validate_cast_style({}, None)


def test_route_requires_an_explicit_supported_style_before_opening_a_project():
    def unexpected_open(_):
        pytest.fail("invalid preparation must not enter a project transaction")
    app = FastAPI()
    register_project_folder_cast_routes(app, unexpected_open)
    client = TestClient(app)
    endpoint = "/api/v2/projects/fixture/cast/candidates"
    assert client.post(endpoint).status_code == 422
    assert client.post(endpoint, json={}).status_code == 422
    assert client.post(endpoint, json={"renderStyle": "unknown"}).status_code == 422


def test_generation_entrypoint_retains_upstream_structure_checks(tmp_path):
    contract = freeze_cast_style("live-action", "真人写实")
    paths = {}
    for name, value in (("cast", styled_cast(contract)), ("contract", contract), ("request", {"source": {"text": "A woman enters."}})):
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(json.dumps(value), encoding="utf-8")
    result = subprocess.run(["node", str(STYLE_OWNER), "validate", str(paths["cast"]), "--request", str(paths["request"]), "--contract", str(paths["contract"])], capture_output=True, text=True)
    assert result.returncode != 0
    assert "summary" in result.stderr
    assert "persona" in result.stderr


@pytest.mark.parametrize("change", ["missing", "implementation", "brief"])
def test_persisted_cast_style_change_revokes_art_consumption_without_mutation(tmp_path, change):
    from sqlalchemy import select
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from plotloom.project_storage.composition import ProjectFolderStorage
    from plotloom.persistence.schema.project_cast import CastRevisionRow
    from plotloom.review_context_diagnostics import ReviewContextError
    from tests.test_project_storage_art import _prepare_art_context

    store = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application").projects.create(FIXED_CHINESE_BRIEF)
    try:
        _prepare_art_context(store)
        assert store.cast_state().status == "accepted"
        if change == "brief":
            project = store.project()
            store.update_brief(project.brief.model_copy(update={"visual_style": "Changed photographic direction"}), expected_revision=project.revision)
        else:
            # Corrupt only this disposable test receipt to represent absent/stale authority.
            with store.repository._write() as session:
                accepted = session.scalar(select(CastRevisionRow).where(CastRevisionRow.project_id == store.manifest.project_id))
                binding = deepcopy(accepted.binding)
                if change == "missing": binding.pop("renderContract")
                else: binding["renderContract"]["implementationHash"] = "0" * 64
                accepted.binding = binding
        state = store.cast_state()
        assert state.status == "stale"
        # A Brief save invalidates the installed graph before Cast is evaluated.
        # Report that prerequisite first rather than masking it with a style error.
        expected_reason = "installed_graph_not_current" if change == "brief" else "cast_render_contract_changed"
        assert expected_reason in {reason.code for reason in state.stale_reasons}
        assert not cast_style_current(state.accepted_cast.binding.render_contract, store.project().brief.visual_direction)
        before = store.art_state()
        with pytest.raises(ReviewContextError) as error:
            store.prepare_art_candidate("ch_" + "n" * 32, render_style="realistic")
        assert error.value.diagnostic.code == ("installed_graph_not_current" if change == "brief" else "accepted_cast_not_current")
        assert store.art_state() == before
        assert store.cast_state() == state
    finally:
        store.close()
