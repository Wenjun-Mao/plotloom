"""Explicit synthetic literal intent/provenance for offline checks only."""

from plotloom.content_language_classifier import string_leaves
from plotloom.provider_literals import LITERAL_INPUT, digest, freeze_provider_context, text_hash


def literal_source(request):
    request.source["text"] = request.source.get("text", "") + "\n" + 'A plain yellow cup bears the exact nonspoken visible lettering 安 and Mira. Do not speak the lettering.'
    freeze_provider_context(request)


def add_fact(request, text="安", role="literal_visible_text"):
    context = request.input_artifacts[LITERAL_INPUT]
    path = "$.source.text"; value = context["sources"][path]["text"]; start = value.index(text)
    fact = {"role":role,"sourceSpan":{"path":path,"start":start,"end":start+len(text),"text":text},
        "sourceFieldHash":text_hash(value), "evidence":[{"checkJobId":"synthetic-upstream-check", "bindingHash":"a"*64,"candidateHash":"d"*64,"resultHash":"b"*64,"receiptHash":"c"*64}]}
    fact["id"] = digest({k:fact[k] for k in ("role","sourceSpan","sourceFieldHash")})
    freeze_provider_context(request, facts=[*context["facts"],fact])
    return fact


def claim(request, candidate, path, text="安", *, fact=None, role="literal_visible_text"):
    leaves = dict(string_leaves(candidate)); value=leaves[path]; start=value.index(text)
    context = request.input_artifacts[LITERAL_INPUT]; source=context["sources"]["$.source.text"]["text"]; offset=source.index(text)
    value = {"role":role,"candidateSpan":{"path":path,"start":start,"end":start+len(text),"text":text},
        "sourceSpan":{"path":"$.source.text","start":offset,"end":offset+len(text),"text":text},
        "candidateFieldHash":text_hash(leaves[path]),"sourceFieldHash":text_hash(source),"sourceFactId":fact["id"] if fact else None}
    candidate.setdefault("providerLiterals",[]).append(value)
    return value


def art_literal_case(tmp_path, *, saved=True):
    from tests.art_structure_fixtures import art_case
    request,candidate=art_case(tmp_path,saved=saved);literal_source(request);fact=add_fact(request)
    preset=request.input_artifacts["art-style-contract.json"].get("preset",{})
    render=preset.get("render", "Muted watercolor collage")
    candidate["props"]=[{"id":"P01","name":"黄杯","scale":"手持级","summary":"正面写着安的黄色杯子。",
        "anchors":[{"name":name,"desc":"固定细节"} for name in ["杯沿","杯柄","杯底"]],
        "states":[{"state":"完整","description":"正面有安字。","prompt":"Plain yellow cup bearing 安 on its front"}],
        "image":{"prompt":render+", handheld scale, plain yellow cup bearing 安 on its front",
            "sheet":render+", handheld scale, white background, plain yellow cup bearing 安 on its front",
            "negativePrompt":"people, human figures, hands, malformed objects", "tags":[],
            **({"style":"Saved Brief direction"} if saved else {})}}]
    for path in ["$.props[0].states[0].prompt","$.props[0].image.prompt","$.props[0].image.sheet"]:
        claim(request,candidate,path,fact=fact)
    return request,candidate


def sync_inputs(root, request):
    inputs=root/"package/inputs";inputs.mkdir(parents=True,exist_ok=True)
    from plotloom.creative_handoff_identity import canonical_json
    for name,value in request.input_artifacts.items(): (inputs/name).write_bytes(canonical_json(value))
