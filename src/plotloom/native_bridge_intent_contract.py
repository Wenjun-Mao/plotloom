"""Strict native suggestions binding and deterministic, inert review report."""
from html import escape
from typing import Any

from .creative_handoff_contracts import CreativeHandoffRequest
from .production_bridge_intent_contract import bind_intent_suggestions
from .language_policy import assert_candidate_report_language, report_locale


def native_intent_suggestions(request: CreativeHandoffRequest, candidate: Any) -> dict[str, str]:
    if request.stage != "bridge-intent":
        raise ValueError("expected a native bridge intent request")
    assert_candidate_report_language(candidate, request.input_artifacts)
    targets = request.input_artifacts["targets.json"]["entries"]
    suggestions = bind_intent_suggestions(candidate, [entry["id"] for entry in targets])
    if any(suggestions[entry["id"]].strip() == entry["sourceExcerpt"].strip() for entry in targets):
        raise ValueError("intent suggestion merely repeated a source excerpt")
    return suggestions


def render_native_intent_report(request: CreativeHandoffRequest, candidate: Any) -> bytes:
    suggestions = native_intent_suggestions(request, candidate)
    en = report_locale(request.input_artifacts) == "en"
    title = "Dramatic intent suggestions" if en else "戏剧意图建议"
    scene, beat = ("Scene objective", "Beat purpose") if en else ("场次目标", "节拍目的")
    source, suggestion = ("Source excerpt", "Suggestion") if en else ("来源摘录", "建议")
    notice = ("Candidate for whole-package creator review; no creator confirmation or media acceptance is implied. "
        "The frozen request binds sources and production targets." if en else
        "候选仅供作者整包审阅，尚未确认或接受媒体；来源与投产目标由冻结请求绑定。")
    rows = "".join(
        f'<section><h2>{escape(entry["id"])} · {scene if entry["targetKind"] == "scene_objective" else beat}</h2>'
        f'<p>{source}: {escape(entry["sourceExcerpt"])}</p><p>{suggestion}: {escape(suggestions[entry["id"]])}</p></section>'
        for entry in request.input_artifacts["targets.json"]["entries"]
    )
    identity = request.source["proposal"]
    identity_label = "Job / frozen proposal" if en else "任务 / 冻结提案"
    return (f'<!doctype html><html lang="{"en-US" if en else "zh-CN"}"><meta charset="utf-8"><title>{title}</title>'
        f'<style>body{{max-width:900px;margin:32px auto;padding:16px;font:18px sans-serif;line-height:1.7;overflow-wrap:anywhere}}'
        f'section{{border-top:1px solid #ccc}}</style><h1>Codex · {title}</h1><p>{notice}</p>'
        f'<p>{identity_label} {escape(request.job_id)} · r{identity["revision"]} · {escape(identity["contentHash"])}</p>'
        f'{rows}</html>').encode("utf-8")
