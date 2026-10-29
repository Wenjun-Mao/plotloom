"""The actual validated request preserves an executable two-command paragraph."""
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.language_policy import freeze_request_language
from plotloom.storyboard_brief_style import storyboard_brief_instructions
from tests.storyboard_brief_fixtures import real_example_request, execute_example_package


def test_validated_request_freeze_keeps_renderer_shell_block_exact(tmp_path):
    request, board, _binding = real_example_request("restrained watercolor collage")
    authored = storyboard_brief_instructions()
    packet = request.model_dump(mode="json", by_alias=True)
    packet["creativeBrief"] = authored + "\n\n"
    validated = CreativeHandoffRequest.model_validate(packet)
    # Pydantic removes trailing whitespace before prospective language freeze.
    assert validated.creative_brief == authored.strip()
    freeze_request_language(validated, "zh-CN")
    marker = "From the Plotloom repository root, run exactly:\n"
    expected = authored.split(marker, 1)[1].splitlines()
    command_block, prose = validated.creative_brief.split(marker, 1)[1].split("\n\n", 1)
    assert len(expected) == 2 and command_block.splitlines() == expected
    assert prose.lstrip().startswith("Read inputs/language-contract.json:")
    delivered = execute_example_package(tmp_path, validated, board)
    assert delivered.candidate == board
    assert b"<html" in delivered.report.lower()
