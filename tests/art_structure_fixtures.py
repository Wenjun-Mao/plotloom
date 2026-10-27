"""Fresh Art shape packets over real existing upstream/preset/saved-Brief examples."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_artifact
from plotloom.art_style import freeze_art_style
from tests.test_art_style import candidate
from tests.test_codex_exec_validation import _request
from tests.test_codex_exec_stage_routing import _saved_brief_example

ROOT = Path(__file__).resolve().parents[1]
NODE = str(Path(shutil.which("node")).resolve())


def art_case(tmp_path, *, saved=False):
    if saved:
        request, value, _ = _saved_brief_example("art")
    else:
        contract = freeze_art_style("realistic", None)
        cast = json.loads((ROOT / "third_party/shuohao-skills/skills/novel-characters/examples/渡口-cast.json").read_bytes())
        request = _request("art", {"cast.json": cast, "art-style-contract.json": contract})
        value = candidate(contract)
    request = request.model_copy(update={"content_validation_contract": "plotloom.typed-content-result.v1",
        "input_artifacts": request.input_artifacts | {ART_STRUCTURE_FILENAME: art_structure_artifact(preset=not saved)}})
    inputs = tmp_path / "package/inputs"
    inputs.mkdir(parents=True)
    for name, content in request.input_artifacts.items():
        (inputs / name).write_text(json.dumps(content, ensure_ascii=False))
    return request, value


def write_art_packet(tmp_path, request, value):
    (tmp_path / "package/request.json").write_text(request.model_dump_json(by_alias=True))
    (tmp_path / "art.json").write_text(json.dumps(value, ensure_ascii=False))


def run_art(tmp_path, request, value):
    write_art_packet(tmp_path, request, value)
    return subprocess.run(art_command(tmp_path), capture_output=True, timeout=25)


def art_command(tmp_path):
    return [sys.executable, str(ROOT / "scripts/art_content_validation.py"), str(tmp_path / "art.json"),
        "--request", str(tmp_path / "package/request.json"), "--node", NODE]
