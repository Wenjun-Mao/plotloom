"""The specialist transports trusted linkage; receiving never reconstructs it."""

from pathlib import Path

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.test_project_storage_art import (
    _accepted_f4_script,
    _deliver_stage,
    _pilot_script,
)


@pytest.fixture
def prepared_script(tmp_path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        candidate, request = store.prepare_script_candidate("ch_" + "e" * 32)
        yield store, candidate, request
    finally:
        store.close()


def test_primary_brief_and_skill_require_emitting_frozen_linkage(prepared_script):
    _store, candidate, request = prepared_script
    expected = [item.model_dump(mode="json", by_alias=True) for item in candidate.binding.section_bindings]
    assert request.input_artifacts["script-admission.json"]["sectionBindings"] == expected
    assert "Copy script-admission.json.sectionBindings unchanged into top-level script.json.sectionBindings" in request.creative_brief
    assert "exact ordered sectionBindings array and episode set/cardinality" in request.creative_brief
    assert "upstream validator does not check this extension" in request.creative_brief
    skill = Path(".agents/skills/plotloom-shuohao-specialist/SKILL.md").read_text()
    assert "top-level `script.json.sectionBindings`" in skill
    assert "candidate episode numbers" in skill and "same cardinality" in skill


@pytest.mark.parametrize("defect", ["missing", "permuted", "episode-set"])
def test_bad_linkage_is_rejected_without_rewriting_delivery(prepared_script, defect):
    store, _candidate, request = prepared_script
    script = _pilot_script()
    if defect == "missing":
        script.pop("sectionBindings")
    elif defect == "permuted":
        script["sectionBindings"] = list(reversed(script["sectionBindings"]))
    else:
        script["episodes"][0]["ep"] = 9
    delivery = _deliver_stage(store, request, "script.json", script, "invalid-linkage")
    paths = store.creative_handoff_exchange().write_package(request, store.creative_handoff_execution_pin(request))
    root = Path(paths["deliveryPath"])
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    with pytest.raises(ValueError, match="sectionBindings"):
        store.admit_script_delivery(delivery)
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before
    assert delivery.candidate == script
    assert store.script_state().candidate.status == "prepared"
