"""Complete source-bound English drafts; no human endorsement is produced here."""
from html import escape
from .video_batch_contracts import BatchDirectionsDraft
from .video_backends.minimax_h3.directions import validate_direction_fields
from .video_backends.minimax_h3.prompt import compile_i2va_prompt

def bind_draft(request, candidate):
    draft = BatchDirectionsDraft.model_validate(candidate)
    targets = request.input_artifacts["video-targets.json"]["targets"]
    expected = {item["shotId"]: item for item in targets}
    actual = {item.shot_id: item for item in draft.targets}
    if len(actual) != len(draft.targets) or set(actual) != set(expected):
        raise ValueError("draft must cover every frozen target exactly once")
    result = {}
    for shot_id, target in expected.items():
        package = actual[shot_id].model_dump(mode="json", by_alias=True, exclude={"shot_id"})
        validate_direction_fields(target["snapshot"], package)
        prompt = compile_i2va_prompt(target["snapshot"], package, draft=True)
        result[shot_id] = {"directions": package, "compiledPrompt": prompt}
    return result

def render_report(request, candidate):
    targets = bind_draft(request, candidate)
    body = "".join(f"<article><h2>{escape(key)}</h2><pre>{escape(value['compiledPrompt'])}</pre></article>" for key,value in targets.items())
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Video directions draft</title>'
        "<style>body{max-width:75ch;margin:3rem auto;font:18px system-ui}pre{white-space:pre-wrap}</style>"
        "<h1>English directions draft</h1><p>Awaiting creator review. No video dispatch or creative approval.</p>" + body + "</html>").encode()
