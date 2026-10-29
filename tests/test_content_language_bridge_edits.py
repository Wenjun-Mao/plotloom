"""Review revision movement cannot prevent checks or bless changed sources."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest

from plotloom.content_language_candidates import load_generated_candidate
from plotloom.exceptions import InvalidTransitionError
from tests.content_language_fixtures import original_request


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
@pytest.mark.parametrize("mutation", [None, "source", "inputs", "intent"])
def test_edited_generated_candidate_checks_current_sources_after_review_revision_advanced(stage, mutation):
    original = original_request(stage)
    context = {"brief": {"language": "zh-CN"}, "scenes": [{"scriptScene": "原始场景。"}],
        "proposal": {"revision": 1, "contentHash": "a"*64, "inputs": {"script": 2}, "replacementTarget": {}}}
    intent = {"entries": [{"id": "scene", "text": "原始意图。"}]}
    original.source = deepcopy(context)
    if stage == "bridge-presentation":
        original.source["intentPackage"] = deepcopy(intent)
    # The native delivery / explicit creator review advances only the bridge
    # proposal revision; complete original source facts remain unchanged.
    context["proposal"] |= {"revision": 2, "contentHash": "b"*64}
    if mutation == "source": context["scenes"][0]["scriptScene"] = "不同来源。"
    if mutation == "inputs": context["proposal"]["inputs"]["script"] = 3
    if mutation == "intent": intent["entries"][0]["text"] = "不同意图。"
    row = SimpleNamespace(project_id=original.project_id, native_request=original.model_dump(mode="json", by_alias=True),
                          candidate={"lang": "zh", "entries": []}, status="ready")

    @contextmanager
    def read():
        yield SimpleNamespace(get=lambda *_args: row)

    calls = []

    def sources(_project, **target):
        calls.append(target)
        return deepcopy(context), []

    proposal = SimpleNamespace(revision=2, content_hash="b"*64,
        intent_package=SimpleNamespace(model_dump=lambda **_kwargs: deepcopy(intent)))
    store = SimpleNamespace(manifest=SimpleNamespace(project_id=original.project_id),
        repository=SimpleNamespace(_read=read, production_bridge_intent=SimpleNamespace(source_context=sources)),
        production_bridge_state=lambda: SimpleNamespace(proposal=proposal))
    edited = {"lang": "zh", "entries": [{"id": "scene", "suggestedText": "修改后的意图。"}]}
    blocked = mutation in {"source", "inputs"} or mutation == "intent" and stage == "bridge-presentation"
    if blocked:
        with pytest.raises(InvalidTransitionError, match="原始来源或意图"):
            load_generated_candidate(store, stage, original.job_id, edited)
    else:
        request, candidate = load_generated_candidate(store, stage, original.job_id, edited)
        assert request == original and candidate == edited
    assert calls == [{"expected_revision": 2, "expected_hash": "b"*64}]
