"""Native draft and distinct semantic-check contracts; neither authorizes media."""
import json
from hashlib import sha256
from html import escape

from .contract_hash import stable_hash
from .production_brief import assert_adaptable, production_brief
from .video_backends.minimax_h3.directions import validate_direction_fields
from .video_backends.minimax_h3.prompt import compile_i2va_prompt
from .video_batch_contracts import BatchDirectionsDraft
from .video_fidelity_contracts import FidelityResult
from .video_fidelity_paths import bind_finding_paths


def candidate_identity(directions):
    return stable_hash({key: directions[key] for key in ("sourceHash", "fields")})


def bind_draft(request, candidate):
    if request.source.get("operation") == "fidelity-check":
        return bind_fidelity(request, candidate)
    draft = BatchDirectionsDraft.model_validate(candidate)
    targets = request.input_artifacts["video-targets.json"]["targets"]
    expected = {item["shotId"]: item for item in targets}
    actual = {item.shot_id: item for item in draft.targets}
    if len(actual) != len(draft.targets) or set(actual) != set(expected):
        raise ValueError("draft must cover every frozen target exactly once")
    result = {}
    for shot_id, target in expected.items():
        if "languageContract" in target["snapshot"]:
            assert_adaptable(target["snapshot"])
        package = actual[shot_id].model_dump(mode="json", by_alias=True, exclude={"shot_id"})
        validate_direction_fields(target["snapshot"], package)
        prompt = compile_i2va_prompt(target["snapshot"], package, draft=True)
        result[shot_id] = {"directions": package, "compiledPrompt": prompt}
    return result


def bind_fidelity(request, candidate):
    """Only trusted host provenance can turn this typed verdict into evidence."""
    result = FidelityResult.model_validate(candidate)
    targets = request.input_artifacts["video-targets.json"]["targets"]
    expected = {item["shotId"]: item for item in targets}
    binding = stable_hash([{key: item[key] for key in ("shotId", "sourceHash", "directions", "compiledPrompt")} for item in targets])
    if request.source.get("candidateBinding") not in {None, binding}:
        raise ValueError("frozen checker input binding changed")
    actual = {item.shot_id: item for item in result.targets}
    if len(actual) != len(result.targets) or set(actual) != set(expected):
        raise ValueError("fidelity check must cover every frozen target exactly once")
    bound = {}
    for shot_id, target in expected.items():
        snapshot, directions = target["snapshot"], target["directions"]
        if request.input_artifacts.get("language-contract.json") != snapshot.get("languageContract"):
            raise ValueError("checker language differs from its complete frozen source")
        assert_adaptable(snapshot)
        validate_direction_fields(snapshot, directions)
        prompt = compile_i2va_prompt(snapshot, directions, draft=True)
        check = actual[shot_id]
        paths = {field["path"] for field in directions["fields"]}
        if (check.source_hash != stable_hash(snapshot) or check.candidate_hash != candidate_identity(directions)
                or check.compiled_prompt_sha256 != sha256(prompt.encode()).hexdigest()
                or prompt != target["compiledPrompt"]
                or len(check.checked_paths) != len(paths) or set(check.checked_paths) != paths):
            raise ValueError("fidelity result does not bind exact complete sources, candidate and compiled prompt")
        findings = bind_finding_paths(snapshot, directions, check.findings)
        bound[shot_id] = check.model_dump(mode="json", by_alias=True) | {"findings": findings}
    return bound


def render_report(request, candidate):
    checked = request.source.get("operation") == "fidelity-check"
    result = bind_draft(request, candidate)
    language = request.input_artifacts.get("language-contract.json", {})
    # Historical frozen requests retain their original report rendering.
    if not language:
        body = "".join(f"<article><h2>{escape(key)}</h2><pre>{escape(value['compiledPrompt'])}</pre></article>" for key,value in result.items())
        return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Video directions draft</title>'
            "<style>body{max-width:75ch;margin:3rem auto;font:18px system-ui}pre{white-space:pre-wrap}</style>"
            "<h1>English directions draft</h1><p>Awaiting creator review. No video dispatch or creative approval.</p>" + body + "</html>").encode()
    locale = language["reportLocale"]
    if locale not in {"zh", "en"}:
        raise ValueError("unsupported frozen report locale")
    en = locale == "en"
    title = ("Provider fidelity check" if checked else "Production directions draft") if en else ("提供方指令保真检查" if checked else "制作指令草稿")
    disclaimer = ("Assistant semantic review has limits. It is not creator authorization or media acceptance."
        if en else "助手语义审阅存在局限，不代表创作者授权或成片验收。")
    articles = []
    for target in request.input_artifacts["video-targets.json"]["targets"]:
        brief = production_brief(target["snapshot"])
        sections = "".join(f"<section><h3>{escape(section['label'])}</h3><dl>" + "".join(
            f"<dt>{escape(item['label'])}</dt><dd>{escape(item['value'])}</dd>" for item in section["items"])
            + "</dl></section>" for section in brief["sections"])
        constraints = "".join(f"<li>{escape(item)}</li>" for item in brief["adapterConstraints"])
        sections += f"<p>{escape(brief['discretion'])}</p><ul>{constraints}</ul>"
        value = result[target["shotId"]]
        if checked:
            verdict = (("Passed" if value["verdict"] == "pass" else "Rejected") if en
                else ("检查通过" if value["verdict"] == "pass" else "检查未通过"))
            sections += f"<aside><h3>{verdict}</h3>" + "".join(
                f"<p>{escape(finding['sourceOwner'])} · {escape(finding['message'])}</p>" for finding in value["findings"]) + "</aside>"
        technical = json.dumps({"snapshot": target["snapshot"], "directions": target.get("directions") or value.get("directions"),
            "compiledPrompt": target.get("compiledPrompt") or value.get("compiledPrompt"),
            **({"fidelity": value} if checked else {})}, ensure_ascii=False, indent=2, sort_keys=True)
        label = "Exact provider instructions / checking result" if en else "精确提供方指令／检查结果"
        articles.append(f"<article><h2>{escape(target['shotId'])}</h2>{sections}<details><summary>{label}</summary><pre>{escape(technical)}</pre></details></article>")
    return (f'<!doctype html><html lang="{locale}"><meta charset="utf-8"><title>{title}</title>'
        '<style>body{max-width:85ch;margin:3rem auto;font:18px system-ui}dd{white-space:pre-wrap;margin-bottom:1em}dt{font-weight:bold}pre{white-space:pre-wrap}</style>'
        f'<h1>{title}</h1><p>{disclaimer}</p>' + ''.join(articles) + '</html>').encode()
