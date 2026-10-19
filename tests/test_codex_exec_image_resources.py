"""Image workers read one source-pinned instruction file, with no runtime grants."""
import hashlib
import subprocess

import pytest

from plotloom.codex_exec_resources import (
    CodexExecResourceError,
    codex_exec_image_resources,
)


@pytest.fixture
def image_source(tmp_path):
    root = tmp_path / "source"
    skill = root / ".agents/skills/plotloom-image-specialist/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"frozen image skill\n")
    for args in (("init", "--quiet"), ("add", "."),
                 ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "--quiet", "-m", "image instruction fixture")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    request = {"packageVersion": 8, "executorBackend": "codex_exec", "executionContract": "codex_exec.v1",
               "specialistPreflight": {"version": "p1.5-pin.v2", "skillVersion": "plotloom-image-specialist.v4",
                   "executionContract": "codex_exec.v1", "codeRevision": revision,
                   "skillHash": hashlib.sha256(skill.read_bytes()).hexdigest()}}
    return root, skill, request


def test_image_instruction_grant_is_one_exact_regular_file(image_source):
    root, skill, request = image_source
    resources = codex_exec_image_resources(root, request)
    assert resources.read_paths == (skill,)
    assert resources.tools == ()
    assert resources.python_environment is None


@pytest.mark.parametrize("field,value", [("codeRevision", "0" * 40), ("skillHash", "0" * 64),
    ("skillVersion", "other"), ("executionContract", "codex_specialist.v3"), ("version", "p1.5-pin.v1")])
def test_image_instruction_pin_cannot_drift(image_source, field, value):
    root, _skill, request = image_source
    request["specialistPreflight"][field] = value
    with pytest.raises(CodexExecResourceError):
        codex_exec_image_resources(root, request)


@pytest.mark.parametrize("defect", ["missing", "changed", "symlink", "directory"])
def test_unavailable_or_redirected_instruction_cannot_be_granted(image_source, tmp_path, defect):
    root, skill, request = image_source
    original = skill.read_bytes()
    skill.unlink()
    if defect == "changed":
        skill.write_bytes(original + b"changed")
    elif defect == "symlink":
        outside = tmp_path / "outside.md"
        outside.write_bytes(original)
        skill.symlink_to(outside)
    elif defect == "directory":
        skill.mkdir()
    with pytest.raises(CodexExecResourceError):
        codex_exec_image_resources(root, request)
