"""Read-only production meaning projected from the existing frozen owners."""
from copy import deepcopy

from .contract_hash import stable_hash
from .production_brief_display import DISPLAY_VERSION, readable_sections

BRIEF_VERSION = "plotloom.production-brief.v2"


def production_brief(snapshot):
    """No prose generation, translation or writes: edits belong to source owners."""
    language = snapshot["languageContract"]["contentLocale"]
    english = language == "en-US"
    shot, context = snapshot["shot"], snapshot["resolvedContext"]
    groups = (
        ("shot", "画面、动作、镜头与连续性", "Picture, action, camera and continuity", shot),
        ("context", "人物、场景、表演与对白原文", "Characters, scene, performance and exact dialogue", context),
        ("presentation", "画面文字与呈现方式", "Exact visible words and presentation", snapshot.get("shotPresentation")),
        ("references", "已审阅的首尾帧、人物与物料参考", "Reviewed frames, identities and material references", {
            "keyframe": snapshot["keyframe"], "endFrame": snapshot.get("endFrame"),
            "identityLineage": snapshot.get("identityLineage", []), "samePersonReviewId": snapshot.get("samePersonReviewId")}),
        ("timing", "作者播放时长与原片窗口", "Authored timing and source window", {
            "sourceTiming": snapshot["sourceTiming"], "playbackIntent": snapshot["playbackIntent"]}),
        ("settings", "本次生成规格与可见效果", "Generation settings and visible effects", {
            "provider": snapshot["provider"], "request": snapshot["request"]}),
    )
    body = {"version": BRIEF_VERSION, "displayVersion": DISPLAY_VERSION, "contentLocale": language,
        "sourceHash": stable_hash({key:value for key,value in snapshot.items() if key != "executionRetry"}), "sections": [
            {"id": key, "label": en if english else zh, "content": deepcopy(value)}
            for key, zh, en, value in groups],
        "adapterConstraints": ([
            "Preserve the reviewed first frame's style, subjects, objects and positions in one continuous shot.",
            "Speak each authored cue once in its authored language; preserve off-screen and nonspoken roles.",
            "Show only exact authored visible words; do not add captions, replies, speech or sound events.",
            "Follow the reviewed ending frame when one is selected; use the frozen timing and input-frame treatment."] if english else [
            "以已审阅首帧的风格、人物、物体和位置为依据，连续完成此镜头。",
            "各条作者对白只说一次，保留原语言、画外音与非发声角色。",
            "仅显示作者指定的原文，不新增字幕、回复、对白或声音事件。",
            "如已选择尾帧则向该尾帧衔接，遵循冻结的时长和首尾帧比例处理。"]),
        "discretion": ("Faithful wording only; no new creative facts, speech, text or sounds."
            if english else "仅可忠实调整表述；不可新增创作事实、对白、文字或声音。"),
        "conflicts": _adapter_conflicts(snapshot)}
    body["sections"], display_conflicts = readable_sections(snapshot, body["sections"])
    body["conflicts"] += display_conflicts
    return body | {"briefHash": stable_hash(body)}


def _adapter_conflicts(snapshot):
    """Refuse representational losses before a draft or provider dispatch."""
    english = snapshot.get("languageContract", {}).get("contentLocale") == "en-US"
    conflicts = []
    def add(path, zh, en):
        conflicts.append({"path": path, "message": en if english else zh})
    events = snapshot["shot"].get("audioPlan", {}).get("events", [])
    for index, event in enumerate(events):
        if event.get("kind") not in {"ambience", "sound_effect", "diegetic_sound", "diegetic_music", "score"}:
            add(f"shot.audioPlan.events.{index}.kind", "H3 无法表达此声音角色；请回到声音计划调整要求。",
                "H3 cannot represent this sound role; revise the owning audio plan.")
    cues = snapshot["resolvedContext"].get("dialogueCues", [])
    for index, cue in enumerate(cues):
        if cue.get("text") and cue.get("language") not in {"zh-CN", "en-US"}:
            add(f"resolvedContext.dialogueCues.{index}.language",
                "当前 H3 工作流不支持此对白语言；请在对白源明确支持的语言。",
                "This H3 workflow does not support the cue language; correct the owning dialogue cue.")
    return conflicts


def adaptation_conflicts(snapshot):
    return production_brief(snapshot)["conflicts"]


def assert_adaptable(snapshot):
    conflicts = adaptation_conflicts(snapshot)
    if conflicts:
        raise ValueError("; ".join(item["path"] + ": " + item["message"] for item in conflicts))
