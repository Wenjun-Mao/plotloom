"""Strict native suggestions binding and deterministic, inert review report."""
from html import escape
from typing import Any

from .creative_handoff_contracts import CreativeHandoffRequest
from .production_bridge_intent_contract import bind_intent_suggestions


def native_intent_suggestions(request: CreativeHandoffRequest, candidate: Any) -> dict[str, str]:
    if request.stage != "bridge-intent":
        raise ValueError("expected a native bridge intent request")
    targets = request.input_artifacts["targets.json"]["entries"]
    suggestions = bind_intent_suggestions(candidate, [entry["id"] for entry in targets])
    if any(suggestions[entry["id"]].strip() == entry["sourceExcerpt"].strip() for entry in targets):
        raise ValueError("intent suggestion merely repeated a source excerpt")
    return suggestions


def render_native_intent_report(request: CreativeHandoffRequest, candidate: Any) -> bytes:
    suggestions = native_intent_suggestions(request, candidate)
    rows = "".join(
        f'<section><h2>{escape(entry["id"])} · {"场次目标" if entry["targetKind"] == "scene_objective" else "节拍目的"}</h2>'
        f'<p>来源摘录：{escape(entry["sourceExcerpt"])}</p><p>建议：{escape(suggestions[entry["id"]])}</p></section>'
        for entry in request.input_artifacts["targets.json"]["entries"]
    )
    identity = request.source["proposal"]
    return (f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>戏剧意图候选报告</title>'
            f'<style>body{{max-width:900px;margin:32px auto;padding:16px;font:18px sans-serif;line-height:1.7;overflow-wrap:anywhere}}'
            f'section{{border-top:1px solid #ccc}}</style><h1>Codex 戏剧意图建议</h1>'
            f'<p>候选仅供整包审阅，尚未由作者确认；来源与投产目标由冻结请求绑定。</p>'
            f'<p>任务 {escape(request.job_id)} · 冻结提案 r{identity["revision"]} · {escape(identity["contentHash"])}</p>'
            f'{rows}</html>').encode("utf-8")
