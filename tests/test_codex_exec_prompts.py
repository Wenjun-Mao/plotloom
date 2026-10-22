import pytest

from plotloom.autopilot_image_guidance import IMAGE_CONTENT_OWNERSHIP_INSTRUCTION
from plotloom.codex_exec_prompts import (
    IMAGE_PROMPT_VERSION,
    PROMPT_VERSION,
    assignment_prompt,
)


def test_text_prompt_assigns_candidate_files_and_leaves_completion_to_host(tmp_path):
    prompt = assignment_prompt(
        job_id="ch_" + "a" * 20,
        package_path=tmp_path / "package",
        delivery_path=tmp_path / "delivery",
        domain="text",
    )

    assert PROMPT_VERSION.endswith("v6")
    assert "Write only the requested candidate JSON" in prompt
    assert "trusted host runs its exact frozen validation plan" in prompt
    assert "request.creativeBrief" in prompt
    assert "manual specialist-chat workflow" in prompt
    assert "Do not invoke validators or renderers" in prompt
    assert "do not claim trusted validation" in prompt
    assert "Do not `cd` into" in prompt
    assert "Do not write image files" not in prompt
    assert IMAGE_CONTENT_OWNERSHIP_INSTRUCTION not in prompt
    assert "request.textCorrection" in prompt
    assert "untrusted candidate data" in prompt
    assert "preserve every frozen source/style/upstream constraint" in prompt


def test_image_prompt_reserves_delivery_tree_for_trusted_host_copy(tmp_path):
    prompt = assignment_prompt(
        job_id="ij_" + "b" * 20,
        package_path=tmp_path / "package",
        delivery_path=tmp_path / "delivery",
        domain="image",
    )

    assert "Do not write image files or completion markers" in prompt
    assert "trusted host copies its exact completed session output" in prompt
    assert IMAGE_PROMPT_VERSION.endswith("v6")
    assert prompt.startswith(IMAGE_PROMPT_VERSION)
    assert IMAGE_CONTENT_OWNERSHIP_INSTRUCTION in prompt
    assert "one direct top-level awaited expression" in prompt
    assert "Do not put it in a branch" in prompt
    assert "Write only the requested candidate JSON" not in prompt
    assert "view_image" in prompt
    assert "referenced_image_paths" in prompt
    assert "manual specialist-chat pin" in prompt
    assert "Do not run those commands" in prompt
    assert "without claiming host publication or completion" in prompt


def test_prompt_rejects_an_unowned_domain(tmp_path):
    with pytest.raises(ValueError, match="supported delivery domain"):
        assignment_prompt(
            job_id="ch_" + "c" * 20,
            package_path=tmp_path / "package",
            delivery_path=tmp_path / "delivery",
            domain="unknown",
        )
