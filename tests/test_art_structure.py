"""Art's source-owned structural normal result; no candidate coercion or provider."""
import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_issues
from tests.art_structure_fixtures import ROOT, NODE, art_case, art_command, run_art, write_art_packet


@pytest.mark.parametrize("saved", [False, True])
def test_complete_art_structural_result_then_valid_render_byte_parity(tmp_path, saved):
    request, good = art_case(tmp_path, saved=saved)
    bad = deepcopy(good)
    scene = bad["scenes"][0]
    scene["lighting"] = "not an array"
    scene.pop("anchors"); scene.pop("summary")
    result = run_art(tmp_path, request, bad)
    assert result.returncode == 42 and not result.stderr, result.stderr
    data = json.loads(result.stdout)
    assert data["candidateHash"] == sha256((tmp_path / "art.json").read_bytes()).hexdigest()
    assert {message.split(":")[0] for message in data["displayDiagnostics"]} >= {
        "$.scenes[0].lighting", "$.scenes[0].anchors", "$.scenes[0].summary"}
    assert run_art(tmp_path, request, good).returncode == 0
    file = tmp_path / "art.json"; before = file.read_bytes()
    adapter = "brief-art-style.mjs" if saved else "art-style.mjs"
    command = [NODE, str(ROOT / "scripts" / adapter), "render", str(file),
        "--cast", str(tmp_path / "package/inputs/cast.json")]
    if not saved: command += ["--html", "--contract", str(tmp_path / "package/inputs/art-style-contract.json")]
    report = subprocess.run(command, capture_output=True, check=True).stdout
    assert b"<html" in report.lower()
    assert run_art(tmp_path, request, good).returncode == 0
    assert subprocess.run(command, capture_output=True, check=True).stdout == report
    assert file.read_bytes() == before


@pytest.mark.parametrize("field,value", [("scenes", None), ("scenes", {}), ("scenes", [None]),
    ("props", {}), ("props", [1])])
def test_art_bad_root_containers_are_normal_structural_issues(field, value):
    doc = {"source": "x", "style": "realistic", "scenes": []}
    doc[field] = value
    assert any(x.startswith("$." + field) for x in art_structure_issues(doc, preset=False))


@pytest.mark.parametrize("field,value", [("anchors", "x"), ("anchors", [None]*3),
    ("lighting", {}), ("lighting", ["x"]), ("image", []), ("primary", 1),
    ("usage", None), ("usage", {"episodes": "x", "beats": []})])
def test_art_bad_nested_fields_return_all_errors(tmp_path, field, value):
    request, doc = art_case(tmp_path)
    doc["scenes"][0][field] = value
    assert run_art(tmp_path, request, doc).returncode == 42


@pytest.mark.parametrize("props", ["omit", None, []])
@pytest.mark.parametrize("saved", [False, True])
def test_optional_props_and_tolerated_extensions_preserve_application_boundary(tmp_path, props, saved):
    request, doc = art_case(tmp_path, saved=saved)
    if props == "omit": doc.pop("props", None)
    else: doc["props"] = props
    doc["extension"] = {"arbitrary": [False, 3]}
    doc["scenes"][0]["extension"] = None
    doc["scenes"][0]["image"]["tags"] = [42, None, {"extension": True}]
    # ECMAScript trim does not treat U+0085 as whitespace; do not narrow thText.
    doc["scenes"][0]["summary"] = "\u0085"
    issues = art_structure_issues(doc, preset=not saved)
    result = run_art(tmp_path, request, doc)
    if props is None:
        assert issues == ("$.props: must be an array",) and result.returncode == 42
        # This is upstream-only tolerance, never application receiving acceptance.
        from plotloom.persistence.project.art import _art_ids
        with pytest.raises(ValueError): _art_ids(doc)
        unmarked = request.model_copy(update={"input_artifacts": {
            k:v for k,v in request.input_artifacts.items() if k != ART_STRUCTURE_FILENAME}})
        path = tmp_path/"package/unmarked-request.json"
        path.write_text(unmarked.model_dump_json(by_alias=True))
        legacy = subprocess.run([NODE, str(ROOT/"scripts/text-content-validation.mjs"),
            str(tmp_path/"art.json"), str(path)], capture_output=True)
        assert legacy.returncode == 0
    else:
        assert not issues and result.returncode == 0
        if props == "omit": assert "props" not in json.loads((tmp_path/"art.json").read_bytes())


@pytest.mark.parametrize("mutation", ["marker", "schema", "schema-type", "missing-marker", "copy", "copy-type", "style", "style-type", "authority",
    "cast", "node", "parser", "nan", "bom", "prior", "overflow"])
def test_art_parser_frozen_context_and_runtime_failures_never_grant_correction(tmp_path, mutation):
    request, doc = art_case(tmp_path, saved=True)
    doc["scenes"][0]["lighting"] = "invalid"
    artifacts = deepcopy(request.input_artifacts)
    if mutation == "marker": artifacts[ART_STRUCTURE_FILENAME]["contract"] = "unknown"
    elif mutation == "schema": artifacts[ART_STRUCTURE_FILENAME]["schema"]["extra"] = True
    elif mutation == "schema-type": artifacts[ART_STRUCTURE_FILENAME]["schema"]["additionalProperties"] = 1
    elif mutation == "missing-marker": artifacts.pop(ART_STRUCTURE_FILENAME)
    elif mutation == "style": artifacts["art-style-contract.json"]["contentHash"] = "0"*64
    elif mutation == "style-type": artifacts["art-style-contract.json"]["version"] = True
    elif mutation == "authority": artifacts["art-style-contract.json"]["authority"] = "foreign"
    elif mutation == "cast": artifacts["cast.json"] = {"characters": {}}
    elif mutation == "overflow": doc["scenes"] = [{}]*10
    request = request.model_copy(update={"input_artifacts": artifacts})
    for name, content in artifacts.items(): (tmp_path / "package/inputs" / name).write_text(json.dumps(content))
    if mutation == "copy": (tmp_path / "package/inputs/cast.json").write_text("{}")
    if mutation == "copy-type":
        altered=deepcopy(artifacts[ART_STRUCTURE_FILENAME]);altered["schema"]["additionalProperties"]=1
        (tmp_path/"package/inputs"/ART_STRUCTURE_FILENAME).write_text(json.dumps(altered))
    write_art_packet(tmp_path, request, doc)
    command = art_command(tmp_path)
    if mutation == "node": command[-1] = str(tmp_path / "absent-node")
    elif mutation == "parser": (tmp_path / "art.json").write_text("{")
    elif mutation == "nan": (tmp_path / "art.json").write_text('{"scenes":NaN}')
    elif mutation == "bom": (tmp_path / "art.json").write_bytes(b'\xef\xbb\xbf{}')
    elif mutation == "prior":
        raw = json.loads((tmp_path / "package/request.json").read_text())
        raw["textCorrection"] = {"priorCandidateJson": "{}", "rejection": {"candidateHash": "0"*64}}
        (tmp_path / "package/request.json").write_text(json.dumps(raw))
    result = subprocess.run(command, capture_output=True, timeout=25)
    assert result.returncode == 1 and result.stdout == b"", result.stdout


@pytest.mark.parametrize("saved", [False, True])
def test_marked_art_plan_binds_python_node_and_refuses_manual_preflight_substitution(tmp_path, saved):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom.codex_exec_validation import validation_plan_from_package
    from plotloom.codex_exec_resources import codex_exec_source_resources
    from plotloom.alpha_provenance import preflight_plan_identity
    request, _ = art_case(tmp_path, saved=saved)
    exchange = CreativeHandoffExchange(tmp_path / "exchange");pin = exchange.current_execution_pin("art")
    paths = exchange.write_package(request, pin, executor_backend="codex_exec", plotloom_code_revision="a"*40)
    payload = json.loads((Path(paths["packagePath"])/"request.json").read_bytes());plan = validation_plan_from_package(payload)
    assert plan.steps[0].program == "uv" and plan.steps[0].argv[-2:] == ("--node", "{tool:node}")
    assert "{source}/scripts/art_content_validation.py" in plan.steps[0].argv
    assert plan.steps[1].program == "node"
    resources = codex_exec_source_resources(ROOT, payload)
    assert {"uv", "node", "python"} <= dict(resources.tools).keys()
    assert (ROOT / "scripts/art_content_validation.py") in resources.read_paths
    if saved:
        assert (ROOT/"scripts/brief-cast-style.mjs") in resources.read_paths
        assert (ROOT/"third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs") in resources.read_paths
    assert preflight_plan_identity(Path(paths["packagePath"]))[2] == plan.plan_hash
    old = request.model_copy(update={"job_id": "ch_"+"v"*32,
        "input_artifacts": {k:v for k,v in request.input_artifacts.items() if k != ART_STRUCTURE_FILENAME}})
    ordinary = exchange.write_package(old, pin, executor_backend="codex_exec", plotloom_code_revision="a"*40)
    with pytest.raises(ValueError, match="marked Python"):
        preflight_plan_identity(Path(ordinary["packagePath"]))


def test_saved_optional_extension_items_keep_existing_tolerance(tmp_path):
    request, doc = art_case(tmp_path, saved=True)
    doc["scenes"][0]["states"] = [None, 17, "extension"]
    assert not art_structure_issues(doc, preset=False)
    assert art_structure_issues(doc, preset=True)
    assert run_art(tmp_path, request, doc).returncode == 0
    result = subprocess.run([NODE, str(ROOT / 'scripts/brief-art-style.mjs'), 'render',
        str(tmp_path/'art.json'), '--cast', str(tmp_path/'package/inputs/cast.json')], capture_output=True)
    assert result.returncode == 0 and b'<html' in result.stdout.lower()


def test_valid_shape_keeps_existing_specific_art_scale_feedback(tmp_path):
    request, doc = art_case(tmp_path, saved=True)
    assert doc['props']
    for key in ['prompt', 'sheet']:
        for phrase in ['handheld scale', 'tabletop scale', 'furniture scale']:
            doc['props'][0]['image'][key] = doc['props'][0]['image'][key].replace(phrase, '')
    assert not art_structure_issues(doc, preset=False)
    result = run_art(tmp_path, request, doc)
    assert result.returncode == 42 and not result.stderr
    assert any(issue['code']=='art_prop_scale' for issue in json.loads(result.stdout)['issues'])


def test_runtime_nonzero_and_exact_prior_parser_are_never_structural_results(tmp_path):
    request, doc = art_case(tmp_path, saved=True)
    write_art_packet(tmp_path, request, doc)
    node = tmp_path/'failed-node'
    node.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo v24.18.0; exit 0; fi\nexit 2\n')
    node.chmod(0o700)
    command=art_command(tmp_path);command[-1]=str(node)
    result=subprocess.run(command,capture_output=True)
    assert result.returncode==2 and not result.stdout
    raw=json.loads((tmp_path/'package/request.json').read_text())
    raw['textCorrection']={'priorCandidateJson':'{','rejection':{'candidateHash':sha256(b'{').hexdigest()}}
    (tmp_path/'package/request.json').write_text(json.dumps(raw))
    doc['scenes'][0]['lighting']='invalid'
    (tmp_path/'art.json').write_text(json.dumps(doc))
    result=subprocess.run(art_command(tmp_path),capture_output=True)
    assert result.returncode==1 and not result.stdout
