"""Reusable, non-collected builders for production presentation tests."""

from plotloom.production_presentation import (
    ProductionPresentationUpdateRequest,
    prepare_presentation,
)


def _package():
    choice = {
        "choiceId": "turn",
        "sectionId": "opening",
        "prompt": "怎么办？",
        "outcomes": [
            {"outcomeId": "a", "label": "赴约"},
            {"outcomeId": "b", "label": "回家"},
        ],
    }
    script = {
        "sectionBindings": [{"episode": 1, "sectionId": "opening"}],
        "episodes": [
            {
                "ep": 1,
                "scenes": [
                    {
                        "flow": [
                            {"action": "停步。抬眼。"},
                            {"action": "留在门廊。显示怎么办？赴约或回家。"},
                            {"action": "输入今晚不去了，明天见。"},
                            {"action": "发送，保留已发文字，不出现新回信。"},
                            {"line": "你好。", "speaker": "C01"},
                        ]
                    }
                ],
            }
        ],
    }
    board = {
        "episodes": [
            {
                "ep": 1,
                "segments": [
                    {"sceneIndex": 1, "cuts": [{"frame": "门廊画面。预留选择区域。"}]}
                ],
            }
        ]
    }
    return prepare_presentation(
        inputs={"scriptRevision": 3},
        script=script,
        storyboard=board,
        mapping={"choices": [choice]},
    )


def _updates(pkg):
    result = []
    for source in pkg.sources:
        text = source.source_text
        if source.kind == "dialogue":
            spans = [{"start": 0, "end": len(text), "role": "dialogue"}]
        elif "显示" in text:
            cut = text.index("显示")
            spans = [
                {"start": 0, "end": cut, "role": "physical", "rendering": text[:cut]},
                {
                    "start": cut,
                    "end": len(text),
                    "role": "runtime_choice",
                    "reason": "Exact frozen author choice belongs to player",
                },
            ]
        elif "预留" in text:
            cut = text.index("预留")
            spans = [
                {"start": 0, "end": cut, "role": "physical", "rendering": text[:cut]},
                {
                    "start": cut,
                    "end": len(text),
                    "role": "review_only",
                    "reason": "Runtime choices do not require generated UI",
                },
            ]
        elif "今晚" in text:
            cut = text.index("今晚")
            spans = [
                {
                    "start": 0,
                    "end": cut,
                    "role": "physical",
                    "rendering": "在手机上输入完整回复。",
                },
                {"start": cut, "end": len(text), "role": "visible_text"},
            ]
        else:
            spans = [
                {"start": 0, "end": len(text), "role": "physical", "rendering": text}
            ]
        result.append({"id": source.id, "spans": spans})
    return result


def _request(pkg, entries):
    return ProductionPresentationUpdateRequest(
        expected_proposal_revision=1,
        expected_content_hash="a" * 64,
        source_hash=pkg.source_hash,
        reviewed_complete=True,
        entries=entries,
    )
