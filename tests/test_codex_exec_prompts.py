import pytest

from plotloom.codex_exec_prompts import PROMPT_VERSION, assignment_prompt


def test_text_prompt_assigns_candidate_files_and_leaves_completion_to_host(tmp_path):
    prompt = assignment_prompt(
        job_id="ch_" + "a" * 20,
        package_path=tmp_path / "package",
        delivery_path=tmp_path / "delivery",
        domain="text",
    )

    assert PROMPT_VERSION.endswith("v3")
    assert "Write only the requested candidate and report files" in prompt
    assert "trusted host publishes the completion manifest" in prompt
    assert "$PLOTLOOM_SOURCE_ROOT" in prompt
    assert "$PLOTLOOM_UV" in prompt
    assert "$PLOTLOOM_UV" in prompt
    assert "--locked --no-sync" in prompt
    assert "Do not `cd` into" in prompt
    assert "Do not write image files" not in prompt


def test_image_prompt_reserves_delivery_tree_for_trusted_host_copy(tmp_path):
    prompt = assignment_prompt(
        job_id="ij_" + "b" * 20,
        package_path=tmp_path / "package",
        delivery_path=tmp_path / "delivery",
        domain="image",
    )

    assert "Do not write image files or completion markers" in prompt
    assert "trusted host copies its exact completed session output" in prompt
    assert "one direct top-level awaited expression" in prompt
    assert "Do not put it in a branch" in prompt
    assert "Write only the requested candidate and report files" not in prompt


def test_prompt_rejects_an_unowned_domain(tmp_path):
    with pytest.raises(ValueError, match="supported delivery domain"):
        assignment_prompt(
            job_id="ch_" + "c" * 20,
            package_path=tmp_path / "package",
            delivery_path=tmp_path / "delivery",
            domain="unknown",
        )
