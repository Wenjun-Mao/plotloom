"""Suggestions-only semantic spans bound to exact frozen presentation evidence."""
from html import escape
from typing import Literal

from pydantic import ConfigDict, Field

from .creative_handoff_contracts import CreativeHandoffRequest
from .domain import CamelModel
from .production_presentation import (
    PresentationSpan, PresentationUpdate, ProductionPresentation, bind_presentation_spans,
)

MAX_PRESENTATION_CONTEXT_BYTES = 180_000
MAX_PRESENTATION_SOURCES = 256


class SuggestedPresentationSpan(PresentationSpan):
    model_config = ConfigDict(extra="forbid")
    role: Literal["physical", "visible_text", "runtime_choice", "review_only", "dialogue"]
    rendering: str = Field(max_length=12_000)
    reason: str = Field(max_length=2_000)


class PresentationSuggestionEntry(CamelModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    spans: list[SuggestedPresentationSpan] = Field(min_length=1, max_length=64)


class PresentationSuggestions(CamelModel):
    model_config = ConfigDict(extra="forbid")
    entries: list[PresentationSuggestionEntry] = Field(min_length=1, max_length=MAX_PRESENTATION_SOURCES)


def presentation_response_schema(expected_ids: list[str]) -> dict:
    schema = PresentationSuggestions.model_json_schema(by_alias=True)
    schema["$defs"]["PresentationSuggestionEntry"]["properties"]["id"]["enum"] = expected_ids
    schema["properties"]["entries"].update(minItems=len(expected_ids), maxItems=len(expected_ids))
    return schema


def frozen_presentation(request: CreativeHandoffRequest) -> ProductionPresentation:
    if request.stage != "bridge-presentation":
        raise ValueError("not a presentation suggestion request")
    return ProductionPresentation.model_validate(request.input_artifacts["presentation-source.json"])


def native_presentation_suggestions(request: CreativeHandoffRequest, candidate: dict) -> PresentationSuggestions:
    suggestions = PresentationSuggestions.model_validate(candidate)
    package = frozen_presentation(request)
    bind_presentation_spans(package, [PresentationUpdate(id=item.id, spans=item.spans) for item in suggestions.entries])
    return suggestions


def render_native_presentation_report(request: CreativeHandoffRequest, candidate: dict) -> bytes:
    suggestions = native_presentation_suggestions(request, candidate)
    by_id = {entry.id: entry for entry in suggestions.entries}
    sections = []
    for source in frozen_presentation(request).sources:
        spans = "".join(f"<li><strong>{escape(span.role)}</strong><blockquote>{escape(source.source_text[span.start:span.end])}</blockquote>"
            f"<p>{escape(span.rendering)}</p><p>{escape(span.reason)}</p></li>" for span in by_id[source.id].spans)
        sections.append(f"<section><h2>{escape(source.id)}</h2><ol>{spans}</ol></section>")
    proposal = request.source["proposal"]
    return ("<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>Codex 呈现方式建议</title>"
        "<style>body{font:17px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:24px}section{border-top:1px solid #bbb}blockquote{white-space:pre-wrap}</style>"
        f"<h1>Codex 呈现方式建议 · 待作者确认</h1><p>冻结提案 r{proposal['revision']} · {escape(proposal['contentHash'])}</p>"
        "<p>助手建议不是作者确认；不会投产或生成媒体。</p>" + "".join(sections) + "</html>").encode()
