"""Report UI metadata is independent of author content and never rewrites it."""
import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.outline_report_metadata import (
    OUTLINE_REPORT_SCHEMA_FILENAME,
    assert_outline_report_metadata,
    assert_outline_report_schema_current,
    outline_report_metadata_schema,
)


@pytest.mark.parametrize("metadata", [{}, {"lang": None}, {"lang": "zh"}, {"lang": "en"}])
def test_metadata_projection_preserves_creative_content_and_defaults(metadata):
    candidate = {**metadata, "episodes": [{"synopsis": "雨夜"}], "params": {"language": "zh-CN"}}
    before = deepcopy(candidate)
    assert assert_outline_report_metadata(candidate) is None
    assert candidate == before
    assert candidate.keys() == before.keys()


@pytest.mark.parametrize("lang", ["zh-CN", "en-US", "", " ", "ZH", 0, 1, False, [], {}])
def test_metadata_rejects_non_ui_keys_without_conversion(lang):
    with pytest.raises(CreativeHandoffError) as error:
        assert_outline_report_metadata({"lang": lang})
    assert error.value.code == "outline_report_metadata_invalid"


def test_generated_schema_is_a_permissive_metadata_projection():
    schema = outline_report_metadata_schema()
    assert schema["additionalProperties"] is True
    assert "required" not in schema
    assert set(schema["properties"]) == {"lang"}
    assert schema["properties"]["lang"]["anyOf"] == [
        {"enum": ["zh", "en"], "type": "string"}, {"type": "null"},
    ]
    assert_outline_report_schema_current({OUTLINE_REPORT_SCHEMA_FILENAME: schema})
    schema["properties"]["lang"]["default"] = "en"
    with pytest.raises(CreativeHandoffError) as error:
        assert_outline_report_schema_current({OUTLINE_REPORT_SCHEMA_FILENAME: schema})
    assert error.value.code == "outline_report_schema_stale"
    with pytest.raises(CreativeHandoffError) as error:
        assert_outline_report_schema_current({})
    assert error.value.code == "outline_report_schema_missing"


def test_expected_schema_identity_distinguishes_boolean_from_number():
    schema = outline_report_metadata_schema() | {"additionalProperties": 1}
    with pytest.raises(CreativeHandoffError, match="not current"):
        assert_outline_report_schema_current({OUTLINE_REPORT_SCHEMA_FILENAME: schema})


@pytest.mark.parametrize("metadata", [{}, {"lang": None}, {"lang": "zh"}, {"lang": "en"}])
def test_valid_metadata_renders_through_unchanged_upstream_commands(tmp_path, metadata):
    stage = Path(__file__).resolve().parents[1] / "third_party/shuohao-skills/skills/novel-outline"
    candidate = json.loads((stage / "examples/渡口-outline.json").read_bytes())
    candidate.pop("lang", None)
    candidate.update(metadata)
    candidate["params"]["language"] = "zh-CN"
    assert_outline_report_metadata(candidate)
    raw = json.dumps(candidate, ensure_ascii=False).encode()
    path = tmp_path / "outline.json"
    path.write_bytes(raw)
    for argv in [("validate", str(path)), ("render", str(path), "--html")]:
        completed = subprocess.run(["node", str(stage / "scripts/novel-outline.mjs"), *argv],
                                   capture_output=True, timeout=15, check=False)
        assert completed.returncode == 0, completed.stderr.decode()
        if argv[0] == "render":
            assert completed.stdout.lstrip().lower().startswith(b"<!doctype html")
            label = "Quality gates" if metadata.get("lang") == "en" else "质量门"
            assert label.encode() in completed.stdout
    assert path.read_bytes() == raw
