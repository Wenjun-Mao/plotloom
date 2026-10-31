"""Frozen production-brief source bindings, independent of adapter prose."""
from .contract_hash import stable_hash
from .production_brief_display import DISPLAY_VERSION

BRIEF_VERSION = "plotloom.production-brief.v2"


def source_groups(snapshot):
    return (
        ("shot", "画面、动作、镜头与连续性", "Picture, action, camera and continuity", snapshot["shot"]),
        ("context", "人物、场景、表演与对白原文", "Characters, scene, performance and exact dialogue", snapshot["resolvedContext"]),
        ("presentation", "画面文字与呈现方式", "Exact visible words and presentation", snapshot.get("shotPresentation")),
        ("references", "已审阅的首尾帧、人物与物料参考", "Reviewed frames, identities and material references", {
            "keyframe": snapshot["keyframe"], "endFrame": snapshot.get("endFrame"),
            "identityLineage": snapshot.get("identityLineage", []), "samePersonReviewId": snapshot.get("samePersonReviewId")}),
        ("timing", "作者播放时长与原片窗口", "Authored timing and source window", {
            "sourceTiming": snapshot["sourceTiming"], "playbackIntent": snapshot["playbackIntent"]}),
        ("settings", "本次生成规格与可见效果", "Generation settings and visible effects", {
            "provider": snapshot["provider"], "request": snapshot["request"]}),
    )


def assert_frozen_brief(snapshot, brief):
    """Check recorded bytes/source; native evidence separately binds authority."""
    keys = {"version", "displayVersion", "contentLocale", "sourceHash", "sections",
        "adapterConstraints", "discretion", "conflicts", "briefHash"}
    if (not isinstance(brief, dict) or set(brief) != keys
            or brief["version"] != BRIEF_VERSION or brief["displayVersion"] != DISPLAY_VERSION
            or brief["contentLocale"] != snapshot["languageContract"]["contentLocale"]
            or brief["sourceHash"] != stable_hash({k: v for k, v in snapshot.items() if k != "executionRetry"})
            or brief["briefHash"] != stable_hash({k: v for k, v in brief.items() if k != "briefHash"})):
        raise ValueError("frozen production brief identity changed")
    groups = source_groups(snapshot)
    sections = brief["sections"]
    if not isinstance(sections, list) or len(sections) != len(groups):
        raise ValueError("frozen production brief source coverage changed")
    for section, (identifier, _, _, content) in zip(sections, groups, strict=True):
        if (not isinstance(section, dict) or set(section) != {"id", "label", "content", "items"}
                or section["id"] != identifier or section["content"] != content
                or not isinstance(section["label"], str) or not section["label"].strip()
                or not isinstance(section["items"], list)
                or any(not isinstance(item, dict)
                    or set(item) not in ({"path", "label", "value"}, {"path", "label", "value", "kind"})
                    or ("kind" in item and item["kind"] not in {"text", "exact_text"})
                    or any(not isinstance(item[key], str) for key in ("path", "label", "value"))
                    for item in section["items"])):
            raise ValueError("frozen production brief source or display shape changed")
    constraints = brief["adapterConstraints"]
    if (not isinstance(constraints, list) or len(constraints) != 4
            or any(not isinstance(text, str) or not text.strip() for text in constraints)
            or not isinstance(brief["discretion"], str) or not brief["discretion"].strip()
            or not isinstance(brief["conflicts"], list)
            or any(not isinstance(item, dict) or set(item) != {"path", "message"}
                or any(not isinstance(item[key], str) for key in ("path", "message"))
                for item in brief["conflicts"])):
        raise ValueError("frozen production brief constraints changed shape")
