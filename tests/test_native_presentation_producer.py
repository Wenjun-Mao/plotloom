"""Stage-owned schema/assignment guidance preserves the strict literal-text binder."""
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_package_projection import project_creative_package
from plotloom.native_bridge_presentation_contract import (
    PresentationSuggestions,
    native_presentation_suggestions,
    presentation_response_schema,
)
from plotloom.production_presentation import ProductionPresentationUpdateRequest, review_presentation
from tests.production_presentation_fixtures import _package, _updates

ROOT = Path(__file__).resolve().parents[1]


def presentation_case():
    package = _package()
    ids = [source.id for source in package.sources]
    request = CreativeHandoffRequest(job_id="ch_" + "a" * 32, project_id="provider-free-producer-proof",
        section_id="production-bridge", stage="bridge-presentation", expected_stage_revision=3,
        source={"proposal": {"revision": 3, "contentHash": "b" * 64}},
        input_artifacts={"presentation-source.json": package.model_dump(mode="json", by_alias=True),
            "presentation-schema.json": presentation_response_schema(ids)}, creative_brief="Frozen source only")
    entries = _updates(package)
    for entry in entries:
        entry["spans"] = [{"rendering": "", "reason": "", **span} for span in entry["spans"]]
    return package, request, {"entries": entries}


def test_all_five_roles_keep_valid_native_and_author_review_payloads_identical():
    package, request, candidate = presentation_case()
    before = deepcopy(candidate)
    advice = native_presentation_suggestions(request, candidate)
    assert {span.role for entry in advice.entries for span in entry.spans} == {
        "physical", "visible_text", "dialogue", "runtime_choice", "review_only"}
    assert advice.model_dump(mode="json", by_alias=True) == before == candidate
    reviewed = review_presentation(package, ProductionPresentationUpdateRequest(
        expected_proposal_revision=3, expected_content_hash="b" * 64, source_hash=package.source_hash,
        reviewed_complete=True, entries=advice.model_dump(mode="json")["entries"]))
    assert reviewed.reviewed and reviewed.frozen_evidence == package.frozen_evidence
    assert reviewed.runtime_choice == package.runtime_choice
    assert [item.source_text for item in reviewed.sources] == [item.source_text for item in package.sources]
    assert not package.reviewed and all(not item.spans for item in package.sources)


def test_response_schema_encodes_literal_rendering_with_required_bounded_fields():
    package, request, _ = presentation_case()
    schema = request.input_artifacts["presentation-schema.json"]
    entry = schema["$defs"]["PresentationSuggestionEntry"]
    assert entry["properties"]["id"]["enum"] == [source.id for source in package.sources]
    assert schema["properties"]["entries"]["minItems"] == len(package.sources)
    assert schema["properties"]["entries"]["maxItems"] == len(package.sources)
    spans = entry["properties"]["spans"]
    assert (spans["minItems"], spans["maxItems"]) == (1, 64)
    variants = spans["items"]["discriminator"]["mapping"]
    assert set(variants) == {"physical", "visible_text", "dialogue", "runtime_choice", "review_only"}
    assert len(spans["items"]["oneOf"]) == 2
    for role, reference in variants.items():
        shape = schema["$defs"][reference.rsplit("/", 1)[1]]
        assert set(shape["required"]) == {"start", "end", "role", "rendering", "reason"}
        assert shape["additionalProperties"] is False
        assert shape["properties"]["reason"]["maxLength"] == 2000
        rendering = shape["properties"]["rendering"]
        if role == "physical":
            assert rendering["minLength"] == 1 and rendering["maxLength"] == 12000
        else:
            assert rendering["const"] == "" and rendering["type"] == "string"


@pytest.mark.parametrize("role", ["visible_text", "dialogue", "runtime_choice", "review_only"])
@pytest.mark.parametrize("rendering", ["copied source words", " ", "🙂"])
def test_nonphysical_rendering_is_rejected_at_native_schema_without_coercion(role, rendering):
    _, _, candidate = presentation_case()
    span = next(span for entry in candidate["entries"] for span in entry["spans"] if span["role"] == role)
    span["rendering"] = rendering
    before = deepcopy(candidate)
    with pytest.raises(ValidationError) as caught:
        PresentationSuggestions.model_validate(candidate)
    assert any(error["type"] == "literal_error" and error["loc"][-1] == "rendering"
        for error in caught.value.errors(include_input=False))
    assert candidate == before


@pytest.mark.parametrize("mutation", ["missing-field", "extra-field", "overlong-physical", "overlong-reason", "gap", "omitted", "dialogue-ownership"])
def test_schema_and_unchanged_binder_keep_existing_refusals(mutation):
    _, request, candidate = presentation_case()
    span = candidate["entries"][0]["spans"][0]
    if mutation == "missing-field": span.pop("reason")
    if mutation == "extra-field": span["sourceText"] = "not model-owned"
    if mutation == "overlong-physical": span["rendering"] = "x" * 12001
    if mutation == "overlong-reason": span["reason"] = "x" * 2001
    if mutation == "gap": span["start"] = 1
    if mutation == "omitted": candidate["entries"].pop()
    if mutation == "dialogue-ownership": span.update(role="dialogue", rendering="")
    with pytest.raises(ValueError): native_presentation_suggestions(request, candidate)


@pytest.mark.parametrize("backend", ["codex_exec", "specialist_chat"])
def test_exact_frozen_assignment_states_role_rule_and_correct_validation_owner(tmp_path, backend):
    _, request, _ = presentation_case()
    pin = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
    projected, assignment, _, _ = project_creative_package(tmp_path / "job", request, pin,
        executor_backend=backend, plotloom_code_revision="d" * 40 if backend == "codex_exec" else None)
    text = assignment.decode()
    assert "fully read docs/creative-workflow/native-bridge-presentation.md" in text
    assert 'rendering to exactly the empty string ""' in text
    assert "visible_text, dialogue, runtime_choice and review_only" in text
    assert "Only physical spans have faithful nonempty rendering" in text
    assert projected["inputArtifacts"]["presentation-schema.json"] == request.input_artifacts["presentation-schema.json"]
    if backend == "codex_exec":
        assert "do not run validators or renderers" in text
        assert "trusted host must successfully validate and render before publishing completion" in text
        assert "validate" in {step["stepId"] for step in projected["validationPlan"]["steps"]}
    else:
        assert "Both must succeed before publishing completion" in text
    skill = (ROOT / ".agents/skills/plotloom-presentation-specialist/SKILL.md").read_text()
    assert 'rendering: ""' in skill and "Both validation and\nrendering must succeed" in skill
    assert "candidate-only precedence" in skill
