"""Core production presentation segmentation, review, and projection contracts."""

import pytest

from plotloom.production_presentation import project_presentation, review_presentation
from plotloom.production_timing import source_seconds_to_milliseconds
from tests.production_presentation_fixtures import _package, _request, _updates


@pytest.mark.parametrize(
    "seconds,units",
    [
        (2.5, 2500),
        (1.001, 1001),
        (5, 5000),
        (10**35 + 1, (10**35 + 1) * 1000),
    ],
)
def test_exact_ms(seconds, units):
    assert source_seconds_to_milliseconds(seconds) == units


@pytest.mark.parametrize(
    "seconds",
    [
        True,
        False,
        0,
        -1,
        float("nan"),
        float("inf"),
        -float("inf"),
        2.5001,
        "2.5",
        None,
    ],
)
def test_unrepresentable_ms(seconds):
    with pytest.raises(ValueError):
        source_seconds_to_milliseconds(seconds)


def test_complete_review_preserves_order_text_constraints_and_runtime_separation():
    pkg = _package()
    reviewed = review_presentation(pkg, _request(pkg, _updates(pkg)))
    raw = {
        "sceneBeats": {
            "beats": [
                {"id": source.target_id}
                for source in pkg.sources
                if source.kind != "composition"
            ]
        },
        "storyboard": {
            "shots": [{"id": "opening-s1-c1", "title": "作者的镜头名"}],
            "shotBeatLinks": [
                {"shotId": "opening-s1-c1", "beatId": f"opening-s1-b{i}"}
                for i in range(1, 6)
            ],
        },
    }
    projected = project_presentation(raw, reviewed)
    shot = projected["storyboard"]["shots"][0]
    assert shot["title"] == "作者的镜头名"
    assert shot["action"].startswith("停步。抬眼。\n留在门廊。")
    assert "发送，保留已发文字，不出现新回信。" in shot["action"]
    assert "怎么办" not in str(shot) and "预留" not in str(shot)
    assert shot["visibleTexts"][0]["text"] == "今晚不去了，明天见。"
    assert "你好。" not in shot["action"]
    assert reviewed.runtime_choice == pkg.runtime_choice
    assert reviewed.frozen_evidence == pkg.frozen_evidence
    assert [source.source_hash for source in reviewed.sources] == [
        source.source_hash for source in pkg.sources
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "omitted",
        "duplicate",
        "gap",
        "overlap",
        "unassigned",
        "rewrite_visible",
        "dialogue_action",
        "hash",
    ],
)
def test_review_refuses_incomplete_or_wrong_authority(mutation):
    pkg = _package()
    entries = _updates(pkg)
    request = _request(pkg, entries)
    if mutation == "omitted":
        request.entries.pop()
    elif mutation == "duplicate":
        request.entries.append(request.entries[0])
    elif mutation == "gap":
        request.entries[0].spans[0].start = 1
    elif mutation == "overlap":
        request.entries[1].spans[1].start -= 1
    elif mutation == "unassigned":
        request.entries[0].spans[0].role = "unassigned"
    elif mutation == "rewrite_visible":
        request.entries[2].spans[1].rendering = "different words"
    elif mutation == "dialogue_action":
        request.entries[4].spans[0].role = "physical"
    elif mutation == "hash":
        request.source_hash = "b" * 64
    with pytest.raises(ValueError):
        review_presentation(pkg, request)


def test_dialogue_only_cut_keeps_spoken_words_exclusively_cue_owned():
    package = _package()
    reviewed = review_presentation(package, _request(package, _updates(package)))
    payload = {
        "sceneBeats": {
            "beats": [{"id": "opening-s1-b5"}],
            "dialogueCues": [{"id": "cue", "text": "你好。"}],
        },
        "storyboard": {
            "shots": [{"id": "opening-s1-c1"}],
            "shotBeatLinks": [{"shotId": "opening-s1-c1", "beatId": "opening-s1-b5"}],
        },
    }
    result = project_presentation(payload, reviewed)
    assert result["storyboard"]["shots"][0]["action"] == ""
    assert result["sceneBeats"]["dialogueCues"] == payload["sceneBeats"]["dialogueCues"]


@pytest.mark.parametrize("words", ["", "  ", "\t\n", "\u3000"])
def test_authored_visible_text_rejects_whitespace_only_without_normalizing(words):
    from plotloom.canonical_schema import AuthoredVisibleText

    with pytest.raises(ValueError):
        AuthoredVisibleText.model_validate(
            {"text": words, "sourceCoordinates": {}, "sourceContentHash": "a" * 64}
        )
